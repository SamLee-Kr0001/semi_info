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
# 0. 페이지 설정 및 초기화 (오류 방지 핵심)
# ==========================================
st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# [핵심 수정] AttributeError 방지를 위한 세션 상태 최상단 초기화
CATEGORIES = ["Daily Report", "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", "Process Gas", "Wafer", "Package"]

if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}

if 'keywords' not in st.session_state:
    # 키워드 로드 로직은 뒤에 함수로 정의되지만, 초기값은 여기서 잡습니다.
    st.session_state.keywords = {cat: [] for cat in CATEGORIES}

if 'daily_history' not in st.session_state:
    st.session_state.daily_history = []

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        
        /* 리포트 스타일 */
        .report-box { background-color: #FFFFFF; padding: 50px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; font-size: 16px; }
        .report-box h2 { color: #1E3A8A; border-bottom: 2px solid #3B82F6; padding-bottom: 10px; margin-top: 30px; margin-bottom: 20px; font-size: 24px; font-weight: 700; }
        
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
        
        /* 레퍼런스 링크 스타일 */
        .ref-link { font-size: 0.9em; color: #555; text-decoration: none; display: block; margin-bottom: 6px; padding: 5px; border-radius: 4px; transition: background 0.2s; }
        .ref-link:hover { background-color: #F1F5F9; color: #2563EB; }
        .ref-number { font-weight: bold; color: #3B82F6; margin-right: 8px; background: #DBEAFE; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    </style>
""", unsafe_allow_html=True)

# 기본값 설정

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
# 1. 데이터 관리 함수
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
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data)
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass

# ==========================================
# 2. 뉴스 수집 함수
# ==========================================
def fetch_news(keywords, days=1, limit=20, strict_time=False):
    all_items = []
    
    # 시간 필터링 기준 (KST)
    now_kst = datetime.utcnow() + timedelta(hours=9)
    end_target = datetime(now_kst.year, now_kst.month, now_kst.day, 6, 0, 0)
    if now_kst.hour < 6:
        end_target -= timedelta(days=1)
    start_target = end_target - timedelta(hours=18)
    
    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={quote(kw)}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            
            for item in items:
                is_valid = True
                if strict_time:
                    try:
                        pub_date_str = item.pubDate.text
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                        pub_date_kst = pub_date + timedelta(hours=9)
                        if not (start_target <= pub_date_kst <= end_target):
                            is_valid = False
                    except: is_valid = True
                
                if is_valid:
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
# 3. AI 리포트 생성 (프롬프트 수정됨)
# ==========================================
def get_available_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [m['name'].replace("models/", "") for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    except: pass
    return []

def inject_links_to_report(report_text, news_data):
    """[1] -> [[1]](URL) 변환"""
    def replace_match(match):
        try:
            idx_str = match.group(1)
            idx = int(idx_str) - 1
            if 0 <= idx < len(news_data):
                link = news_data[idx]['Link']
                return f"[[{idx_str}]]({link})"
        except: pass
        return match.group(0)
    return re.sub(r'\[(\d+)\]', replace_match, report_text)

def generate_report_with_citations(api_key, news_data):
    models = get_available_models(api_key)
    if not models:
        models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    # Context에 Source 정보 포함
    news_context = ""
    for i, item in enumerate(news_data):
        news_context += f"[{i+1}] {item['Title']} (Source: {item['Source']})\n"

    # [수정] 프롬프트: 서술형(Narrative) 지시 강화
    prompt = f"""
    당신은 글로벌 반도체 투자 및 전략 수석 애널리스트입니다. 
    제공된 뉴스 데이터를 바탕으로 전문가 수준의 **[일일 반도체 심층 분석 보고서]**를 작성하세요.

    **[작성 원칙 - 매우 중요]**
    1. **단순 요약 금지**: 뉴스 제목을 단순히 나열하거나 번역하지 마세요.
    2. **서술형 작성**: 이슈별로 현상/원인/전망을 개조식(Bullet points)으로 나누지 말고, **하나의 자연스러운 논리적 흐름을 가진 줄글(Narrative Paragraph)**로 서술하세요. 전문적인 문체를 사용하세요.
    3. **근거 명시**: 모든 주장이나 사실 언급 시 반드시 제공된 뉴스 번호 **[1], [2]**를 문장 끝에 인용하세요.

    [뉴스 데이터]
    {news_context}
    
    [보고서 구조 (Markdown)]
    ## 📊 Executive Summary (시장 총평)
    - 오늘 반도체 시장의 핵심 분위기와 가장 중요한 변화를 3~4문장으로 요약. (기존 유지)

    ## 🚨 Key Issues & Deep Dive (핵심 이슈 심층 분석)
    - 가장 중요한 이슈 2~3가지를 선정하여 소제목을 달고 분석하세요.
    - **중요**: 현상, 원인, 전망을 구분하여 나열하지 말고, **깊이 있는 서술형 문단**으로 작성하세요. 사건의 배경부터 파급 효과까지 매끄럽게 연결되도록 하세요.
    - 반드시 인용 번호[n]를 포함할 것.

    ## 🕸️ Supply Chain & Tech Trends (공급망 및 기술 동향)
    - 소부장, 파운드리, 메모리 등 섹터별 주요 단신을 종합하여 서술.

    ## 💡 Analyst's View (투자 아이디어)
    - 오늘의 뉴스가 주는 시사점과 향후 관전 포인트 한 줄 정리.
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
        if "vision" in model: continue
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                res_json = response.json()
                if 'candidates' in res_json and res_json['candidates']:
                    raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                    linked_text = inject_links_to_report(raw_text, news_data)
                    return True, linked_text
            elif response.status_code == 429:
                time.sleep(1) 
                continue
        except: continue
            
    return False, "AI 분석 실패 (모든 모델 응답 없음)"

# ==========================================
# 4. 메인 앱 UI
# ==========================================
# [수정] 키워드 초기화 로직도 최상단으로 이동했지만, 안전을 위해 여기서 한 번 더 체크
if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
# 이미 상단에서 news_data를 초기화했으므로 AttributorError는 해결됨

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

c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

# ----------------------------------
# [Mode 1] Daily Report
# ----------------------------------
if selected_category == "Daily Report":
    # [수정] 문구 추가
    st.info("ℹ️ 매일 오전 6시 기준 반도체 소재관련 정보 Report 입니다.")

    now_kst = datetime.utcnow() + timedelta(hours=9)
    if now_kst.hour < 6:
        target_date = (now_kst - timedelta(days=1)).date()
    else:
        target_date = now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; color:#888;'>Report Date<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        new_kw = c1.text_input("수집 키워드 추가", placeholder="예: HBM, 패키징", label_visibility="collapsed")
        if c2.button("추가", use_container_width=True):
            if new_kw and new_kw not in st.session_state.keywords["Daily Report"]:
                st.session_state.keywords["Daily Report"].append(new_kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
        
        # [수정] 키워드 심플 디스플레이 & 경고 문구
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            cols = st.columns(len(daily_kws) if len(daily_kws) < 8 else 8)
            for i, kw in enumerate(daily_kws):
                if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        
        st.caption("⚠️ 관심 키워드를 추가하면 해당 주제로 보고서에 반영됩니다. 단 키워드가 늘어나면 시스템 오류발생 가능성이 높습니다. 왼쪽 각 sector 별 Keyword 검색을 활용해주세요")
    
    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if not today_report:
        st.info(f"📢 {target_date} 리포트가 아직 생성되지 않았습니다.")
        if st.button("🚀 금일 리포트 생성 시작", type="primary"):
            status_box = st.status("🚀 리포트 생성 프로세스...", expanded=True)
            
            status_box.write(f"📡 뉴스 수집 중 (전일 12:00 ~ 금일 06:00)...")
            news_items = fetch_news(daily_kws, days=2, strict_time=True)
            
            if not news_items:
                status_box.update(label="⚠️ 조건에 맞는 뉴스가 없어 범위를 확장합니다 (최근 24시간).", state="running")
                time.sleep(1)
                news_items = fetch_news(daily_kws, days=1, strict_time=False)
            
            if not news_items:
                status_box.update(label="❌ 수집된 뉴스가 없습니다.", state="error")
            else:
                status_box.write(f"🧠 AI 심층 분석 중... (기사 {len(news_items)}건)")
                success, result = generate_report_with_citations(api_key, news_items)
                
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 리포트 생성 완료!", state="complete")
                    st.rerun()
                else:
                    status_box.update(label="⚠️ AI 분석 실패", state="error")
                    st.error(result)
    else:
        st.success(f"✅ {target_date} 리포트가 완료되었습니다.")
        if st.button("🔄 리포트 다시 만들기 (덮어쓰기)"):
            status_box = st.status("🚀 리포트 재생성 중...", expanded=True)
            news_items = fetch_news(daily_kws, days=1, strict_time=False)
            if news_items:
                success, result = generate_report_with_citations(api_key, news_items)
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 재생성 완료!", state="complete")
                    st.rerun()

    if history:
        for entry in history:
            st.divider()
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            with st.expander(f"📚 References (기사 원문) - {len(entry.get('articles', []))}건"):
                st.markdown("#### 기사 원문 링크")
                ref_cols = st.columns(2)
                for i, item in enumerate(entry.get('articles', [])):
                    col = ref_cols[i % 2]
                    with col:
                        st.markdown(f"""
                        <a href="{item['Link']}" target="_blank" class="ref-link">
                            <span class="ref-number">[{i+1}]</span> {item['Title']}
                        </a>
                        """, unsafe_allow_html=True)

# ----------------------------------
# [Mode 2] General Category
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

    # [수정] AttributeError가 발생했던 부분 (이제 안전함)
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
