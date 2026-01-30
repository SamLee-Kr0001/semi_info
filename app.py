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
# 0. 페이지 설정
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        .report-box { background-color: #FFFFFF; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; }
        .status-log { font-family: monospace; font-size: 0.85em; color: #334155; background: #F1F5F9; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #3B82F6; }
        .error-raw { font-family: monospace; font-size: 0.85em; color: #DC2626; background: #FEF2F2; padding: 10px; border: 1px solid #FECACA; border-radius: 6px; margin-top: 10px; white-space: pre-wrap; }
        
        /* 주식 폰트 고정 */
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 600 !important; }
        section[data-testid="stSidebar"] div[data-testid="stMetricDelta"] { font-size: 12px !important; }
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] { font-size: 12px !important; color: #64748B !important; }
    </style>
""", unsafe_allow_html=True)

# 사용자 제공 API Key (Fallback)
FALLBACK_API_KEY = "AIzaSyCBSqIQBIYQbWtfQAxZ7D5mwCKFx-7VDJo"

CATEGORIES = [
    "Daily Report", "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package"
]

DAILY_DEFAULT_KEYWORDS = [
    "반도체 소재", "소재 공급망", "희토류 제한", "EUV", 
    "중국 반도체", "일본 반도체", "중국 광물", "반도체 규제", "삼성전자 파운드리", "SK하이닉스 HBM"
]

STOCK_CATEGORIES = {
    "🏭 Chipmakers": {"Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU"},
    "🧠 Fabless": {"Nvidia": "NVDA", "Broadcom": "AVGO"},
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX"},
    "🧪 Materials": {"Soulbrain": "357780.KS", "Dongjin": "005290.KS", "Merck": "MRK.DE"}
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
                    currency = "₩" if ".KS" in symbol else "$"
                    result_map[symbol] = {"Price": f"{currency}{current:,.0f}" if currency == "₩" else f"{currency}{current:,.2f}", "Delta": f"{change:,.2f} ({pct_change:+.2f}%)"}
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
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s\.,%]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==========================================
# 2. AI 호출 (REST API - 상세 디버깅 모드)
# ==========================================
def generate_content_rest_api_debug(api_key, prompt):
    """
    여러 모델을 순회하며 시도하고, 실패 시 '정확한 에러 메시지'를 반환합니다.
    """
    models = ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-pro-latest"]
    last_error = ""
    
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
                if 'candidates' in result and result['candidates']:
                    return True, result['candidates'][0]['content']['parts'][0]['text']
                else:
                    last_error = f"Model {model} returned 200 but no text. Blocked? {result}"
            else:
                # 400, 403, 404, 500 등 에러 코드 수집
                last_error += f"\n[Model: {model}] Status: {response.status_code}, Body: {response.text[:200]}"
                
        except Exception as e:
            last_error += f"\n[Model: {model}] Exception: {str(e)}"
            continue
            
    return False, last_error

# ==========================================
# 3. 크롤링 및 프로세스
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
    log_area = status_box.empty()
    logs = []
    
    # 1. 수집
    for idx, kw in enumerate(keywords):
        items = fetch_rss_feed(kw, days_back=2)
        filtered = parse_and_filter_news(items, kw, start_dt, end_dt)
        
        if len(filtered) == 0:
            fallback_items = parse_and_filter_news(items, kw, end_dt - timedelta(hours=24), end_dt + timedelta(hours=24))
            if fallback_items:
                logs.append(f"⚠️ {kw}: 0건 -> 범위확장: {len(fallback_items)}건")
                all_news.extend(fallback_items)
            else:
                logs.append(f"❌ {kw}: 기사 없음")
        else:
            logs.append(f"✅ {kw}: {len(filtered)}건 수집")
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
    # [중요] AI 입력 데이터 15개로 제한 (오류 최소화)
    final_articles = df.head(15).to_dict('records')
    
    status_box.write(f"🧠 총 {len(final_articles)}건의 기사 분석 중... (API 호출 시도)")
    
    # 3. 리포트 작성
    context = ""
    for i, item in enumerate(final_articles):
        d_str = item['Date'].strftime('%H:%M')
        context += f"News {i+1}: {item['Title']}\nSummary: {item['Snippet']}\n\n"
        
    prompt = f"""
    당신은 반도체 애널리스트입니다. 아래 뉴스를 바탕으로 [일일 브리핑]을 한국어로 작성하세요.
    
    ## 1. 핵심 요약 (3줄)
    ## 2. 주요 이슈 분석
    ## 3. 시장 동향

    [데이터]
    {context}
    """
    
    success, result_text = generate_content_rest_api_debug(api_key, prompt)
    
    if success:
        status_box.update(label="🎉 리포트 생성 완료!", state="complete", expanded=False)
        save_data = {
            'date': target_date.strftime('%Y-%m-%d'),
            'report': result_text,
            'articles': final_articles
        }
        save_daily_history(save_data)
        return save_data
    else:
        # 실패 시 에러 로그 출력
        status_box.update(label="⚠️ AI 리포트 생성 실패 (상세 로그 확인)", state="error")
        st.markdown(f"**[구글 서버 에러 메시지]**\n<div class='error-raw'>{result_text}</div>", unsafe_allow_html=True)
        
        # 실패해도 기사 목록은 저장
        save_data = {
            'date': target_date.strftime('%Y-%m-%d'),
            'report': f"⚠️ **AI 분석 실패**\n\n아래 에러 메시지를 확인하세요.\n\n```\n{result_text}\n```",
            'articles': final_articles
        }
        save_daily_history(save_data)
        return save_data

# ==========================================
# 4. 앱 초기화 및 UI
# ==========================================
if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None
if 'daily_history' not in st.session_state: st.session_state.daily_history = load_daily_history()

with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    selected_category = st.radio("카테고리", CATEGORIES, index=0, label_visibility="collapsed")
    st.divider()
    
    # 키 관리
    with st.expander("🔐 API Key"):
        user_key = st.text_input("Key", type="password")
        if user_key: api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
        else: api_key = FALLBACK_API_KEY
    
    if st.button("🤖 AI 연결 테스트", use_container_width=True):
        ok, msg = generate_content_rest_api_debug(api_key, "Hi")
        if ok: st.success("연결 성공!")
        else: st.error(f"연결 실패\n{msg}")

    st.markdown("---")
    with st.expander("📉 Global Stock", expanded=True):
        stock_map = get_stock_prices_grouped()
        if stock_map:
            for cat_name, items in STOCK_CATEGORIES.items():
                st.markdown(f"<div class='stock-header'>{cat_name}</div>", unsafe_allow_html=True)
                for name, symbol in items.items():
                    data = stock_map.get(symbol)
                    if data:
                        c1, c2 = st.columns([1, 1.2])
                        c1.caption(f"**{name}**")
                        c2.metric("", data['Price'], data['Delta'], label_visibility="collapsed")
                        st.markdown("<hr style='margin: 2px 0; border-top: 1px dashed #f1f5f9;'>", unsafe_allow_html=True)

# 메인 UI
c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

if selected_category == "Daily Report":
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_date = (now_kst - timedelta(days=1)).date() if now_kst.hour < 6 else now_kst.date()
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Date: {target_date}</div>", unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        new_kw = c1.text_input("키워드 추가", label_visibility="collapsed")
        if c2.button("추가", use_container_width=True):
            st.session_state.keywords["Daily Report"].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
        
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("Keywords: " + ", ".join([f"`{k}`" for k in daily_kws]))

    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date.strftime('%Y-%m-%d')), None)
    
    if today_report:
        st.success(f"✅ {target_date} 리포트가 생성되어 있습니다.")
        if st.button("🔄 리포트 다시 만들기"):
             res = generate_daily_report_process(target_date, daily_kws, api_key)
             if res: st.rerun()
    else:
        st.info("📢 오늘의 리포트가 아직 없습니다.")
        if st.button("🚀 리포트 생성 시작", type="primary"):
            res = generate_daily_report_process(target_date, daily_kws, api_key)
            if res: st.rerun()

    if history:
        for entry in history:
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            with st.expander(f"📚 Reference ({len(entry.get('articles', []))})"):
                for i, item in enumerate(entry.get('articles', [])):
                    st.markdown(f"{i+1}. [{item['Title']}]({item['Link']})", unsafe_allow_html=True)

else:
    # 일반 카테고리 (생략 - 기존 유지)
    st.info("Daily Report 메뉴를 이용해주세요.")
