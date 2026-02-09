import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time as dt_time
import json
import os
import re
import time
import yfinance as yf
from github import Github
import concurrent.futures  # [추가] 주식 데이터 병렬 처리를 위한 모듈

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 0. 페이지 설정
# ==========================================
st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

CATEGORIES = ["Daily Report", "P&C 소재", "EDTW 소재", "PKG 소재"]
KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json'

if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'daily_history' not in st.session_state:
    st.session_state.daily_history = []

st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F8FAFC; }
        
        .report-box { background-color: #FFFFFF; padding: 50px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; font-size: 16px; }
        .news-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 10px; }
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }
        
        /* 주식 정보 스타일 */
        .stock-row { display: flex; justify-content: space-between; align-items: center; font-size: 14px; padding: 5px 0; border-bottom: 1px dashed #e2e8f0; }
        .stock-name { font-weight: 600; color: #334155; }
        .stock-price { font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; }
        .up-color { color: #DC2626 !important; }
        .down-color { color: #2563EB !important; }
        .flat-color { color: #64748B !important; }
        .stock-header { font-size: 13px; font-weight: 700; color: #475569; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }
        .ref-link { font-size: 0.9em; color: #555; text-decoration: none; display: block; margin-bottom: 6px; padding: 5px; border-radius: 4px; transition: background 0.2s; }
        
        section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
        div.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.2s ease-in-out; }
        .streamlit-expanderHeader { background-color: #FFFFFF; border-radius: 8px; }
        a { text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

# 주식 티커
STOCK_CATEGORIES = {
    "🏭 Chipmakers": {"SK Hynix": "000660.KS", "Samsung": "005930.KS", "Micron": "MU", "TSMC": "TSM", "Intel": "INTC", "AMD": "AMD", "SMIC": "0981.HK"},
    "🧠 AI ": {"NVIDIA": "NVDA", "Apple": "AAPL", "Alphabet (Google)": "GOOGL", "Microsoft": "MSFT", "Meta": "META", "Amazon": "AMZN", "Tesla": "TSLA", "IBM": "IBM", "Oracle": "ORCL", "Broadcom": "AVGO"},
    "🧪 Materials": {"Soulbrain": "357780.KQ", "Dongjin": "005290.KQ", "Hana Mat": "166090.KQ", "Wonik Mat": "104830.KQ", "TCK": "064760.KQ", "Foosung": "093370.KS", "PI Adv": "178920.KS", "ENF": "102710.KQ", "TEMC": "425040.KQ", "YC Chem": "112290.KQ", "Samsung SDI": "006400.KS", "Shin-Etsu": "4063.T", "Sumco": "3436.T", "Merck": "MRK.DE", "Entegris": "ENTG", "TOK": "4186.T", "Resonac": "4004.T", "Air Prod": "APD", "Linde": "LIN", "Qnity": "Q", "Nissan Chem": "4021.T", "Sumitomo": "4005.T"},
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T", "KLA": "KLAC", "Advantest": "6857.T", "Hitachi HT": "8036.T", "Hanmi": "042700.KS", "Wonik IPS": "240810.KQ", "Jusung": "036930.KQ", "EO Tech": "039030.KQ", "Techwing": "089030.KQ", "Eugene": "084370.KQ", "PSK": "319660.KQ", "Zeus": "079370.KQ", "Top Eng": "065130.KQ"}
}

# ==========================================
# 1. 데이터 관리 (GitHub Auto-Sync)
# ==========================================
def sync_to_github(filename, content_data):
    if "GITHUB_TOKEN" not in st.secrets or "REPO_NAME" not in st.secrets: return False
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(st.secrets["REPO_NAME"])
        content_str = json.dumps(content_data, ensure_ascii=False, indent=4)
        try:
            contents = repo.get_contents(filename)
            repo.update_file(contents.path, f"Update {filename}", content_str, contents.sha)
        except:
            repo.create_file(filename, f"Create {filename}", content_str)
        return True
    except: return False

def load_keywords():
    data = {cat: [] for cat in CATEGORIES}
    if "GITHUB_TOKEN" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(KEYWORD_FILE)
            loaded = json.loads(contents.decoded_content.decode("utf-8"))
            return loaded
        except: pass
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
    sync_to_github(KEYWORD_FILE, data)

def load_daily_history_from_source():
    if "GITHUB_TOKEN" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(HISTORY_FILE)
            return json.loads(contents.decoded_content.decode("utf-8"))
        except: pass
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'keywords' not in st.session_state:
    st.session_state.keywords = load_keywords()
if 'daily_history' not in st.session_state:
    st.session_state.daily_history = load_daily_history_from_source()

def save_daily_history(new_report_data):
    current_history = [h for h in st.session_state.daily_history if h['date'] != new_report_data['date']]
    current_history.insert(0, new_report_data)
    st.session_state.daily_history = current_history
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=4)
    except: pass
    sync_to_github(HISTORY_FILE, current_history)

# [수정] 주식 개별 수집 함수 (병렬 처리용)
def fetch_single_stock(name, symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 1. fast_info를 우선 시도 (가장 최신/정확)
        try:
            current = ticker.fast_info['last_price']
            prev = ticker.fast_info['previous_close']
        except:
            # 2. 실패 시 history 조회
            hist = ticker.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = ticker.info.get('previousClose', current) # info는 느릴 수 있음
            else:
                # 3. 데이터가 아예 없으면 5일치로 fallback
                hist_5d = ticker.history(period="5d")
                if len(hist_5d) >= 1:
                    current = hist_5d['Close'].iloc[-1]
                    prev = hist_5d['Close'].iloc[-2] if len(hist_5d) >= 2 else current
                else:
                    return name, None

        if current is None: return name, None

        change = current - prev
        pct = (change / prev) * 100
        
        # 통화 기호 설정
        if ".KS" in symbol or ".KQ" in symbol: cur_sym = "₩"
        elif ".T" in symbol: cur_sym = "¥"
        elif ".HK" in symbol: cur_sym = "HK$"
        elif ".DE" in symbol: cur_sym = "€"
        else: cur_sym = "$"
        
        fmt_price = f"{cur_sym}{current:,.0f}" if cur_sym in ["₩", "¥"] else f"{cur_sym}{current:,.2f}"
        
        if change > 0: color_class, arrow, sign = "up-color", "▲", "+"
        elif change < 0: color_class, arrow, sign = "down-color", "▼", ""
        else: color_class, arrow, sign = "flat-color", "-", ""
        
        html_str = f"""
        <div class="stock-row">
            <span class="stock-name">{name}</span>
            <span class="stock-price {color_class}">
                {fmt_price} <span style="font-size:0.9em; margin-left:3px;">{arrow} {sign}{pct:.2f}%</span>
            </span>
        </div>
        """
        return name, html_str
    except:
        return name, None

# [수정] 병렬 처리 적용된 주식 수집 함수 (속도 개선)
@st.cache_data(ttl=300)
def get_stock_prices_grouped():
    result_map = {}
    # 모든 티커를 리스트로 평탄화
    all_tickers = []
    for cat, items in STOCK_CATEGORIES.items():
        for name, symbol in items.items():
            all_tickers.append((name, symbol))
            
    # 병렬 실행 (최대 10개 스레드)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_stock = {executor.submit(fetch_single_stock, name, symbol): name for name, symbol in all_tickers}
        for future in concurrent.futures.as_completed(future_to_stock):
            try:
                name, html = future.result()
                if html:
                    result_map[name] = html
            except: pass
            
    return result_map

# ==========================================
# 2. 뉴스 수집 (기존 유지)
# ==========================================
def fetch_news(keywords, days=1, limit=40, strict_time=False, start_dt=None, end_dt=None):
    all_items = []
    if not (strict_time and start_dt and end_dt):
        now_kst = datetime.utcnow() + timedelta(hours=9)
        end_dt = datetime(now_kst.year, now_kst.month, now_kst.day, 6, 0, 0)
        if now_kst.hour < 6: end_dt -= timedelta(days=1)
        start_dt = end_dt - timedelta(hours=18)
    
    per_kw_limit = 3 if len(keywords) > 4 else 7

    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={quote(kw)}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            kw_collected = 0
            for item in items:
                is_valid = True
                if strict_time:
                    try:
                        pub_date_str = item.pubDate.text
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                        pub_date_kst = pub_date + timedelta(hours=9)
                        if not (start_dt <= pub_date_kst <= end_dt): is_valid = False
                    except: is_valid = True 
                
                if is_valid:
                    if not any(i['Title'] == item.title.text for i in all_items):
                        all_items.append({
                            'Title': item.title.text,
                            'Link': item.link.text,
                            'Date': item.pubDate.text,
                            'Source': item.source.text if item.source else "Google News",
                            'ParsedDate': pub_date_kst if strict_time else None
                        })
                        kw_collected += 1
                if kw_collected >= per_kw_limit: break
        except: pass
        time.sleep(0.1)
        
    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['Title'])
        if strict_time: df = df.sort_values(by='ParsedDate', ascending=False)
        return df.head(limit).to_dict('records')
    return []

# ==========================================
# 2-1. 글로벌 뉴스
# ==========================================
def translate_text_batch(api_key, texts, target_lang="Korean"):
    if not texts: return []
    model = "gemini-1.5-flash"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            models = [m['name'].replace("models/", "") for m in res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if models: model = models[0]
    except: pass
    prompt = f"Translate the following list of texts to {target_lang}. Return ONLY the translated strings in a JSON array format [\"text1\", \"text2\"...].\n\nTexts: {json.dumps(texts)}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if match: return json.loads(match.group(0))
    except: pass
    return texts

def get_translated_keywords(api_key, keyword):
    prompt = f"Translate '{keyword}' into English, Japanese, Traditional Chinese(TW), Simplified Chinese(CN). Return JSON: {{'EN':'..','JP':'..','TW':'..','CN':'..'}}"
    model = "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            txt = res.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', txt, re.DOTALL)
            if match: return json.loads(match.group(0))
    except: pass
    return {"EN": keyword, "JP": keyword, "TW": keyword, "CN": keyword}

def fetch_news_global(api_key, keywords, days=3):
    TARGETS = {
        "KR": {"gl": "KR", "hl": "ko", "key": "KR"},
        "US": {"gl": "US", "hl": "en", "key": "EN"},
        "JP": {"gl": "JP", "hl": "ja", "key": "JP"},
        "TW": {"gl": "TW", "hl": "zh-TW", "key": "TW"},
        "CN": {"gl": "CN", "hl": "zh-CN", "key": "CN"}
    }
    all_raw_items = []
    per_kw_limit = 3 if len(keywords) > 4 else 5
    for kw in keywords:
        trans_map = get_translated_keywords(api_key, kw)
        trans_map["KR"] = kw
        for country, conf in TARGETS.items():
            search_term = trans_map.get(conf["key"], kw)
            url = f"https://news.google.com/rss/search?q={quote(search_term)}+when:{days}d&hl={conf['hl']}&gl={conf['gl']}&ceid={conf['gl']}:{conf['hl']}"
            try:
                res = requests.get(url, timeout=3, verify=False)
                soup = BeautifulSoup(res.content, 'xml')
                items = soup.find_all('item')
                kw_added = 0
                for item in items:
                    all_raw_items.append({
                        'Title': item.title.text,
                        'Link': item.link.text,
                        'Date': item.pubDate.text,
                        'Source': f"[{country}] {item.source.text if item.source else 'Google News'}",
                        'Lang': conf['key']
                    })
                    kw_added += 1
                    if kw_added >= per_kw_limit: break
            except: pass
            time.sleep(0.1)
    if not all_raw_items: return []
    df = pd.DataFrame(all_raw_items)
    df = df.drop_duplicates(subset=['Title'])
    items_to_process = df.head(40).to_dict('records')
    titles_to_translate = [x['Title'] for x in items_to_process if x['Lang'] != "KR"]
    indices_to_translate = [i for i, x in enumerate(items_to_process) if x['Lang'] != "KR"]
    if titles_to_translate:
        translated_titles = translate_text_batch(api_key, titles_to_translate)
        for idx, new_title in zip(indices_to_translate, translated_titles):
            if idx < len(items_to_process):
                items_to_process[idx]['Title'] = f"{new_title} <span style='font-size:0.8em; color:#94A3B8;'>({items_to_process[idx]['Title']})</span>"
    return items_to_process

# ==========================================
# 3. AI 리포트 생성 (기존 유지)
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
    def replace_match(match):
        try:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(news_data):
                link = news_data[idx]['Link']
                return f"<a href='{link}' target='_blank' class='text-blue-600 font-bold hover:underline'>[{match.group(1)}]</a>"
        except: pass
        return match.group(0)
    return re.sub(r'\[(\d+)\]', replace_match, report_text)

def generate_report_with_citations(api_key, news_data):
    models = get_available_models(api_key)
    if not models:
        models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    else:
        if "gemini-1.5-flash" in models:
            models.remove("gemini-1.5-flash")
            models.insert(0, "gemini-1.5-flash")
    
    news_context = ""
    for i, item in enumerate(news_data):
        clean_title = re.sub(r'<[^>]+>', '', item['Title'])
        news_context += f"[{i+1}] {clean_title} (Source: {item['Source']})\n"

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
    - 오늘 반도체 시장의 핵심 분위기와 가장 중요한 변화를 3~4문장으로 요약.

    ## 🚨 Key Issues & Deep Dive (핵심 이슈 심층 분석)
    - 가장 중요한 이슈 2~3가지를 선정하여 소제목을 달고 분석하세요.
    - **중요**: 현상, 원인, 전망을 구분하여 나열하지 말고, **깊이 있는 서술형 문단**으로 작성하세요. 사건의 배경부터 파급 효과까지 매끄럽게 연결되도록 하세요.
    - 반드시 인용 번호[n]를 포함할 것.

    ## 🕸️ Supply Chain & Tech Trends (공급망 및 기술 동향)
    - 반도체 소재 그리고 소부장, 파운드리, 메모리 등 섹터별 주요 단신을 종합하여 서술.

    ## 💡 Analyst's View (투자 아이디어)
    - 오늘의 뉴스가 주는 시사점과 향후 관전 포인트 한 줄 정리.
    """
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
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
                    return True, inject_links_to_report(raw_text, news_data)
            elif response.status_code == 429:
                time.sleep(1) 
                continue
        except: continue
            
    return False, "AI 분석 실패 (모든 모델 응답 없음)"

# ==========================================
# 4. 메인 앱 UI
# ==========================================
with st.sidebar:
    st.markdown("<h2 class='text-2xl font-bold text-slate-800 mb-4'>Semi-Insight</h2>", unsafe_allow_html=True)
    selected_category = st.radio("카테고리", CATEGORIES, index=0)
    st.markdown("---")
    
    with st.expander("🔐 API Key 설정"):
        user_key = st.text_input("Gemini API Key", type="password")
        if user_key: api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
        else: api_key = ""
    
    st.markdown("<div class='h-4'></div>", unsafe_allow_html=True)
    
    if "GITHUB_TOKEN" in st.secrets:
        st.markdown("<div class='text-xs text-green-600 font-bold mb-2'>✅ GitHub Auto-Sync Active</div>", unsafe_allow_html=True)
    
    with st.expander("📉 Global Stock (실시간)", expanded=True):
        if st.button("🔄 시세 업데이트", use_container_width=True):
            get_stock_prices_grouped.clear()
            st.rerun()
        stock_data = get_stock_prices_grouped()
        if stock_data:
            for cat, items in STOCK_CATEGORIES.items():
                st.markdown(f"<div class='stock-header'>{cat}</div>", unsafe_allow_html=True)
                for name, symbol in items.items():
                    html_info = stock_data.get(name)
                    if html_info: st.markdown(html_info, unsafe_allow_html=True)

c_head, c_info = st.columns([3, 1])
with c_head: st.markdown(f"<h1 class='text-3xl font-bold text-slate-800 mb-2'>{selected_category}</h1>", unsafe_allow_html=True)

# ----------------------------------
# [Mode 1] Daily Report
# ----------------------------------
if selected_category == "Daily Report":
    st.markdown("<div class='bg-blue-50 text-blue-800 px-4 py-3 rounded-lg text-sm mb-6'>ℹ️ 매일 오전 6시 기준 반도체 정보 리포트입니다.</div>", unsafe_allow_html=True)
    
    now_kst = datetime.utcnow() + timedelta(hours=9)
    if now_kst.hour < 6: target_date = (now_kst - timedelta(days=1)).date()
    else: target_date = now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    st.markdown(f"<div class='text-right text-sm text-slate-500 mb-4'>Report Date: <b>{target_date}</b></div>", unsafe_allow_html=True)

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
            st.markdown("<div class='flex flex-wrap gap-2'>", unsafe_allow_html=True)
            cols = st.columns(len(daily_kws) if len(daily_kws) < 8 else 8)
            for i, kw in enumerate(daily_kws):
                if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    # 세션 우선 표시 (화면 깜빡임/데이터 증발 방지)
    history = st.session_state.daily_history
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if not today_report:
        st.info("📢 오늘의 리포트가 아직 생성되지 않았습니다.")
        if st.button("🚀 금일 리포트 생성 시작", type="primary"):
            status_box = st.status("🚀 리포트 생성 프로세스...", expanded=True)
            end_dt = datetime.combine(target_date, dt_time(6, 0))
            start_dt = end_dt - timedelta(hours=18)
            
            status_box.write("📡 뉴스 수집 중 (40건)...")
            news_items = fetch_news(daily_kws, days=2, limit=40, strict_time=True, start_dt=start_dt, end_dt=end_dt)
            
            if not news_items:
                status_box.update(label="⚠️ 조건 미달. 확장 검색 시도...", state="running")
                time.sleep(1)
                news_items = fetch_news(daily_kws, days=1, limit=40, strict_time=False)
            
            if not news_items:
                status_box.update(label="❌ 수집된 뉴스가 없습니다.", state="error")
            else:
                status_box.write(f"🧠 AI 심층 분석 중... ({len(news_items)}건)")
                success, result = generate_report_with_citations(api_key, news_items)
                
                if success:
                    status_box.write("💾 저장 중...")
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 완료!", state="complete", expanded=False)
                    st.rerun()
                else:
                    status_box.update(label="⚠️ AI 분석 실패", state="error")
                    st.error(result)
    else:
        st.success("✅ 리포트 생성 완료")
        if st.button("🔄 리포트 다시 만들기"):
            status_box = st.status("🚀 재생성 중...", expanded=True)
            news_items = fetch_news(daily_kws, days=1, limit=40, strict_time=False)
            if news_items:
                status_box.write("🧠 AI 분석 중...")
                success, result = generate_report_with_citations(api_key, news_items)
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    save_daily_history(save_data)
                    status_box.update(label="🎉 완료!", state="complete", expanded=False)
                    st.rerun()
                else:
                    status_box.update(label="⚠️ 실패", state="error")
                    st.error(result)

    if history:
        st.markdown("<div class='h-8'></div>", unsafe_allow_html=True)
        st.subheader("🗂️ 리포트 아카이브")
        for entry in history:
            is_today = (entry['date'] == target_date_str)
            with st.expander(f"{'🔥 ' if is_today else ''}{entry['date']} Daily Report", expanded=is_today):
                st.markdown(f"""
                <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 leading-relaxed text-gray-800">
                    {entry['report']}
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<h4 class='text-sm font-bold text-slate-500 mt-4 mb-2'>📚 참고 기사</h4>", unsafe_allow_html=True)
                for item in entry.get('articles', []):
                    st.markdown(f"<div class='flex items-start gap-2 mb-1 text-sm text-slate-600'><span class='text-blue-500 font-bold'>📄</span><a href='{item['Link']}' target='_blank' class='hover:text-blue-600 hover:underline transition'>{item['Title']}</a></div>", unsafe_allow_html=True)

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
        
        search_days = c3.slider("검색 기간", 1, 30, 3)

        if st.button("실행 (5개국 검색 + 번역)", type="primary", use_container_width=True, disabled=not bool(api_key)):
            kws = st.session_state.keywords[selected_category]
            if kws:
                with st.spinner("🌍 5개국 뉴스 수집 중..."):
                    news = fetch_news_global(api_key, kws, days=search_days)
                    st.session_state.news_data[selected_category] = news
                    st.rerun()
        
        curr_kws = st.session_state.keywords.get(selected_category, [])
        if curr_kws:
            st.write("")
            st.markdown("<div class='flex flex-wrap gap-2'>", unsafe_allow_html=True)
            cols = st.columns(8)
            for i, kw in enumerate(curr_kws):
                if cols[i%8].button(f"{kw} ×", key=f"gdel_{kw}"):
                    st.session_state.keywords[selected_category].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    data = st.session_state.news_data.get(selected_category, [])
    if data:
        st.markdown(f"<div class='text-sm text-slate-500 mb-4'>총 {len(data)}건 수집됨 (최근 {search_days}일)</div>", unsafe_allow_html=True)
        for item in data:
            st.markdown(f"""
            <div class="news-card">
                <div class="flex justify-between items-start">
                    <div class="text-xs font-bold text-blue-600 mb-1">{item['Source']}</div>
                    <div class="text-xs text-slate-400">{item['Date']}</div>
                </div>
                <a href="{item['Link']}" target="_blank" class="block text-base font-bold text-slate-800 hover:text-blue-600 transition decoration-0">
                    {item['Title']}
                </a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("상단의 '실행' 버튼을 눌러 뉴스를 수집하세요. (API Key 필요)")
