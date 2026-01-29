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
import concurrent.futures

# [필수] 라이브러리
from deep_translator import GoogleTranslator
import yfinance as yf

# Google Gemini
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

        /* 뉴스 스타일 */
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-title:hover { color: #2563EB !important; text-decoration: underline; }
        .news-snippet { font-size: 13.5px !important; color: #475569 !important; line-height: 1.5; margin-bottom: 10px; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }

        /* 컨트롤 패널 */
        .control-box {
            background-color: #FFFFFF;
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            margin-bottom: 20px;
        }
        
        /* 버튼 스타일 */
        button[kind="secondary"] { height: 28px !important; font-size: 12px !important; padding: 0 10px !important; border-radius: 14px !important; }

        /* 주식 정보 */
        div[data-testid="stMetricValue"] { font-size: 13px !important; }
        div[data-testid="stMetricDelta"] { font-size: 11px !important; }
        div[data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 600; color: #64748B; }
        .stock-header { font-size: 12px; font-weight: 700; color: #475569; margin-top: 15px; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }

        /* 리포트 스타일 */
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
        .report-sub { font-size: 0.9em; color: #64748B; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "Daily", "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package"
]

# Daily 기본 키워드 지정
DAILY_DEFAULT_KEYWORDS = [
    "반도체 소재", "소재 공급망", "희토류 제한", "EUV", 
    "중국 반도체", "일본 반도체", "중국 광물", "반도체 규제"
]

# ==========================================
# 1. 주식 데이터 관리
# ==========================================
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
# 2. 유틸리티 및 크롤링 로직
# ==========================================
KEYWORD_FILE = 'keywords.json'

def load_keywords():
    data = {cat: [] for cat in CATEGORIES}
    # 파일이 있으면 로드
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in data: data[k] = v
        except: pass
    
    # [중요] Daily 항목이 비어있으면 기본값 강제 주입
    if not data["Daily"]:
        data["Daily"] = DAILY_DEFAULT_KEYWORDS
        
    return data

def save_keywords(data):
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def safe_translate(text):
    if not text: return ""
    try:
        return GoogleTranslator(source='auto', target='ko').translate(text[:999])
    except: return text

def parallel_translate_articles(articles):
    tasks = [a for a in articles if 'KR' not in a.get('Country', 'KR')]
    if not tasks: return articles
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        title_futures = {executor.submit(safe_translate, a['Title']): a for a in tasks}
        snip_futures = {executor.submit(safe_translate, a['Snippet']): a for a in tasks}
        for future in concurrent.futures.as_completed(title_futures):
            try: res = future.result(); title_futures[future]['Title'] = res if res else title_futures[future]['Title']
            except: pass
        for future in concurrent.futures.as_completed(snip_futures):
            try: res = future.result(); snip_futures[future]['Snippet'] = f"🌐 {res}" if res else snip_futures[future]['Snippet']
            except: pass
    return articles

def make_smart_query(keyword, country_code):
    base_kw = keyword
    negatives = "-TikTok -틱톡 -douyin -dance -shorts -reels -viral -music -game -soccer"
    contexts = {
        'KR': "(반도체 OR 소자 OR 공정 OR 소재 OR 파운드리 OR 팹 OR 양산)",
        'CN': "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)",
        'HK': "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)",
        'TW': "(半導體 OR 晶片 OR 晶圓 OR 光阻 OR 蝕刻 OR 封裝)",
        'JP': "(半導体 OR シリコン OR ウェーハ OR レジスト)",
        'US': "(semiconductor OR chip OR fab OR foundry OR wafer OR lithography)"
    }
    context = contexts.get(country_code, contexts['US'])
    return f'{base_kw} AND {context} {negatives}'

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        content_text = ""
        for i, item in enumerate(articles[:40]):
            safe_snip = re.sub(r'[^\w\s]', '', item.get('Snippet', ''))[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {safe_snip}\n"
        prompt = f"""
        Role: Semiconductor Analyst.
        Task: Filter noise. Keep B2B Tech/Fab/Materials.
        Data: {content_text}
        Output: IDs ONLY (e.g., 1, 3).
        """
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

def crawl_google_rss(keyword, country_code, language):
    results = []
    smart_query = make_smart_query(keyword, country_code)
    url = f"https://news.google.com/rss/search?q={quote(smart_query)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            for item in soup.find_all('item')[:5]:
                src = item.source.text if item.source else "Google"
                snip = BeautifulSoup(item.description.text if item.description else "", "html.parser").get_text(strip=True)[:200]
                pub_date = item.pubDate.text if item.pubDate else str(datetime.now())
                try: dt_obj = pd.to_datetime(pub_date).to_pydatetime()
                except: dt_obj = datetime.now()
                results.append({
                    'Title': item.title.text, 'Source': src, 'Date': dt_obj,
                    'Link': item.link.text, 'Keyword': keyword, 'Snippet': snip,
                    'AI_Verified': False, 'Country': country_code
                })
    except: pass
    return results

# [NEW] Daily 자동 실행을 위한 캐싱 함수 (핵심)
# date와 keywords가 바뀌면 자동으로 재실행됨
@st.cache_data(ttl=3600*12, show_spinner=False)
def auto_generate_daily_report(target_date, keywords, api_key):
    # 1. 크롤링
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    all_news = []
    for kw in keywords:
        # 주요 4개국 대상 크롤링
        for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW'), ('CN', 'zh-CN')]:
            all_news.extend(crawl_google_rss(kw, cc, lang))
            
    df = pd.DataFrame(all_news)
    final_articles = []
    report_text = ""
    
    if not df.empty:
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        df = df.drop_duplicates(subset=['Title']).sort_values('Date', ascending=False)
        
        # 리포트용으로 충분한 양 확보 (최대 80개)
        final_articles = df.head(80).to_dict('records')
        
        # 번역 & 필터링
        if final_articles: final_articles = parallel_translate_articles(final_articles)
        if api_key and final_articles: final_articles = filter_with_gemini(final_articles, api_key)
        
        # 2. 리포트 생성
        if api_key and final_articles:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                context = ""
                for i, item in enumerate(final_articles[:40]): # 상위 40개 참조
                    context += f"- {item['Title']}: {item.get('Snippet', '')}\n"
                    
                prompt = f"""
                역할: 반도체 산업 수석 애널리스트
                작업: '{target_date.strftime('%Y-%m-%d')}' 기준 반도체 공급망 및 이슈 일일 브리핑 작성.
                
                [작성 지침]
                1. 톤앤매너: 전문적, 통찰력 있음, 핵심 위주
                2. 형식: 깔끔한 Markdown
                3. 필수 섹션:
                   - 🚨 Key Headlines (오늘의 핵심 뉴스 3가지)
                   - 🌍 Global Supply Chain (공급망/소재/규제 이슈 분석)
                   - 📈 Tech & Market (기술 및 시장 동향)
                   - 📝 Analyst Note (종합 의견 한 줄)
                
                [참고 뉴스]
                {context}
                """
                response = model.generate_content(prompt)
                report_text = response.text
            except Exception as e:
                report_text = f"⚠️ 리포트 생성 실패: {str(e)}"
    
    return final_articles, report_text

def perform_crawling(category, start_date, end_date, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    with st.spinner(f"🚀 '{category}' 뉴스 수집 중..."):
        all_news = []
        for kw in kws:
            for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW'), ('CN', 'zh-CN')]:
                all_news.extend(crawl_google_rss(kw, cc, lang))
        
        df = pd.DataFrame(all_news)
        if not df.empty:
            df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
            df = df.drop_duplicates(subset=['Title']).sort_values('Date', ascending=False)
            final_list = df.head(60).to_dict('records')
            if final_list: final_list = parallel_translate_articles(final_list)
            if api_key and final_list: final_list = filter_with_gemini(final_list, api_key)
            st.session_state.news_data[category] = final_list
        else:
             st.session_state.news_data[category] = []

if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None

# ==========================================
# 3. Sidebar UI
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
            st.caption("⏳ Loading...")

# ==========================================
# 4. Main UI & Logic (자동 실행 분기)
# ==========================================
c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

# ----------------------------------------------------------------
# [Logic A] Daily 모드: 6시 기준 자동 실행 & 리포트 표시
# ----------------------------------------------------------------
if selected_category == "Daily":
    # 1. 6시 기준 날짜 계산
    now = datetime.now()
    if now.hour < 6:
        target_date = (now - timedelta(days=1)).date() # 6시 전이면 어제 날짜
    else:
        target_date = now.date() # 6시 이후면 오늘 날짜
        
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Target Date<br><b>{target_date} (06:00 AM)</b></div>", unsafe_allow_html=True)

    # 2. 키워드 관리 (Daily 전용)
    with st.container(border=True):
        st.markdown("##### ⚙️ Daily Report Settings")
        c_k1, c_k2 = st.columns([3, 1])
        with c_k1:
            new_kw = st.text_input("키워드 추가 (리포트에 자동 반영됩니다)", placeholder="예: HBM, 전력반도체", label_visibility="collapsed")
        with c_k2:
            if st.button("추가", use_container_width=True):
                if new_kw and new_kw not in st.session_state.keywords["Daily"]:
                    st.session_state.keywords["Daily"].append(new_kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun() # 키워드 변경 시 재실행을 위해 리로드

        # 키워드 태그
        daily_kws = st.session_state.keywords["Daily"]
        if daily_kws:
            st.write("")
            cols = st.columns(8)
            for i, kw in enumerate(daily_kws):
                if cols[i%8].button(f"{kw} ×", key=f"d_{kw}", type="secondary"):
                    st.session_state.keywords["Daily"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()

    # 3. [핵심] 자동 리포트 생성 및 캐싱 호출
    if api_key:
        with st.spinner(f"☕ {target_date}자 일일 브리핑을 준비 중입니다... (최초 1회 생성 시 시간 소요)"):
            # 키워드 리스트를 튜플로 변환하여 캐시 키로 사용 (리스트 변경 시 자동 갱신됨)
            articles, report_text = auto_generate_daily_report(target_date, tuple(daily_kws), api_key)
            
        if report_text:
            # 리포트 출력
            st.markdown(f"""
                <div class="report-box">
                    <div class="report-header">📑 {target_date} Daily Briefing</div>
                    <div class="report-sub">Generated by AI based on {len(articles)} articles</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(report_text)
            
            st.markdown("---")
            st.subheader("🔗 Reference Headlines")
            for i, item in enumerate(articles):
                with st.container():
                     st.markdown(f"{i+1}. [{item['Title']}]({item['Link']}) <span style='color:#999; font-size:0.8em'> | {item['Source']}</span>", unsafe_allow_html=True)
        else:
            st.warning("수집된 뉴스가 없거나 리포트를 생성할 수 없습니다.")
    else:
        st.error("🔐 API Key가 필요합니다. 사이드바에서 키를 입력해주세요.")

# ----------------------------------------------------------------
# [Logic B] 일반 카테고리 모드: 수동 실행
# ----------------------------------------------------------------
else:
    with c_info: 
        if st.session_state.last_update:
            st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Last Update<br><b>{st.session_state.last_update}</b></div>", unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 2.5, 1])
        with c1:
            period = st.selectbox("기간", ["1 Month", "3 Months", "Custom"], label_visibility="collapsed")
            today = datetime.now().date()
            if period == "1 Month": s, e = today - timedelta(days=30), today
            elif period == "3 Months": s, e = today - timedelta(days=90), today
            else:
                dr = st.date_input("날짜", (today-timedelta(7), today), label_visibility="collapsed")
                if len(dr)==2: s, e = dr
                else: s, e = dr[0], dr[0]
        with c2: new_kw = st.text_input("키워드", placeholder="예: HBM", label_visibility="collapsed")
        with c3:
            b1, b2 = st.columns(2)
            with b1:
                if st.button("추가", use_container_width=True):
                    if new_kw and new_kw not in st.session_state.keywords[selected_category]:
                        st.session_state.keywords[selected_category].append(new_kw)
                        save_keywords(st.session_state.keywords)
                        st.rerun()
            with b2:
                if st.button("실행", type="primary", use_container_width=True):
                    perform_crawling(selected_category, s, e, api_key)
                    st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    # 결과 디스플레이 (일반 모드)
    data = st.session_state.news_data.get(selected_category, [])
    if data:
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Collected", len(data))
        m2.metric("AI Verified", sum(1 for d in data if d.get('AI_Verified')))
        st.markdown("<br>", unsafe_allow_html=True)
        
        for i in range(0, len(data), 2):
            row_items = data[i : i+2]
            cols = st.columns(2)
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"""
                            <div class="news-meta" style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <span>📰 {item['Source']}</span>
                                <span>{item['Date'].strftime('%Y-%m-%d')}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f'<a href="{item["Link"]}" target="_blank" class="news-title">{item["Title"]}</a>', unsafe_allow_html=True)
                        if item.get('Snippet'):
                            st.markdown(f'<div class="news-snippet">{item["Snippet"]}</div>', unsafe_allow_html=True)
                        st.markdown("---")
                        ft1, ft2 = st.columns([3, 1])
                        with ft1:
                            st.markdown(f"<span style='background:#F1F5F9; color:#64748B; padding:3px 8px; border-radius:4px; font-size:11px;'>#{item['Keyword']}</span>", unsafe_allow_html=True)
                        with ft2:
                            if item.get('AI_Verified'):
                                st.markdown("<span style='color:#4F46E5; font-size:11px; font-weight:bold;'>✨ AI Pick</span>", unsafe_allow_html=True)
    else:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding:30px; color:#999;'>데이터가 없습니다.<br>상단의 '실행' 버튼을 눌러주세요.</div>", unsafe_allow_html=True)
