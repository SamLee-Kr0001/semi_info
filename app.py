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
import yfinance as yf

# ==========================================
# 0. 페이지 설정 및 Modern CSS (주식 폰트 강력 수정)
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        
        .report-box { background-color: #FFFFFF; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; }
        .history-header { font-size: 1.2em; font-weight: 700; color: #475569; margin-top: 50px; margin-bottom: 20px; border-left: 5px solid #CBD5E1; padding-left: 10px; }
        .status-log { font-family: monospace; font-size: 0.85em; color: #334155; background: #F1F5F9; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #3B82F6; }
        
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-title:hover { color: #2563EB !important; text-decoration: underline; }
        .news-snippet { font-size: 13.5px !important; color: #475569 !important; line-height: 1.5; margin-bottom: 10px; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }

        /* [수정] 사이드바 주식 폰트 강제 고정 (더 구체적인 선택자 사용) */
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
            font-size: 18px !important; /* 크기 강제 조절 */
            font-weight: 600 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stMetricDelta"] {
            font-size: 12px !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] {
            font-size: 12px !important;
            color: #64748B !important;
        }
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
    try: with open(KEYWORD_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def load_daily_history():
    if os.path.exists(HISTORY_FILE):
        try: with open(HISTORY_FILE, 'r', encoding='utf-8') as f: return json.load(f) 
        except: return []
    return []

def save_daily_history(new_report_data):
    history = load_daily_history()
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data) 
    try: with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass
    return history

def clean_text(text):
    if not text: return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s\.,%]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==========================================
# [핵심] REST API 방식 AI 호출 (라이브러리 미사용)
# ==========================================
def generate_content_rest_api(api_key, prompt):
    """
    Python 라이브러리(google-generativeai)를 쓰지 않고,
    HTTP 요청을 직접 보내서 404 에러와 버전 문제를 원천 차단함.
    """
    # 1순위: 1.5-flash, 2순위: 1.0-pro (엔드포인트 직접 지정)
    models = ["gemini-1.5-flash", "gemini-pro"]
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                # 응답 파싱
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"Model {model} failed: {response.text}")
                continue # 다음 모델 시도
        except Exception as e:
            print(f"Connection error with {model}: {e}")
            continue
            
    return None # 모든 모델 실패

# ==========================================
# 3. 크롤링 및 리포트 로직
# ==========================================

def fetch_rss_feed(keyword, days_back=2):
    url = f"https://news.google.com/rss/search?q={quote(keyword)}+when:{days_back}d&hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
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
            
            raw_desc = item.description.text if item.description else ""
            clean_snip = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)
            clean_snip = clean_text(clean_snip)
            if len(clean_snip) < 10: clean_snip = item.title.text

            if start_dt <= pub_date_kst_naive <= end_dt:
                src = item.source.text if item.source else "Google"
                parsed_items.append({
                    'Title': clean_text(item.title.text),
                    'Source': src,
                    'Date': pub_date_kst_naive,
                    'Link': item.link.text,
                    'Keyword': keyword,
                    'Snippet': clean_snip[:300], 
                    'Country': 'KR'
                })
        except Exception: continue
    return parsed_items

def generate_daily_report_process(target_date, keywords, api_key):
    status_box = st.status("🚀 리포트 생성 프로세스 시작...", expanded=True)
    
    end_dt = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6)
    start_dt = end_dt - timedelta(hours=18)
    
    status_box.write(f"⏱️ 수집 기준: {start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')} (KST)")
    
    all_news = []
    logs = []
    log_area = status_box.empty()
    
    # 1. 수집
    for idx, kw in enumerate(keywords):
        items = fetch_rss_feed(kw, days_back=2)
        filtered = parse_and_filter_news(items, kw, start_dt, end_dt)
        
        if len(filtered) == 0:
            fallback_items = parse_and_filter_news(items, kw, end_dt - timedelta(hours=24), end_dt + timedelta(hours=24))
            if fallback_items:
                logs.append(f"⚠️ [{kw}] 0건 -> 범위확장: {len(fallback_items)}건")
                all_news.extend(fallback_items)
            else:
                logs.append(f"❌ [{kw}] 기사 없음")
        else:
            logs.append(f"✅ [{kw}] {len(filtered)}건 수집")
            all_news.extend(filtered)
            
        log_html = "<br>".join([f"<div class='status-log'>{l}</div>" for l in logs[-4:]])
        log_area.markdown(log_html, unsafe_allow_html=True)
        time.sleep(0.1)

    if not all_news:
        status_box.update(label="❌ 기사 수집 실패: 해당 기간에 뉴스가 없습니다.", state="error")
        return None

    # 2. 전처리
    df = pd.DataFrame(all_news)
    df = df.drop_duplicates(subset=['Title']).sort_values(by='Date', ascending=False)
    final_articles = df.head(25).to_dict('records') # 25개로 제한
    
    status_box.write(f"🧠 총 {len(final_articles)}건의 기사를 AI가 분석 중입니다...")
    
    # 3. 리포트 작성 (REST API 호출)
    try:
        context = ""
        for i, item in enumerate(final_articles):
            d_str = item['Date'].strftime('%H:%M')
            context += f"News {i+1}: {item['Title']}\nSummary: {item['Snippet']}\n\n"
            
        prompt = f"""
        당신은 한국 반도체 산업 전문 애널리스트입니다. 
        아래 뉴스 데이터를 바탕으로 [일일 반도체 산업 브리핑]을 작성하세요.
        한국어로 작성하고, 인사이트 위주로 요약하세요.
        
        [리포트 포맷]
        ## 📊 Executive Summary (3줄 요약)
        ## 🚨 Top Headlines (핵심 이슈 3가지)
        ## 📉 Market & Supply Chain (시장/공급망 동향)
        ## 💡 Analyst Insight (종합 의견)

        [뉴스 데이터]
        {context}
        """
        
        # [변경] 라이브러리 대신 REST API 함수 사용
        report_text = generate_content_rest_api(api_key, prompt)
        
        if report_text:
            save_data = {
                'date': target_date.strftime('%Y-%m-%d'),
                'report': report_text,
                'articles': final_articles
            }
            save_daily_history(save_data)
            status_box.update(label="🎉 리포트 생성 완료!", state="complete", expanded=False)
            return save_data
        else:
            raise Exception("AI 응답 없음 (모든 모델 실패 또는 API Key 문제)")
            
    except Exception as e:
        status_box.update(label="⚠️ AI 분석 실패", state="error")
        st.error(f"Error: {str(e)}")
        # 실패하더라도 수집 목록은 저장 및 반환
        save_data = {
            'date': target_date.strftime('%Y-%m-%d'),
            'report': f"⚠️ **분석 실패**: {str(e)}",
            'articles': final_articles
        }
        return save_data

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
            
    # [연결 테스트 - REST API 방식]
    if st.button("🤖 AI 연결 확인", type="secondary", use_container_width=True):
        if not api_key:
            st.error("API Key 없음")
        else:
            res = generate_content_rest_api(api_key, "Hi")
            if res: st.success("연결 성공! (REST API)")
            else: st.error("연결 실패 (키 확인 필요)")

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
        if st.button("🔄 리포트 다시 생성하기"):
             result = generate_daily_report_process(target_date, daily_kws, api_key)
             if result: st.rerun()
    else:
        st.info(f"📢 {target_date} 리포트가 없습니다.")
        if api_key:
            if st.button("🚀 리포트 생성 시작 (전일 12:00 ~ 금일 06:00)", type="primary"):
                result = generate_daily_report_process(target_date, daily_kws, api_key)
                if result: st.rerun()
        else:
            st.error("API Key가 필요합니다.")

    if history:
        for idx, entry in enumerate(history):
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            if entry.get('report'):
                st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
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
