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

CATEGORIES = [
    "Daily", "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package"
]

# [핵심] Daily 리포트용 고정 키워드
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
    # Daily 키워드가 비어있으면 기본값 복구
    if not data.get("Daily"): data["Daily"] = DAILY_DEFAULT_KEYWORDS
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
# 3. 고급 크롤링 로직 (번역 검색 + 안정성)
# ==========================================

# [NEW] 키워드를 현지 언어로 변환하는 함수
def translate_keyword_for_search(keyword, target_lang):
    if target_lang == 'ko': return keyword
    try:
        # deep_translator 사용 (짧은 단어라 빠름)
        return GoogleTranslator(source='auto', target=target_lang).translate(keyword)
    except:
        return keyword # 실패시 원문 사용

def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-pro')

# [NEW] 강력한 크롤러 (재시도 로직 + 랜덤 지연)
def crawl_robust(keyword, country_code, language):
    # 1. 키워드 현지화 (정확도 향상 핵심)
    # 구글 검색용 언어 코드로 변환 (zh-CN -> zh-CN, zh-TW -> zh-TW, en -> en, ja -> ja)
    trans_lang = language.split('-')[0] if '-' in language else language
    if country_code == 'CN' or country_code == 'TW': trans_lang = 'zh-CN' # 중국어 통합
    
    local_keyword = translate_keyword_for_search(keyword, trans_lang)
    
    # 2. 쿼리 생성
    # 검색어에 날짜 필터(when:1d) 추가하여 최신성 확보
    base_url = f"https://news.google.com/rss/search?q={quote(local_keyword)}+when:2d&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://news.google.com/'
    }
    
    # 3. 요청 (재시도 1회)
    for attempt in range(2):
        try:
            # 타임아웃 20초로 넉넉하게 설정
            response = requests.get(base_url, headers=headers, timeout=20, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')[:3] # 키워드/국가당 상위 3개만 (부하 관리)
                
                parsed = []
                for item in items:
                    src = item.source.text if item.source else "Google"
                    snip = BeautifulSoup(item.description.text if item.description else "", "html.parser").get_text(strip=True)[:300]
                    # 날짜 처리
                    try: 
                        pub_date = pd.to_datetime(item.pubDate.text).to_pydatetime()
                    except: 
                        pub_date = datetime.now()
                    
                    parsed.append({
                        'Title': item.title.text,
                        'Source': f"{src} ({country_code})",
                        'Date': pub_date,
                        'Link': item.link.text,
                        'Keyword': keyword, # 원본 키워드 저장
                        'Snippet': snip,
                        'Country': country_code,
                        'AI_Verified': True # Daily는 모두 신뢰
                    })
                return parsed
        except Exception as e:
            time.sleep(1) # 에러 시 1초 대기 후 재시도
            continue
            
    return []

# [핵심] 일일 리포트 프로세스 (순차 처리로 안정성 100%)
def process_daily_report_stable(target_date, keywords, api_key):
    # 진행 상황 표시용
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_news = []
    
    # 1. 타겟 국가 정의 (한국, 미국, 중국, 일본, 대만)
    # (국가코드, 언어코드)
    targets = [
        ('KR', 'ko'), 
        ('US', 'en'), 
        ('CN', 'zh-CN'), 
        ('JP', 'ja'),
        ('TW', 'zh-TW')
    ]
    
    total_steps = len(keywords) * len(targets)
    current_step = 0
    
    # 2. 순차 크롤링 시작
    for kw in keywords:
        for cc, lang in targets:
            current_step += 1
            progress = current_step / total_steps
            progress_bar.progress(progress)
            status_text.text(f"🌍 수집 중... [{int(progress*100)}%] {kw} ({cc})")
            
            # 크롤링 실행
            items = crawl_robust(kw, cc, lang)
            all_news.extend(items)
            
            # [중요] 차단 방지를 위한 랜덤 지연 (0.5 ~ 1.5초)
            time.sleep(random.uniform(0.5, 1.5))
            
    # 3. 데이터 정리
    if not all_news:
        status_text.error("수집된 뉴스가 없습니다. 키워드를 확인해주세요.")
        return [], ""
        
    df = pd.DataFrame(all_news)
    # 날짜 정렬 (최신순)
    df = df.sort_values('Date', ascending=False)
    # 중복 제거 (제목 기준)
    df = df.drop_duplicates(subset=['Title'])
    
    # AI에게 보낼 상위 35개 선정
    final_articles = df.head(35).to_dict('records')
    
    # 4. 리포트 생성
    status_text.text("🤖 AI가 글로벌 뉴스를 분석하고 리포트를 작성 중입니다...")
    
    try:
        model = get_gemini_model(api_key)
        
        # 문맥 생성 (국가 태그 포함)
        context = ""
        for i, item in enumerate(final_articles):
            context += f"[{item['Country']}] {item['Title']} : {item['Snippet'][:100]}\n"
            
        prompt = f"""
        당신은 글로벌 반도체 산업 수석 애널리스트입니다. 
        아래 제공된 {len(final_articles)}개의 다국어(한/미/중/일/대만) 뉴스 데이터를 분석하여,
        '{target_date.strftime('%Y-%m-%d')}' 기준 [일일 반도체 산업 인텔리전스 리포트]를 작성하세요.
        
        [뉴스 데이터]
        {context}
        
        [작성 원칙]
        1. **언어**: 한국어 (전문적이고 통찰력 있는 어조)
        2. **분량**: 충분히 상세하게 작성 (단순 나열 금지)
        3. **구조**:
           - **🚨 Top Headlines**: 가장 파급력이 큰 핵심 이슈 3가지 (심층 분석)
           - **⚔️ Supply Chain & Geopolitics**: 미중 갈등, 수출 규제, 소재 공급망 이슈
           - **📈 Tech & Market**: 기업(삼성, TSMC, 엔비디아 등) 동향 및 기술 이슈
           - **💡 Analyst Insight**: 오늘의 뉴스가 시장에 미치는 영향 요약
        """
        
        response = model.generate_content(prompt)
        report_text = response.text
        
        # 5. 저장
        save_data = {
            'date': target_date.strftime('%Y-%m-%d'),
            'report': report_text,
            'articles': final_articles
        }
        save_daily_history(save_data)
        
        status_text.success("리포트 생성 완료!")
        time.sleep(1)
        status_text.empty()
        progress_bar.empty()
        
        return final_articles, report_text
        
    except Exception as e:
        status_text.error(f"리포트 생성 중 오류: {str(e)}")
        return final_articles, ""

def perform_crawling_general(category, api_key):
    # 일반 카테고리용 단순 크롤링 (기존 로직 유지하되 안정성 강화)
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    
    prog = st.progress(0)
    all_res = []
    
    for i, kw in enumerate(kws):
        prog.progress((i+1)/len(kws))
        # 한국, 미국만 빠르게 수집
        all_res.extend(crawl_robust(kw, 'KR', 'ko'))
        all_res.extend(crawl_robust(kw, 'US', 'en'))
        time.sleep(0.5)
        
    prog.empty()
    
    if all_res:
        df = pd.DataFrame(all_res)
        df = df.sort_values('Date', ascending=False).drop_duplicates('Title')
        final_list = df.head(40).to_dict('records')
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
    selected_category = st.radio("카테고리", CATEGORIES, label_visibility="collapsed")
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
# [Logic A] Daily 모드
# ----------------------------------------------------------------
if selected_category == "Daily":
    # 1. 타겟 날짜 (6시 기준)
    now = datetime.now()
    target_date = (now - timedelta(days=1)).date() if now.hour < 6 else now.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Report Date<br><b>{target_date} (06:00 AM)</b></div>", unsafe_allow_html=True)

    # 2. 키워드 설정
    with st.container(border=True):
        st.markdown("##### ⚙️ Monitoring Keywords")
        c_k1, c_k2 = st.columns([3, 1])
        with c_k1: new_kw = st.text_input("키워드 추가", label_visibility="collapsed")
        with c_k2:
            if st.button("추가", use_container_width=True):
                if new_kw and new_kw not in st.session_state.keywords["Daily"]:
                    st.session_state.keywords["Daily"].append(new_kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        daily_kws = st.session_state.keywords["Daily"]
        if daily_kws:
            st.write("")
            cols = st.columns(8)
            for i, kw in enumerate(daily_kws):
                if cols[i%8].button(f"{kw} ×", key=f"d_{kw}", type="secondary"):
                    st.session_state.keywords["Daily"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()

    # 3. 리포트 로직
    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    # 리포트가 없으면 -> 자동 시작 (단, API Key 필수)
    if not today_report:
        if api_key:
            st.info(f"☀️ {target_date} 리포트 자동 생성 중... (약 1~2분 소요)")
            # 자동 실행
            _, _ = process_daily_report_stable(target_date, daily_kws, api_key)
            st.rerun()
        else:
            st.warning("⚠️ API Key가 입력되지 않아 리포트를 생성할 수 없습니다. 사이드바에 키를 입력해주세요.")

    # 4. 리포트 출력
    if not history:
        st.write("")
    else:
        for idx, entry in enumerate(history):
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Intelligence Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            with st.expander(f"🔗 Source Articles ({len(entry.get('articles', []))})"):
                for i, item in enumerate(entry.get('articles', [])):
                    st.markdown(f"{i+1}. **[{item['Title']}]({item['Link']})** <span style='color:#999; font-size:0.8em'> | {item['Source']}</span>", unsafe_allow_html=True)

# ----------------------------------------------------------------
# [Logic B] 일반 카테고리
# ----------------------------------------------------------------
else:
    with c_info: 
        if st.session_state.last_update:
            st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Last Update<br><b>{st.session_state.last_update}</b></div>", unsafe_allow_html=True)
            
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 2.5, 1])
        with c1: st.write("") # 공간 채움
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
