import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, time as dt_time, timedelta
import json
import os
import re
import time
import yfinance as yf
import traceback

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 0. 페이지 설정
# ==========================================
st.set_page_config(layout="wide", page_title="Semi-Insight Hub (Auto-Fix)", page_icon="💠")

CATEGORIES = ["Daily Report", "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", "Process Gas", "Wafer", "Package"]

if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}

if 'daily_history' not in st.session_state:
    st.session_state.daily_history = []

# [중요] 사용 가능한 모델 리스트를 저장할 세션
if 'available_models' not in st.session_state:
    st.session_state.available_models = []

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        
        .report-box { background-color: #FFFFFF; padding: 50px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; font-size: 16px; }
        .report-box h2 { color: #1E3A8A; border-bottom: 2px solid #3B82F6; padding-bottom: 10px; margin-top: 30px; margin-bottom: 20px; font-size: 24px; font-weight: 700; }
        
        .debug-log { font-family: monospace; font-size: 12px; background: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 4px solid #333; }
        .error-log { font-family: monospace; font-size: 13px; background: #FFEEEE; color: #CC0000; padding: 15px; border-radius: 5px; border: 1px solid #FF0000; margin-top: 10px; white-space: pre-wrap; }
        
        .ref-link { font-size: 0.9em; color: #555; text-decoration: none; display: block; margin-bottom: 6px; padding: 5px; border-radius: 4px; transition: background 0.2s; }
        .ref-link:hover { background-color: #F1F5F9; color: #2563EB; }
        .ref-number { font-weight: bold; color: #3B82F6; margin-right: 8px; background: #DBEAFE; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
        
        sup a { text-decoration: none; color: #3B82F6; font-weight: bold; margin-left: 2px; font-size: 0.8em; }
        sup a:hover { text-decoration: underline; color: #1D4ED8; }
        
        .news-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 10px; }
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 600 !important; }
        .stock-header { font-size: 13px; font-weight: 700; color: #475569; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }
    </style>
""", unsafe_allow_html=True)

STOCK_CATEGORIES = {
    "🏭 Chipmakers": {"Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU", "TSMC": "TSM", "Intel": "INTC"},
    "🧠 Fabless": {"Nvidia": "NVDA", "Broadcom": "AVGO", "Qnity (Q)": "Q"},
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T", "KLA": "KLAC", "Hanmi": "042700.KS"},
    "🧪 Materials": {"Shin-Etsu": "4063.T", "Sumitomo": "4005.T", "TOK": "4186.T", "Merck": "MRK.DE", "Soulbrain": "357780.KS", "Dongjin": "005290.KS", "ENF": "102710.KS", "Ycchem": "232140.KS"},
    "🔋 Others": {"Samsung SDI": "006400.KS"}
}

KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json'

# ==========================================
# 1. 데이터 관리 함수
# ==========================================
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
                    cur_sym = "₩" if ".KS" in symbol else ("¥" if ".T" in symbol else ("€" if ".DE" in symbol else "$"))
                    fmt_price = f"{cur_sym}{current:,.0f}" if cur_sym in ["₩", "¥"] else f"{cur_sym}{current:,.2f}"
                    result_map[symbol] = {"Price": fmt_price, "Delta": f"{change:,.2f} ({pct:+.2f}%)"}
            except: pass
    except: pass
    return result_map

# ==========================================
# 2. 모델 자동 검색 (핵심 해결책)
# ==========================================
def discover_models(api_key):
    """
    구글 서버에 직접 물어봐서 사용 가능한 모델 목록을 가져옴.
    이 함수가 성공하면 API Key는 확실히 작동하는 것임.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # 'generateContent' 기능을 지원하는 모델만 필터링
            models = [
                m['name'] for m in data.get('models', []) 
                if 'generateContent' in m.get('supportedGenerationMethods', [])
            ]
            # gemini-1.5-flash나 pro를 우선순위로 정렬
            models.sort(key=lambda x: 'flash' not in x) # Flash 우선
            return True, models
        else:
            return False, f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# ==========================================
# 3. 뉴스 수집
# ==========================================
def fetch_news_strict_window(keywords, start_dt, end_dt, debug_container):
    all_items = []
    debug_container.markdown(f"<div class='debug-log'>🕒 Time Filter: {start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')}</div>", unsafe_allow_html=True)
    
    total_found = 0
    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={quote(kw)}+when:2d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            total_found += len(items)
            
            for item in items:
                try:
                    pub_date_str = item.pubDate.text
                    pub_date_gmt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                    pub_date_kst = pub_date_gmt + timedelta(hours=9)
                    
                    if start_dt <= pub_date_kst <= end_dt:
                        all_items.append({
                            'Title': item.title.text,
                            'Link': item.link.text,
                            'Date': pub_date_str,
                            'Source': item.source.text if item.source else "Google News",
                            'Timestamp': pub_date_kst
                        })
                except: continue
        except Exception as e:
            debug_container.error(f"Crawling Error ({kw}): {e}")
            continue
        time.sleep(0.1)
    
    debug_container.markdown(f"<div class='debug-log'>🔎 Fetched {total_found} items -> Filtered {len(all_items)} valid items.</div>", unsafe_allow_html=True)

    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.sort_values(by='Timestamp', ascending=False)
        df = df.drop_duplicates(subset=['Title'])
        return df.head(20).to_dict('records')
    return []

def fetch_news_general(keywords, limit=20):
    all_items = []
    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={quote(kw)}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            for item in items:
                all_items.append({
                    'Title': item.title.text,
                    'Link': item.link.text,
                    'Source': item.source.text if item.source else "Google News"
                })
        except: pass
    
    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['Title'])
        return df.head(limit).to_dict('records')
    return []

# ==========================================
# 4. AI 분석 (Auto-Discovery 적용)
# ==========================================
def inject_links_to_report(report_text, news_data):
    def replace_match(match):
        try:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(news_data):
                link = news_data[idx]['Link']
                return f"<sup><a href='{link}' target='_blank' style='text-decoration:none; color:#3B82F6;'>[{match.group(1)}]</a></sup>"
        except: pass
        return match.group(0)
    return re.sub(r'\[(\d+)\]', replace_match, report_text)

def generate_report_smart(api_key, news_data, debug_container):
    # 1. 서버에 직접 물어봐서 모델 리스트 확보
    if not st.session_state.available_models:
        debug_container.info("🔄 Checking available models from Google API...")
        is_ok, models_or_err = discover_models(api_key)
        if is_ok:
            st.session_state.available_models = models_or_err
            debug_container.success(f"✅ Found models: {', '.join([m.split('/')[-1] for m in models_or_err[:3]])}...")
        else:
            return False, f"Failed to list models. Key might be invalid. Error: {models_or_err}"
    
    models = st.session_state.available_models
    
    # 2. 호출 로직
    def call_gemini(current_news):
        news_context = ""
        for i, item in enumerate(current_news):
            news_context += f"[{i+1}] {item['Title']} (Source: {item['Source']})\n"

        prompt = f"""
        당신은 글로벌 반도체 투자 및 전략 수석 애널리스트입니다. 
        제공된 뉴스 데이터를 바탕으로 전문가 수준의 **[일일 반도체 심층 분석 보고서]**를 작성하세요.

        **[작성 원칙]**
        1. **서술형 작성**: 이슈별로 현상/원인/전망을 나누지 말고, 자연스러운 논리적 흐름(Narrative)으로 서술하세요.
        2. **근거 명시**: 내용의 출처가 되는 뉴스 번호 **[1], [2]**를 문장 끝에 반드시 인용하세요.
        3. **전문적 어조**: 투자자 리포트 톤앤매너를 유지하세요.

        [뉴스 데이터]
        {news_context}
        
        [보고서 구조 (Markdown)]
        ## 📊 Executive Summary (시장 총평)
        - 오늘 반도체 시장의 핵심 분위기와 가장 중요한 변화 요약.

        ## 🚨 Key Issues & Deep Dive (핵심 이슈 심층 분석)
        - 중요 이슈 2~3가지를 선정하여 소제목을 달고 분석.
        - 배경, 원인, 파급 효과를 연결하여 깊이 있게 서술.

        ## 🕸️ Supply Chain & Tech Trends (공급망 및 기술 동향)
        - 소부장, 파운드리, 메모리 등 섹터별 주요 단신 종합.

        ## 💡 Analyst's View (투자 아이디어)
        - 오늘의 뉴스가 주는 시사점과 향후 관전 포인트.
        """
        
        headers = {'Content-Type': 'application/json'}
        data = {"contents": [{"parts": [{"text": prompt}]}], "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]}

        for model in models:
            # [중요] 모델명 정규화 (models/models/gemini... 방지)
            clean_model = model.replace("models/", "")
            
            # 불안정한 2.0 및 exp 버전은 건너뜀 (안전빵)
            if "gemini-2.0" in clean_model or "exp" in clean_model:
                continue

            debug_container.markdown(f"<div class='debug-log'>🔄 Trying Model: {clean_model} (Items: {len(current_news)})...</div>", unsafe_allow_html=True)
            
            # v1beta 엔드포인트에 models/ 접두사 없이 요청 (또는 있는 경우도 처리)
            # 가장 확실한 URL 구조: models/{clean_model}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
            
            try:
                response = requests.post(url, headers=headers, json=data, timeout=90)
                
                if response.status_code == 200:
                    res_json = response.json()
                    if 'candidates' in res_json and res_json['candidates']:
                        raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                        debug_container.success(f"✅ Success with {clean_model}")
                        return True, inject_links_to_report(raw_text, current_news)
                    else:
                        debug_container.warning(f"⚠️ {clean_model} Blocked/Empty")
                else:
                    error_msg = f"❌ {clean_model} Failed: {response.status_code}"
                    debug_container.markdown(f"<div class='error-log'>{error_msg}</div>", unsafe_allow_html=True)
                    
                    if response.status_code == 403:
                        return False, "API Key Blocked (403)."
                    if response.status_code == 429:
                        return False, "429" 

            except Exception as e:
                debug_container.error(f"💥 Exception: {str(e)}")
                continue
        return False, "All tested models failed"

    # [1차 시도]
    success, result = call_gemini(news_data)
    
    if success:
        return True, result
    elif result == "429":
        debug_container.warning("⚠️ 429 Quota Error. Retrying with 10 items...")
        time.sleep(3)
        return call_gemini(news_data[:10])
    else:
        return False, result

# ==========================================
# 5. 메인 UI
# ==========================================
if 'keywords' not in st.session_state: 
    st.session_state.keywords = load_keywords()

with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    selected_category = st.radio("카테고리", CATEGORIES, index=0, label_visibility="collapsed")
    st.divider()
    
    api_key = ""
    with st.expander("🔐 API Key Status", expanded=True):
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("✅ Key Loaded from Secrets")
            
            # [진단] 키가 로드되면 사용 가능한 모델을 즉시 확인
            if st.button("Check Models"):
                is_ok, models = discover_models(api_key)
                if is_ok:
                    st.success(f"Models: {len(models)} found.")
                    st.session_state.available_models = models
                else:
                    st.error(f"Key Invalid: {models}")
        else:
            st.warning("⚠️ No Secrets Found")
            api_key = st.text_input("Manually Enter Key", type="password")

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

if selected_category == "Daily Report":
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
        
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            cols = st.columns(len(daily_kws) if len(daily_kws) < 8 else 8)
            for i, kw in enumerate(daily_kws):
                if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        st.caption("⚠️ 관심 키워드를 추가하면 해당 주제로 보고서에 반영됩니다.")
    
    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if today_report:
        st.success(f"✅ {target_date} 리포트가 생성되어 있습니다.")
    else:
        st.info(f"📢 {target_date} 리포트가 아직 없습니다.")

    if st.button("🚀 리포트 생성 (덮어쓰기)", type="primary", disabled=not bool(api_key)):
        debug_box = st.container(border=True)
        debug_box.write("🛠️ **Processing Log**")
        
        end_dt = now_kst
        start_dt = datetime.combine(target_date - timedelta(days=1), dt_time(12, 0))
        
        news_items = fetch_news_strict_window(daily_kws, start_dt, end_dt, debug_box)
        
        if not news_items:
            debug_box.warning("⚠️ 지정 시간 내 기사 없음 -> 범위 확장(24h) 시도...")
            news_items = fetch_news_general(daily_kws, limit=20)
            debug_box.write(f"🔄 Fallback 수집 결과: {len(news_items)}건")
        
        if not news_items:
            debug_box.error("❌ 최종 기사 수집 실패.")
        else:
            debug_box.write(f"🧠 AI 분석 시작... (입력 기사: {len(news_items)}건)")
            success, result = generate_report_smart(api_key, news_items, debug_box)
            
            if success:
                save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                save_daily_history(save_data)
                debug_box.success("🎉 생성 완료! 페이지를 새로고침 합니다.")
                time.sleep(2)
                st.rerun()
            else:
                debug_box.error(f"🚨 최종 실패: {result}")

    if history:
        for entry in history:
            st.divider()
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            with st.expander(f"📚 References (기사 원문) - {len(entry.get('articles', []))}건"):
                ref_cols = st.columns(2)
                for i, item in enumerate(entry.get('articles', [])):
                    col = ref_cols[i % 2]
                    with col:
                        st.markdown(f"""
                        <a href="{item['Link']}" target="_blank" class="ref-link">
                            <span class="ref-number">[{i+1}]</span> {item['Title']}
                        </a>
                        """, unsafe_allow_html=True)

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
                news = fetch_news_general(kws)
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
