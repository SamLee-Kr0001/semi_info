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
STOCK_CATEGORIES = {
    "🏭 Chipmakers": {"Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU", "TSMC": "TSM"},
    "🧠 Fabless": {"Nvidia": "NVDA", "Broadcom": "AVGO", "AMD": "AMD"},
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX"},
    "🧪 Materials": {"Soulbrain": "357780.KS", "Dongjin": "005290.KS", "Merck": "MRK.DE"}
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
                    cur_sym = "₩" if ".KS" in symbol else ("€" if ".DE" in symbol else "$")
                    fmt_price = f"{cur_sym}{current:,.0f}" if cur_sym == "₩" else f"{cur_sym}{current:,.2f}"
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
    # [수정] 고정 키워드 삭제, 비어있으면 기본값 하나만 예시로
    if not data.get("Daily Report"): 
        data["Daily Report"] = ["반도체"] 
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
    # 날짜 중복 시 덮어쓰기 (최신이 위로)
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
    """성공한 로직: 모델 리스트를 순회하며 429/404 회피"""
    models = get_available_models(api_key)
    
    # 만약 조회 실패시 기본 모델셋 시도
    if not models:
        models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    prompt = f"""
    당신은 반도체 산업 수석 애널리스트입니다.
    아래 뉴스들을 종합하여 [일일 반도체 산업 브리핑]을 작성하세요.
    
    [뉴스 데이터]
    {chr(10).join(news_data)}
    
    [작성 양식 (Markdown)]
    ## 📊 Executive Summary
    (시장 핵심 흐름 3줄 요약)
    
    ## 🚨 Key Headlines
    (주요 이슈 분석)
    
    ## 📉 Market & Insight
    (기업 동향 및 향후 전망)
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
        # 이미지 전용 모델 제외
        if "vision" in model: continue
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            # 타임아웃 30초
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                res_json = response.json()
                if 'candidates' in res_json and res_json['candidates']:
                    return True, res_json['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                time.sleep(1) # 용량 초과시 잠깐 대기 후 다음 모델
                continue
                
        except: continue
            
    return False, "모든 모델이 응답하지 않습니다. (Quota Exceeded 또는 연결 오류)"

# ==========================================
# 3. 뉴스 크롤링 (requests + bs4)
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
                    'Date': item.pubDate.text, # 단순 표시용
                    'Source': item.source.text if item.source else "Google News"
                })
        except: pass
        time.sleep(0.1)
        
    # 중복 제거 (제목 기준)
    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['Title'])
        return df.head(limit).to_dict('records')
    return []

# ==========================================
# 4. 앱 UI 및 메인 로직
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
        # 키 우선순위: 입력값 > Secrets > Fallback
        if user_key: api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
        else: api_key = FALLBACK_API_KEY
    
    st.markdown("---")
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
# [Mode 1] Daily Report
# ----------------------------------
if selected_category == "Daily Report":
    # 날짜 계산 (KST)
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_date = (now_kst - timedelta(days=1)).date() if now_kst.hour < 6 else now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; color:#888;'>Report Date<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    # 1. 키워드 설정 (동적 추가/삭제)
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        new_kw = c1.text_input("수집 키워드 추가", placeholder="예: HBM, 패키징", label_visibility="collapsed")
        if c2.button("추가", use_container_width=True):
            if new_kw and new_kw not in st.session_state.keywords["Daily Report"]:
                st.session_state.keywords["Daily Report"].append(new_kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
        
        # 키워드 태그 표시 및 삭제
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            # 가로로 배치
            cols = st.columns(len(daily_kws) if len(daily_kws) < 8 else 8)
            for i, kw in enumerate(daily_kws):
                if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
    
    # 2. 리포트 생성 및 표시
    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if today_report:
        st.success(f"✅ {target_date} 리포트가 발행되었습니다.")
        # 재생성 버튼
        if st.button("🔄 리포트 다시 생성하기 (덮어쓰기)"):
            status_box = st.status("🚀 리포트 재생성 시작...", expanded=True)
            
            # 수집
            status_box.write("📡 뉴스 데이터 수집 중...")
            news_items = fetch_news(daily_kws)
            if not news_items:
                status_box.update(label="❌ 뉴스 수집 실패 (0건)", state="error")
            else:
                # AI 분석
                status_box.write(f"🧠 AI 분석 중... (기사 {len(news_items)}건)")
                news_texts = [f"- {item['Title']}" for item in news_items]
                success, result = generate_report_with_auto_model(api_key, news_texts)
                
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 재생성 완료!", state="complete")
                    st.rerun()
                else:
                    status_box.update(label="⚠️ AI 분석 실패", state="error")
                    st.error(result)
                    
    else:
        st.info("📢 아직 리포트가 없습니다.")
        if st.button("🚀 리포트 생성 시작", type="primary"):
            status_box = st.status("🚀 리포트 생성 프로세스...", expanded=True)
            
            # 수집
            status_box.write("📡 키워드 기반 뉴스 수집 중...")
            news_items = fetch_news(daily_kws)
            
            if not news_items:
                status_box.update(label="❌ 수집된 뉴스가 없습니다. 키워드를 확인하세요.", state="error")
            else:
                # AI 분석
                status_box.write(f"🧠 AI 모델 자동 탐색 및 분석 중... ({len(news_items)}건)")
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

    # 3. 리포트 본문 출력
    if history:
        for entry in history:
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            # [요청사항] 하단에 링크 생성
            with st.expander(f"🔗 수집된 기사 원문 보기 ({len(entry.get('articles', []))}건)"):
                for i, item in enumerate(entry.get('articles', [])):
                    st.markdown(f"**{i+1}. [{item['Title']}]({item['Link']})** <span style='color:#aaa'>| {item['Source']}</span>", unsafe_allow_html=True)

# ----------------------------------
# [Mode 2] General Category
# ----------------------------------
else:
    # 키워드 관리
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
                news = fetch_
