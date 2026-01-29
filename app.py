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
import random

# [필수] 라이브러리
from deep_translator import GoogleTranslator
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

# [수정] Daily를 맨 아래로 이동
CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package", "Daily"
]

# [수정] 속도와 안정성을 위해 핵심 키워드 5개로 압축 (리포트용)
DAILY_TARGET_KEYWORDS = [
    "Semiconductor Supply Chain", # 반도체 공급망
    "EUV Lithography",            # EUV
    "China Semiconductor Ban",    # 중국 규제
    "Samsung Electronics Yield",  # 삼성 수율/이슈
    "HBM Market Share"            # HBM
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
    # 날짜 중복 시 기존 것 삭제하고 최신 것으로 갱신 (맨 앞에 추가)
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data) 
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass
    return history

# ==========================================
# 3. 크롤링 및 AI 로직 (안정성 강화 버전)
# ==========================================
def make_smart_query(keyword, country_code):
    # Daily용은 영어 위주 검색이 정확도가 높음
    return f'{keyword} when:1d'

def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-pro')

def filter_with_gemini(articles, api_key):
    # 일반 모드용 필터 (Daily는 필터링 없이 전체 요약)
    if not articles or not api_key: return articles
    try:
        model = get_gemini_model(api_key)
        content_text = ""
        for i, item in enumerate(articles[:20]): 
            safe_snip = re.sub(r'[^\w\s]', '', item.get('Snippet', ''))[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {safe_snip}\n"
        prompt = f"""Role: Analyst. Task: Filter noise. Output: IDs ONLY (e.g., 1, 3). Data:\n{content_text}"""
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

# [수정] 초고속/안정성 크롤러 (타임아웃 5초 강제)
def crawl_fast_safe(keyword, country_code, language):
    url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Timeout 5초로 제한하여 무한 로딩 방지
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:2] # 키워드당 2개만 (핵심만 수집)
            
            parsed = []
            for item in items:
                src = item.source.text if item.source else "Google"
                snip = BeautifulSoup(item.description.text if item.description else "", "html.parser").get_text(strip=True)[:200]
                pub_date = item.pubDate.text if item.pubDate else str(datetime.now())
                try: dt_obj = pd.to_datetime(pub_date).to_pydatetime()
                except: dt_obj = datetime.now()
                
                parsed.append({
                    'Title': item.title.text,
                    'Source': f"{src}",
                    'Date': dt_obj,
                    'Link': item.link.text,
                    'Keyword': keyword,
                    'Snippet': snip,
                    'Country': country_code
                })
            return parsed
    except:
        pass
    return []

# [핵심] 리포트 생성 프로세스 (Daily)
def generate_daily_report_process(target_date, api_key):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_news = []
    
    # 1. 수집 단계 (US와 KR만 집중 공략하여 속도/성공률 향상)
    # 5개 키워드 * 2개국 = 10번 요청 (매우 빠름)
    targets = [('US', 'en'), ('KR', 'ko')] 
    total_ops = len(DAILY_TARGET_KEYWORDS) * len(targets)
    current_op = 0
    
    for kw in DAILY_TARGET_KEYWORDS:
        for cc, lang in targets:
            current_op += 1
            progress_bar.progress(current_op / (total_ops + 1)) # +1은 생성 단계
            status_text.text(f"📡 데이터 수집 중... {kw} ({cc})")
            
            # 수집
            items = crawl_fast_safe(kw, cc, lang)
            all_news.extend(items)
            time.sleep(0.5) # 구글 차단 방지 딜레이
            
    if not all_news:
        status_text.error("뉴스 수집 실패. 잠시 후 다시 시도해주세요.")
        return [], None

    # 2. 리포트 생성 단계
    status_text.text("📝 AI가 리포트를 작성하고 있습니다...")
    progress_bar.progress(0.9)
    
    df = pd.DataFrame(all_news)
    df = df.drop_duplicates(subset=['Title'])
    # 최신 20개만 AI에게 전달
    final_articles = df.head(20).to_dict('records')
    
    try:
        model = get_gemini_model(api_key)
        
        context = ""
        for i, item in enumerate(final_articles):
            context += f"- [{item['Country']}] {item['Title']}: {item.get('Snippet', '')}\n"
            
        prompt = f"""
        당신은 반도체 산업 전문 애널리스트입니다.
        '{target_date.strftime('%Y-%m-%d')}' 기준 [일일 반도체 브리핑]을 한국어로 작성하세요.
        
        [뉴스 데이터]
        {context}
        
        [작성 양식]
        ## 1. 🚨 핵심 이슈 (Top Headlines)
        (가장 중요한 뉴스 3가지를 요약)
        
        ## 2. 🌍 공급망 및 기업 동향
        (삼성, TSMC, 엔비디아 등 주요 기업 및 공급망 이슈)
        
        ## 3. 💡 시장 인사이트
        (오늘 뉴스가 시장에 주는 시사점 한 줄 요약)
        """
        
        response = model.generate_content(prompt)
        report_text = response.text
        
        # 저장
        save_data = {
            'date': target_date.strftime('%Y-%m-%d'),
            'report': report_text,
            'articles': final_articles
        }
        save_daily_history(save_data)
        
        progress_bar.empty()
        status_text.empty()
        return final_articles, report_text
        
    except Exception as e:
        status_text.error(f"리포트 작성 중 오류 발생: {e}")
        return final_articles, None

def perform_crawling_general(category, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    
    prog = st.progress(0)
    all_res = []
    
    for i, kw in enumerate(kws):
        prog.progress((i+1)/len(kws))
        # 일반 모드는 US, KR만 빠르게
        all_res.extend(crawl_fast_safe(kw, 'KR', 'ko'))
        all_res.extend(crawl_fast_safe(kw, 'US', 'en'))
        time.sleep(0.2)
        
    prog.empty()
    
    if all_res:
        df = pd.DataFrame(all_res)
        df = df.sort_values('Date', ascending=False).drop_duplicates('Title')
        final_list = df.head(40).to_dict('records')
        
        # 일반 모드만 번역 (선택사항)
        # 속도를 위해 번역 생략하거나 필요시 추가
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
    selected_category = st.radio("카테고리", CATEGORIES, index=len(CATEGORIES)-1, label_visibility="collapsed") # Daily 기본 선택 아님 (index조정 가능)
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
# [Logic A] Daily 모드 (1일 1회 생성, 자동 실행 X)
# ----------------------------------------------------------------
if selected_category == "Daily":
    # 1. 타겟 날짜 (6시 기준)
    now = datetime.now()
    target_date = (now - timedelta(days=1)).date() if now.hour < 6 else now.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Target: {target_date}</div>", unsafe_allow_html=True)

    # 2. 리포트 확인
    history = load_daily_history()
    # 날짜가 일치하는 리포트 찾기
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    # 3. UI 표시
    if today_report:
        # 이미 생성된 경우 -> 바로 표시
        st.success(f"✅ {target_date} 리포트가 준비되었습니다.")
        
        st.markdown(f"<div class='history-header'>📅 {today_report['date']} Daily Briefing</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='report-box'>{today_report['report']}</div>", unsafe_allow_html=True)
        
        with st.expander(f"🔗 Reference Sources ({len(today_report.get('articles', []))})"):
            for i, item in enumerate(today_report.get('articles', [])):
                st.markdown(f"{i+1}. [{item['Title']}]({item['Link']}) <span style='color:#999; font-size:0.8em'> | {item['Source']}</span>", unsafe_allow_html=True)
                
        # 지난 리포트 보기
        if len(history) > 1:
            st.markdown("---")
            st.subheader("🗄️ Past Reports")
            for entry in history[1:]:
                with st.expander(f"📅 {entry['date']} Report"):
                    st.markdown(entry['report'])

    else:
        # 생성된 게 없는 경우 -> 생성 버튼 표시
        st.info(f"📢 {target_date} 리포트가 아직 없습니다.")
        
        if api_key:
            if st.button("🚀 금일 리포트 생성 (약 30초 소요)", type="primary"):
                _, _ = generate_daily_report_process(target_date, api_key)
                st.rerun()
        else:
            st.error("API Key가 필요합니다.")
            
        # 지난 리포트가 있다면 보여줌
        if history:
            st.markdown("---")
            st.subheader("🗄️ Past Reports")
            for entry in history:
                with st.expander(f"📅 {entry['date']} Report"):
                    st.markdown(entry['report'])

# ----------------------------------------------------------------
# [Logic B] 일반 카테고리 (수동 실행)
# ----------------------------------------------------------------
else:
    with c_info: 
        if st.session_state.last_update:
            st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Updated: {st.session_state.last_update}</div>", unsafe_allow_html=True)
            
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 2.5, 1])
        with c1: st.write("") # Spacer
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
