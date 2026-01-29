import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import json
import os
import re
import time
import random

# [필수 라이브러리]
import yfinance as yf
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ==========================================
# 0. 페이지 설정 및 스타일
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        .report-box { background-color: #FFFFFF; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; }
        .history-header { font-size: 1.2em; font-weight: 700; color: #475569; margin-top: 50px; margin-bottom: 20px; border-left: 5px solid #CBD5E1; padding-left: 10px; }
        .status-log { font-family: monospace; font-size: 0.9em; color: #334155; background: #F1F5F9; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #3B82F6; }
        .error-log { font-family: monospace; font-size: 0.9em; color: #991B1B; background: #FEF2F2; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #EF4444; }
        
        /* 뉴스 카드 스타일 */
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-title:hover { color: #2563EB !important; text-decoration: underline; }
        .news-snippet { font-size: 13.5px !important; color: #475569 !important; line-height: 1.5; margin-bottom: 10px; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package", "Daily Report"
]

DAILY_DEFAULT_KEYWORDS = [
    "반도체 소재", "소재 공급망", "희토류 제한", "EUV", 
    "중국 반도체", "일본 반도체", "중국 광물", "반도체 규제", "삼성전자 파운드리", "SK하이닉스 HBM"
]

STOCK_CATEGORIES = {
    "🏭 Chipmakers": {"Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU", "TSMC": "TSM", "Intel": "INTC", "SMIC": "0981.HK"},
    "🧠 Fabless": {"Nvidia": "NVDA", "Broadcom": "AVGO", "Qnity (Q)": "Q"},
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T", "KLA": "KLAC", "Hanmi": "042700.KS", "Jusung": "036930.KS"},
    "🧪 Materials": {
        "Shin-Etsu": "4063.T", "Sumitomo": "4005.T", "TOK": "4186.T", "Nissan Chem": "4021.T", 
        "Merck": "MRK.DE", "Air Liquide": "AI.PA", "Linde": "LIN", 
        "Soulbrain": "357780.KS", "Dongjin": "005290.KS", "ENF": "102710.KS", "Ycchem": "232140.KS"
    },
    "🔋 Others": {"Samsung SDI": "006400.KS"}
}

# ==========================================
# 1. 데이터 관리
# ==========================================
@st.cache_data(ttl=600)
def get_stock_prices_grouped():
    all_tickers = []
    for cat in STOCK_CATEGORIES.values(): all_tickers.extend(cat.values())
    ticker_str = " ".join(all_tickers)
    result_map = {}
    try:
        stocks = yf.Tickers(ticker_str)
        if not stocks.tickers: return {}
        for symbol in all_tickers:
            try:
                hist = stocks.tickers[symbol].history(period="5d")
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change = current - prev
                    pct_change = (change / prev) * 100
                    currency = "₩" if ".KS" in symbol else ("¥" if ".T" in symbol else ("HK$" if ".HK" in symbol else ("€" if ".DE" in symbol or ".PA" in symbol else "$")))
                    result_map[symbol] = {"Price": f"{currency}{current:,.0f}" if currency in ["₩", "¥"] else f"{currency}{current:,.2f}", "Delta": f"{change:,.2f} ({pct_change:+.2f}%)"}
            except: pass
    except: pass
    return result_map

KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json' 

def load_keywords():
    data = {cat: [] for cat in CATEGORIES}
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in data: data[k] = v
        except: pass
    if "Daily" in data: data["Daily Report"] = data.pop("Daily")
    if not data.get("Daily Report"): data["Daily Report"] = DAILY_DEFAULT_KEYWORDS
    return data

def save_keywords(data):
    try: 
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def load_daily_history():
    if os.path.exists(HISTORY_FILE):
        try: 
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f: 
                return json.load(f) 
        except: return []
    return []

def save_daily_history(new_report_data):
    history = load_daily_history()
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data) 
    try: 
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f: 
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass
    return history

def clean_text(text):
    if not text: return ""
    clean = re.sub('<.*?>', '', text)
    clean = re.sub('\s+', ' ', clean).strip()
    return clean

# [수정] 안전 설정 강화 (Gemini가 거부하지 않게 설정)
def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    
    # 안전 필터 해제 (뉴스 요약 시 '전쟁', '규제' 단어로 인한 차단 방지)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    
    try: 
        return genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
    except: 
        return genai.GenerativeModel('gemini-pro', safety_settings=safety_settings)

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        model = get_gemini_model(api_key)
        content_text = ""
        for i, item in enumerate(articles[:20]): 
            safe_snip = clean_text(item.get('Snippet', ''))[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {safe_snip}\n"
        prompt = f"Role: Analyst. Task: Filter noise. Output: IDs ONLY (e.g., 1, 3). Data:\n{content_text}"
        response = model.generate_content(prompt)
        nums = re.findall(r'\d+', response.text)
        valid_indices = [int(n)-1 for n in nums]
        filtered = [articles[idx] for idx in valid_indices if 0 <= idx < len(articles)]
        return filtered if filtered else articles
    except: return articles

# ==========================================
# 3. 핵심: 리포트 생성 파이프라인
# ==========================================

def fetch_rss_feed(keyword, days_back=2):
    # 한국어 뉴스 검색
    url = f"https://news.google.com/rss/search?q={quote(keyword)}+when:{days_back}d&hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            return soup.find_all('item')
    except: pass
    return []

def parse_and_filter_news(items, keyword, start_dt, end_dt):
    parsed_items = []
    for item in items:
        try:
            pub_date_str = item.pubDate.text
            pub_date_utc = pd.to_datetime(pub_date_str).replace(tzinfo=timezone.utc)
            pub_date_kst = pub_date_utc + timedelta(hours=9)
            pub_date_kst_naive = pub_date_kst.replace(tzinfo=None)
            
            # 본문 추출 및 정리 (데이터 품질 확보)
            raw_desc = item.description.text if item.description else ""
            clean_snip = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)
            
            # 본문이 너무 짧으면 제목으로 대체 (AI 인식률 향상)
            if len(clean_snip) < 10:
                clean_snip = item.title.text

            if start_dt <= pub_date_kst_naive <= end_dt:
                src = item.source.text if item.source else "Google"
                parsed_items.append({
                    'Title': item.title.text,
                    'Source': src,
                    'Date': pub_date_kst_naive,
                    'Link': item.link.text,
                    'Keyword': keyword,
                    'Snippet': clean_snip[:500], # 길이 제한
                    'Country': 'KR'
                })
        except Exception: continue
    return parsed_items

def generate_daily_report_process(target_date, keywords, api_key):
    # [상태 관리용 컨테이너]
    status_box = st.status("🚀 리포트 생성 프로세스 시작...", expanded=True)
    
    # 1. 시간 설정
    end_dt = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6)
    start_dt = end_dt - timedelta(hours=18)
    
    status_box.write(f"⏱️ 수집 기준: {start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')} (KST)")
    
    all_news = []
    
    # 2. 수집 단계 (Progress bar)
    progress_bar = status_box.empty()
    log_area = status_box.empty()
    
    logs = []
    
    for idx, kw in enumerate(keywords):
        progress = (idx + 1) / len(keywords)
        # 프로그레스 바는 status box 안에는 못 넣으므로 텍스트로 대체
        
        items = fetch_rss_feed(kw, days_back=2)
        filtered = parse_and_filter_news(items, kw, start_dt, end_dt)
        
        if len(filtered) == 0:
            # Fallback: 시간 조건 완화 (24시간)
            fallback_items = parse_and_filter_news(items, kw, end_dt - timedelta(hours=24), end_dt + timedelta(hours=24))
            if fallback_items:
                logs.append(f"⚠️ [{kw}] 0건 -> 범위확장 수집: {len(fallback_items)}건")
                all_news.extend(fallback_items)
            else:
                logs.append(f"❌ [{kw}] 관련 기사 없음")
        else:
            logs.append(f"✅ [{kw}] {len(filtered)}건 수집 성공")
            all_news.extend(filtered)
            
        # 최신 3개 로그만 보여주기
        log_text = "<br>".join([f"<div class='status-log'>{l}</div>" for l in logs[-3:]])
        log_area.markdown(log_text, unsafe_allow_html=True)
        time.sleep(0.1)

    if not all_news:
        status_box.update(label="❌ 수집된 기사가 없습니다.", state="error")
        return [], None

    # 3. 데이터 분석 단계
    df = pd.DataFrame(all_news)
    df = df.drop_duplicates(subset=['Title']).sort_values(by='Date', ascending=False)
    final_articles = df.head(30).to_dict('records') # 30개로 제한
    
    status_box.write(f"🧠 AI 분석 시작 (기사 {len(final_articles)}건)...")
    
    # 4. 리포트 작성 단계
    try:
        model = get_gemini_model(api_key)
        
        context = ""
        for i, item in enumerate(final_articles):
            d_str = item['Date'].strftime('%H:%M')
            # 제목과 요약을 명확히 구분
            context += f"기사{i+1}: [{d_str}] {item['Title']}\n내용: {item['Snippet']}\n\n"
            
        prompt = f"""
        당신은 한국 반도체 산업 전문 애널리스트입니다.
        아래는 오늘 수집된 주요 반도체 뉴스들입니다. 이를 바탕으로 '일일 브리핑 리포트'를 작성해주세요.
        
        [작성 원칙]
        1. 한국어로 작성할 것.
        2. 중복된 내용은 통합하여 요약할 것.
        3. 단순 나열이 아닌 '인사이트' 위주로 작성할 것.
        
        [리포트 포맷]
        ## 📊 Executive Summary
        (오늘의 핵심 흐름을 3문장으로 요약)
        
        ## 🚨 Headline Issues
        (가장 중요한 이슈 3가지 선정 및 상세 분석)
        
        ## 📉 Market & Tech
        (기업 동향, 기술 개발, 공급망 이슈 정리)
        
        ## 💡 Analyst Insight
        (오늘 뉴스가 시장에 미치는 영향 한 줄 평)

        [수집된 뉴스 데이터]
        {context}
        """
        
        response = model.generate_content(prompt)
        
        if response.text:
            report_text = response.text
            status_box.update(label="🎉 리포트 생성 완료!", state="complete", expanded=False)
            
            save_data = {
                'date': target_date.strftime('%Y-%m-%d'),
                'report': report_text,
                'articles': final_articles
            }
            save_daily_history(save_data)
            return final_articles, report_text
        else:
            raise Exception("AI 응답이 비어있습니다 (Safety Filter 가능성).")
            
    except Exception as e:
        status_box.update(label="⚠️ 리포트 생성 실패", state="error")
        st.error(f"오류 상세: {str(e)}")
        # 실패해도 수집된 기사는 보여줌
        return final_articles, None

def perform_crawling_general(category, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    prog = st.progress(0)
    all_res = []
    
    def crawl_simple(kw, cc, lang):
        url = f"https://news.google.com/rss/search?q={quote(kw)}&hl={lang}&gl={cc}&ceid={cc}:{lang}"
        try:
            r = requests.get(url, timeout=5, verify=False)
            if r.status_code == 200:
                s = BeautifulSoup(r.content, 'xml')
                items = s.find_all('item')[:3]
                parsed = []
                for it in items:
                    parsed.append({
                        'Title': it.title.text, 'Source': "Google", 'Date': datetime.now(),
                        'Link': it.link.text, 'Keyword': kw, 'Snippet': "", 'AI_Verified': False
                    })
                return parsed
        except: return []
        return []

    for i, kw in enumerate(kws):
        prog.progress((i+1)/len(kws))
        all_res.extend(crawl_simple(kw, 'KR', 'ko'))
        all_res.extend(crawl_simple(kw, 'US', 'en'))
        time.sleep(0.1)
    prog.empty()
    
    if all_res:
        df = pd.DataFrame(all_res)
        df = df.drop_duplicates('Title')
        final_list = df.head(40).to_dict('records')
        if api_key: final_list = filter_with_gemini(final_list, api_key)
        st.session_state.news_data[category] = final_list
    else:
        st.session_state.news_data[category] = []

# ==========================================
# 4. 앱 초기화
# ==========================================
if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None
if 'daily_history' not in st.session_state: st.session_state.daily_history = load_daily_history()

# ==========================================
# 5. UI Layout
# ==========================================
with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    selected_category = st.radio("카테고리", CATEGORIES, index=len(CATEGORIES)-1, label_visibility="collapsed")
    st.divider()
    with st.expander("🔐 API Key"):
        api_key = st.text_input("Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.caption("Loaded")
    st.markdown("---")
    with st.expander("📉 Global Stock", expanded=True):
        stock_map = get_stock_prices_grouped()
        if stock_map:
            for cat_name, items in STOCK_CATEGORIES.items():
                st.markdown(f"<div class='stock-header'>{cat_name}</div>", unsafe_allow_html=True)
                for name, symbol in items.items():
                    data = stock_map.get(symbol)
                    if data:
                        sc1, sc2 = st.columns([1, 1.2])
                        with sc1: st.caption(f"**{name}**")
                        with sc2: st.metric("", data['Price'], data['Delta'], label_visibility="collapsed")
                        st.markdown("<hr style='margin: 2px 0; border-top: 1px dashed #f1f5f9;'>", unsafe_allow_html=True)

c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

if selected_category == "Daily Report":
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_date = (now_kst - timedelta(days=1)).date() if now_kst.hour < 6 else now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Report Date (KST)<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("##### ⚙️ Settings (Korea Focus)")
        c_k1, c_k2 = st.columns([3, 1])
        with c_k1: new_kw = st.text_input("키워드 추가", label_visibility="collapsed")
        with c_k2:
            if st.button("추가", use_container_width=True):
                if new_kw and new_kw not in st.session_state.keywords["Daily Report"]:
                    st.session_state.keywords["Daily Report"].append(new_kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            cols = st.columns(8)
            for i, kw in enumerate(daily_kws):
                if cols[i%8].button(f"{kw} ×", key=f"d_{kw}", type="secondary"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()

    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if today_report:
        st.success(f"✅ {target_date} 리포트가 이미 발행되었습니다.")
    else:
        st.info(f"📢 {target_date} 리포트가 없습니다.")
        if api_key:
            if st.button("🚀 리포트 생성 시작 (전일 12:00 ~ 금일 06:00)", type="primary"):
                _, _ = generate_daily_report_process(target_date, daily_kws, api_key)
                st.rerun()
        else:
            st.error("API Key가 필요합니다.")

    if history:
        for idx, entry in enumerate(history):
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            if entry.get('report'):
                st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            else:
                st.warning("리포트 내용이 없습니다.")
                
            with st.expander(f"🔗 Reference Articles ({len(entry.get('articles', []))})"):
                for i, item in enumerate(entry.get('articles', [])):
                    d_str = pd.to_datetime(item['Date']).strftime('%m/%d %H:%M')
                    st.markdown(f"{i+1}. **[{item['Title']}]({item['Link']})** <span style='color:#999; font-size:0.8em'> | {item['Source']} ({d_str})</span>", unsafe_allow_html=True)

else:
    with c_info: 
        if st.session_state.last_update:
            st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Updated: {st.session_state.last_update}</div>", unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 2.5, 1])
        with c1: st.write("")
        with c2: new_kw = st.text_input("키워드", placeholder="예: HBM", label_visibility="collapsed")
        with c3:
            b1, b2 = st.columns(2)
            with b1:
                if st.button("추가", use_container_width=True):
                    if new_kw:
                        st.session_state.keywords[selected_category].append(new_kw)
                        save_keywords(st.session_state.keywords)
                        st.rerun()
            with b2:
                if st.button("실행", type="primary", use_container_width=True):
                    perform_crawling_general(selected_category, api_key)
                    st.session_state.last_update = datetime.now().strftime("%H:%M")
                    st.rerun()
        curr_kws = st.session_state.keywords.get(selected_category, [])
        if curr_kws:
            st.write("")
            cols = st.columns(8)
            for i, kw in enumerate(curr_kws):
                if cols[i%8].button(f"{kw} ×", key=f"d_{kw}", type="secondary"):
                    st.session_state.keywords[selected_category].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
    data = st.session_state.news_data.get(selected_category, [])
    if data:
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Collected", len(data))
        st.markdown("<br>", unsafe_allow_html=True)
        for i in range(0, len(data), 2):
            row_items = data[i : i+2]
            cols = st.columns(2)
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"""<div class="news-meta" style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>📰 {item['Source']}</span><span>{item['Date'].strftime('%Y-%m-%d')}</span></div>""", unsafe_allow_html=True)
                        st.markdown(f'<a href="{item["Link"]}" target="_blank" class="news-title">{item["Title"]}</a>', unsafe_allow_html=True)
                        if item.get('Snippet'): st.markdown(f'<div class="news-snippet">{item["Snippet"]}</div>', unsafe_allow_html=True)
                        st.markdown("---")
                        st.markdown(f"<span style='background:#F1F5F9; color:#64748B; padding:3px 8px; border-radius:4px; font-size:11px;'>#{item['Keyword']}</span>", unsafe_allow_html=True)
    else:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding:30px; color:#999;'>데이터가 없습니다.<br>상단의 '실행' 버튼을 눌러주세요.</div>", unsafe_allow_html=True)
