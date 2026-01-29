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

# [필수] 라이브러리
import yfinance as yf
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 Modern CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            background-color: #F8FAFC;
            color: #1E293B;
        }
        .stApp { background-color: #F8FAFC; }

        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-title:hover { color: #2563EB !important; text-decoration: underline; }
        .news-snippet { font-size: 13.5px !important; color: #475569 !important; line-height: 1.5; margin-bottom: 10px; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }

        .control-box { background-color: #FFFFFF; padding: 15px 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 20px; }
        
        button[kind="secondary"] { height: 28px !important; font-size: 12px !important; padding: 0 10px !important; border-radius: 14px !important; }

        div[data-testid="stMetricValue"] { font-size: 13px !important; }
        div[data-testid="stMetricDelta"] { font-size: 11px !important; }
        div[data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 600; color: #64748B; }
        .stock-header { font-size: 12px; font-weight: 700; color: #475569; margin-top: 15px; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }

        .report-box {
            background-color: #FFFFFF;
            padding: 40px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            line-height: 1.8;
            color: #334155;
        }
        .report-header {
            border-bottom: 2px solid #3B82F6;
            padding-bottom: 15px;
            margin-bottom: 25px;
            font-size: 1.8em;
            font-weight: 800;
            color: #1E3A8A;
        }
        .history-header {
            font-size: 1.2em;
            font-weight: 700;
            color: #475569;
            margin-top: 50px;
            margin-bottom: 20px;
            border-left: 5px solid #CBD5E1;
            padding-left: 10px;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package", "Daily Report"
]

DAILY_DEFAULT_KEYWORDS = [
    "반도체 소재", "소재 공급망", "희토류 제한", "EUV", 
    "중국 반도체", "일본 반도체", "중국 광물", "반도체 규제"
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
# 1. 주식 데이터 관리
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
                    
                    if ".KS" in symbol: currency = "₩"
                    elif ".T" in symbol: currency = "¥"
                    elif ".HK" in symbol: currency = "HK$"
                    elif ".DE" in symbol or ".PA" in symbol: currency = "€"
                    else: currency = "$"
                    
                    price_str = f"{currency}{current:,.0f}" if currency in ["₩", "¥"] else f"{currency}{current:,.2f}"
                    delta_str = f"{change:,.2f} ({pct_change:+.2f}%)"
                    result_map[symbol] = {"Price": price_str, "Delta": delta_str}
            except: pass
    except: pass
    return result_map

# ==========================================
# 2. 파일 I/O 및 데이터 관리
# ==========================================
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
    # 날짜 중복 시 덮어쓰기
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data) 
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass
    return history

def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-pro')

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        model = get_gemini_model(api_key)
        content_text = ""
        for i, item in enumerate(articles[:20]): 
            safe_snip = re.sub(r'[^\w\s]', '', item.get('Snippet', ''))[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {safe_snip}\n"
        prompt = f"Role: Analyst. Task: Filter noise. Output: IDs ONLY (e.g., 1, 3). Data:\n{content_text}"
        response = model.generate_content(prompt)
        nums = re.findall(r'\d+', response.text)
        valid_indices = [int(n)-1 for n in nums]
        filtered = []
        for idx in valid_indices:
            if 0 <= idx < len(articles):
                articles[idx]['AI_Verified'] = True
                filtered.append(articles[idx])
        return filtered if filtered else articles
    except: return articles

# ==========================================
# 3. Daily Report 전용 크롤러 (로직 수정됨)
# ==========================================
def crawl_korean_daily(keyword, start_dt_kst, end_dt_kst):
    # [조건 1] 한국 웹사이트 중심 (검색어 뒤에 when:1d 추가하여 최신성 확보)
    url = f"https://news.google.com/rss/search?q={quote(keyword)}+when:2d&hl=ko&gl=KR&ceid=KR:ko"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            parsed = []
            for item in items:
                try: 
                    # RSS 날짜는 GMT 기준임. KST로 변환해야 함.
                    pub_date_str = item.pubDate.text
                    # 포맷 예: Fri, 02 Feb 2024 08:00:00 GMT
                    pub_date_utc = pd.to_datetime(pub_date_str).replace(tzinfo=timezone.utc)
                    pub_date_kst = pub_date_utc + timedelta(hours=9)
                    
                    # timezone-aware끼리 비교하기 위해 naive로 통일 (비교 편의성)
                    pub_date_kst_naive = pub_date_kst.replace(tzinfo=None)
                    
                except: 
                    # 날짜 파싱 실패시 현재 시간으로 가정 (데이터 유실 방지)
                    pub_date_kst_naive = datetime.now() + timedelta(hours=9)

                # [조건 2] 수집 기간: 전일 12:00 ~ 금일 06:00
                if start_dt_kst <= pub_date_kst_naive <= end_dt_kst:
                    src = item.source.text if item.source else "Google"
                    snip = BeautifulSoup(item.description.text if item.description else "", "html.parser").get_text(strip=True)[:300]
                    
                    parsed.append({
                        'Title': item.title.text,
                        'Source': src,
                        'Date': pub_date_kst_naive,
                        'Link': item.link.text,
                        'Keyword': keyword,
                        'Snippet': snip,
                        'Country': 'KR'
                    })
            return parsed
    except Exception as e:
        print(f"Crawl Error: {e}")
        pass
    return []

# [핵심] 리포트 생성 프로세스
def generate_daily_report_process(target_date_kst, keywords, api_key):
    # 진행 상황 UI
    status_box = st.status("🚀 리포트 생성 작업을 시작합니다...", expanded=True)
    
    # [조건 2] 시간 설정 (KST 기준)
    # target_date_kst는 '오늘 날짜'임.
    # 종료: 오늘 06:00
    end_dt = datetime.combine(target_date_kst, datetime.min.time()) + timedelta(hours=6)
    # 시작: 어제 12:00 (18시간 전)
    start_dt = end_dt - timedelta(hours=18)
    
    status_box.write(f"📅 수집 구간: {start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')} (KST)")
    
    all_news = []
    total_kws = len(keywords)
    
    # 1. 크롤링
    for idx, kw in enumerate(keywords):
        status_box.write(f"running... [{idx+1}/{total_kws}] 키워드 검색: {kw}")
        items = crawl_korean_daily(kw, start_dt, end_dt)
        all_news.extend(items)
        time.sleep(0.3) # 차단 방지 딜레이
            
    if not all_news:
        status_box.update(label="❌ 수집된 기사가 없습니다.", state="error")
        return [], None

    # 2. 데이터 정리
    df = pd.DataFrame(all_news)
    df = df.drop_duplicates(subset=['Title'])
    df = df.sort_values(by='Date', ascending=False)
    
    # AI에게 보낼 기사 선정 (최대 40개)
    final_articles = df.head(40).to_dict('records')
    status_box.write(f"✅ 총 {len(final_articles)}건의 유효 기사 수집 완료. AI 분석 시작...")
    
    # 3. 리포트 생성
    try:
        model = get_gemini_model(api_key)
        
        context = ""
        for i, item in enumerate(final_articles):
            date_str = item['Date'].strftime('%H:%M')
            context += f"- [{date_str}] {item['Title']} ({item['Source']}): {item.get('Snippet', '')}\n"
            
        prompt = f"""
        당신은 대한민국 최고의 반도체 산업 애널리스트입니다.
        제공된 뉴스 데이터는 **{start_dt.strftime('%Y-%m-%d %H:%M')}부터 {end_dt.strftime('%Y-%m-%d %H:%M')}까지** 수집된 한국 기사입니다.
        
        이 정보를 바탕으로 **[일일 반도체 산업 브리핑]**을 작성하세요.
        
        [뉴스 데이터]
        {context}
        
        [작성 양식 (Markdown)]
        ## 📊 Executive Summary
        (전체 흐름을 3문장으로 요약)
        
        ## 🚨 주요 이슈 (Key Headlines)
        (가장 중요한 기사 3개를 선정하여 심층 분석)
        
        ## 📉 시장 및 공급망 동향
        (소재, 부품, 장비 및 기업 동향 정리)
        
        ## 💡 Analyst Insight
        (투자자 및 업계 관계자를 위한 한 줄 평)
        """
        
        response = model.generate_content(prompt)
        report_text = response.text
        
        # 4. 저장 (날짜 기준)
        save_data = {
            'date': target_date_kst.strftime('%Y-%m-%d'),
            'report': report_text,
            'articles': final_articles
        }
        save_daily_history(save_data)
        
        status_box.update(label="🎉 리포트 생성이 완료되었습니다!", state="complete", expanded=False)
        return final_articles, report_text
        
    except Exception as e:
        status_box.update(label="⚠️ 리포트 생성 중 오류 발생", state="error")
        st.error(f"Error Details: {str(e)}")
        return final_articles, None

# 일반 크롤링 (기존 유지)
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

if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None
if 'daily_history' not in st.session_state: st.session_state.daily_history = load_daily_history()

# ==========================================
# 3. Sidebar
# ==========================================
with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    # [조건 5] Daily Report가 포함된 카테고리 선택
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
        else:
            st.caption("Loading...")

# ==========================================
# 4. Main UI & Logic
# ==========================================
c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

# ----------------------------------------------------------------
# [Logic A] Daily Report 모드
# ----------------------------------------------------------------
if selected_category == "Daily Report":
    # 1. 타겟 날짜 계산 (KST 기준)
    # Streamlit Cloud는 UTC이므로 +9시간 보정
    now_kst = datetime.utcnow() + timedelta(hours=9)
    
    # 06시 기준: 06시 이전이면 '어제', 06시 이후면 '오늘'이 타겟
    if now_kst.hour < 6:
        target_date = (now_kst - timedelta(days=1)).date()
    else:
        target_date = now_kst.date()
        
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Report Date (KST)<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    # 2. 키워드 설정
    with st.container(border=True):
        st.markdown("##### ⚙️ Report Settings (Korea Focus)")
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

    # 3. 리포트 로직
    history = load_daily_history()
    # [조건 4] 1일 1회 작성 원칙 (이미 있으면 생성 안함)
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    # 리포트가 없으면 -> 생성 버튼 표시
    if not today_report:
        st.info(f"📢 {target_date} 리포트가 아직 생성되지 않았습니다.")
        
        if api_key:
            if st.button("🚀 금일 리포트 생성 (전일 12:00 ~ 금일 06:00 수집)", type="primary"):
                _, _ = generate_daily_report_process(target_date, daily_kws, api_key)
                st.rerun()
        else:
            st.error("API Key가 필요합니다.")
            
    # 4. 리포트 출력 (누적 표시)
    if not history:
        st.write("")
    else:
        for idx, entry in enumerate(history):
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            # [조건 3] References 하단 기록
            with st.expander(f"🔗 Reference Articles ({len(entry.get('articles', []))})"):
                for i, item in enumerate(entry.get('articles', [])):
                    st.markdown(f"{i+1}. [{item['Title']}]({item['Link']}) <span style='color:#999; font-size:0.8em'> | {item['Source']} - {item['Date']}</span>", unsafe_allow_html=True)

# ----------------------------------------------------------------
# [Logic B] 일반 카테고리 (수동 실행)
# ----------------------------------------------------------------
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
