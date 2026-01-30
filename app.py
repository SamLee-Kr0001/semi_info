import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import re
import time
import yfinance as yf

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 0. 페이지 설정 및 스타일
# ==========================================
st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        
        /* 리포트 스타일 */
        .report-box { background-color: #FFFFFF; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; }
        .history-header { font-size: 1.2em; font-weight: 700; color: #475569; margin-top: 50px; margin-bottom: 20px; border-left: 5px solid #3B82F6; padding-left: 10px; }
        
        /* 뉴스 카드 스타일 */
        .news-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 10px; }
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-title:hover { color: #2563EB !important; text-decoration: underline; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }

        /* 사이드바 주식 폰트 강제 고정 */
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 600 !important; }
        section[data-testid="stSidebar"] div[data-testid="stMetricDelta"] { font-size: 12px !important; }
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] { font-size: 12px !important; color: #64748B !important; }
        .stock-header { font-size: 13px; font-weight: 700; color: #475569; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }
    </style>
""", unsafe_allow_html=True)

# 기본값 설정
FALLBACK_API_KEY = "AIzaSyCBSqIQBIYQbWtfQAxZ7D5mwCKFx-7VDJo"
CATEGORIES = ["Daily Report", "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", "Process Gas", "Wafer", "Package"]

# [요청하신 종목 원복]
STOCK_CATEGORIES = {
    "🏭 Chipmakers": {
        "Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU",
        "TSMC": "TSM", "Intel": "INTC", "SMIC": "0981.HK"
    },
    "🧠 Fabless": {
        "Nvidia": "NVDA", "Broadcom": "AVGO", "Qnity (Q)": "Q" 
    },
    "⚙️ Equipment": {
        "ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", 
        "TEL": "8035.T", "KLA": "KLAC", "Hanmi": "042700.KS", "Jusung": "036930.KS"
    },
    "🧪 Materials": {
        "Shin-Etsu": "4063.T", "Sumitomo": "4005.T", "TOK": "4186.T", 
        "Nissan Chem": "4021.T", "Merck": "MRK.DE", "Air Liquide": "AI.PA", 
        "Linde": "LIN", "Soulbrain": "357780.KS", "Dongjin": "005290.KS", 
        "ENF": "102710.KS", "Ycchem": "232140.KS"
    },
    "🔋 Others": {
        "Samsung SDI": "006400.KS"
    }
}

# ==========================================
# 1. 데이터 관리 (키워드, 히스토리, 주식)
# ==========================================
KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json'

@st.cache_data(ttl=600)
def get_stock_prices_grouped():
    all_tickers = []
    for cat in STOCK_CATEGORIES.values(): all_tickers.extend(cat.values())
    ticker_str = " ".join(all_tickers)
    result_map = {}
    try:
        stocks = yf.Tickers(ticker_str)
        for symbol in all_tickers:
            try:
                hist = stocks.tickers[symbol].history(period="5d")
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change = current - prev
                    pct = (change / prev) * 100
                    cur_sym = "₩" if ".KS" in symbol else ("¥" if ".T" in symbol else ("HK$" if ".HK" in symbol else ("€" if ".DE" in symbol or ".PA" in symbol else "$")))
                    fmt_price = f"{cur_sym}{current:,.0f}" if cur_sym in ["₩", "¥"] else f"{cur_sym}{current:,.2f}"
                    result_map[symbol] = {"Price": fmt_price, "Delta": f"{change:,.2f} ({pct:+.2f}%)"}
            except: pass
    except: pass
    return result_map

def load_keywords():
    data = {cat: [] for cat in CATEGORIES}
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in data: data[k] = v
        except: pass
    if not data.get("Daily Report"): 
        data["Daily Report"] = ["반도체", "삼성전자", "SK하이닉스"] 
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
    # 날짜 중복 시 덮어쓰기 (항상 최신 날짜가 맨 위로 오도록)
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data)
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass

# ==========================================
# 2. [성공한 로직] AI 모델 자동 탐색 및 생성
# ==========================================
def get_available_models(api_key):
    """현재 API Key로 사용 가능한 모델 리스트 조회"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [m['name'].replace("models/", "") for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    except: pass
    return []

def generate_report_with_auto_model(api_key, news_data):
    """모델 리스트를 순회하며 429/404 회피"""
    models = get_available_models(api_key)
    
    # 조회 실패 시 기본 모델셋 (성공 확률 높은 순)
    if not models:
        models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    prompt = f"""
    당신은 대한민국 최고의 반도체 산업 애널리스트입니다.
    아래 수집된 뉴스들을 종합하여 **[일일 반도체 산업 브리핑]**을 작성하세요.
    
    [뉴스 데이터]
    {chr(10).join(news_data)}
    
    [작성 양식 (Markdown)]
    ## 📊 Executive Summary
    (오늘의 핵심 흐름을 3문장으로 요약)
    
    ## 🚨 Key Headlines
    (가장 중요한 이슈 3가지 선정 및 심층 분석)
    
    ## 📉 Market & Supply Chain Insight
    (기업 동향, 소부장 이슈, 향후 시장 전망)
    """
    
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

    for model in models:
        if "vision" in model: continue # 텍스트 전용
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                res_json = response.json()
                if 'candidates' in res_json and res_json['candidates']:
                    return True, res_json['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                time.sleep(1) 
                continue
        except: continue
            
    return False, "AI 분석에 실패했습니다. (서버 과부하 또는 사용량 초과)"

# ==========================================
# 3. 뉴스 크롤링
# ==========================================
def fetch_news(keywords, days=1, limit=15):
    all_items = []
    
    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={quote(kw)}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            for item in items:
                all_items.append({
                    'Title': item.title.text,
                    'Link': item.link.text,
                    'Date': item.pubDate.text,
                    'Source': item.source.text if item.source else "Google News"
                })
        except: pass
        time.sleep(0.1)
        
    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['Title'])
        return df.head(limit).to_dict('records')
    return []

# ==========================================
# 4. 메인 앱 UI
# ==========================================
if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()

# [사이드바]
with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    selected_category = st.radio("카테고리", CATEGORIES, index=0, label_visibility="collapsed")
    st.divider()
    
    with st.expander("🔐 API Key"):
        user_key = st.text_input("Key", type="password")
        if user_key: api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
        else: api_key = FALLBACK_API_KEY
    
    st.markdown("---")
    # [주식 정보 표시]
    with st.expander("📉 Global Stock", expanded=True):
        stock_data = get_stock_prices_grouped()
        if stock_data:
            for cat, items in STOCK_CATEGORIES.items():
                st.markdown(f"<div class='stock-header'>{cat}</div>", unsafe_allow_html=True)
                for name, symbol in items.items():
                    info = stock_data.get(symbol)
                    if info:
                        c1, c2 = st.columns([1, 1.3])
                        c1.caption(f"**{name}**")
                        c2.metric("", info['Price'], info['Delta'], label_visibility="collapsed")
                        st.markdown("<hr style='margin: 2px 0; border-top: 1px dashed #f1f5f9;'>", unsafe_allow_html=True)

# [메인 화면]
c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

# ----------------------------------
# [Mode 1] Daily Report (06시 기준)
# ----------------------------------
if selected_category == "Daily Report":
    # 시간 계산 (KST 기준)
    now_kst = datetime.utcnow() + timedelta(hours=9)
    # 06시 이전이면 어제 날짜, 06시 이후면 오늘 날짜
    if now_kst.hour < 6:
        target_date = (now_kst - timedelta(days=1)).date()
    else:
        target_date = now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; color:#888;'>Target Date<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    # 1. 키워드 설정
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        new_kw = c1.text_input("수집 키워드 추가", placeholder="예: HBM, 패키징", label_visibility="collapsed")
        if c2.button("추가", use_container_width=True):
            if new_kw and new_kw not in st.session_state.keywords["Daily Report"]:
                st.session_state.keywords["Daily Report"].append(new_kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
        
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            cols = st.columns(len(daily_kws) if len(daily_kws) < 8 else 8)
            for i, kw in enumerate(daily_kws):
                if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
    
    # 2. 리포트 관리
    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    # 리포트가 없으면 생성 버튼 표시
    if not today_report:
        st.info(f"📢 {target_date} 리포트가 아직 생성되지 않았습니다.")
        if st.button("🚀 금일 리포트 생성 시작", type="primary"):
            status_box = st.status("🚀 리포트 생성 프로세스...", expanded=True)
            
            # 수집
            status_box.write(f"📡 '{', '.join(daily_kws)}' 뉴스 수집 중...")
            news_items = fetch_news(daily_kws, days=1) # 1일치 (06시 기준이므로 대략 맞음)
            
            if not news_items:
                status_box.update(label="❌ 수집된 뉴스가 없습니다.", state="error")
            else:
                # 분석
                status_box.write(f"🧠 AI 분석 및 요약 중... (기사 {len(news_items)}건)")
                news_texts = [f"- {item['Title']}" for item in news_items]
                success, result = generate_report_with_auto_model(api_key, news_texts)
                
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 리포트 생성 완료!", state="complete")
                    st.rerun()
                else:
                    status_box.update(label="⚠️ AI 분석 실패", state="error")
                    st.error(result)
    
    # 이미 생성된 경우 재생성 옵션
    else:
        st.success(f"✅ {target_date} 리포트가 완료되었습니다.")
        if st.button("🔄 리포트 다시 만들기 (덮어쓰기)"):
            status_box = st.status("🚀 리포트 재생성 중...", expanded=True)
            news_items = fetch_news(daily_kws)
            if news_items:
                news_texts = [f"- {item['Title']}" for item in news_items]
                success, result = generate_report_with_auto_model(api_key, news_texts)
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 재생성 완료!", state="complete")
                    st.rerun()

    # 3. 히스토리 출력 (누적)
    if history:
        for entry in history:
            st.divider()
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            # [요청사항] Reference Links
            with st.expander(f"🔗 Reference Articles ({len(entry.get('articles', []))}건)"):
                for i, item in enumerate(entry.get('articles', [])):
                    st.markdown(f"**{i+1}. [{item['Title']}]({item['Link']})** <span style='color:#888; font-size:0.8em'> | {item['Source']}</span>", unsafe_allow_html=True)

# ----------------------------------
# [Mode 2] General Category (수동)
# ----------------------------------
else:
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        new_kw = c1.text_input("키워드", label_visibility="collapsed")
        if c2.button("추가", use_container_width=True):
            if new_kw:
                st.session_state.keywords[selected_category].append(new_kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
        if c3.button("실행", type="primary", use_container_width=True):
            kws = st.session_state.keywords[selected_category]
            if kws:
                news = fetch_news(kws, limit=20)
                st.session_state.news_data[selected_category] = news
                st.rerun()

        curr_kws = st.session_state.keywords[selected_category]
        if curr_kws:
            st.write("")
            cols = st.columns(8)
            for i, kw in enumerate(curr_kws):
                if cols[i%8].button(f"{kw} ×", key=f"gdel_{kw}"):
                    st.session_state.keywords[selected_category].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()

    data = st.session_state.news_data.get(selected_category, [])
    if data:
        st.write(f"총 {len(data)}건 수집됨")
        for item in data:
            st.markdown(f"""
            <div class="news-card">
                <div class="news-meta">{item['Source']} | {item['Date']}</div>
                <a href="{item['Link']}" target="_blank" class="news-title">{item['Title']}</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("상단의 '실행' 버튼을 눌러 뉴스를 수집하세요.")
