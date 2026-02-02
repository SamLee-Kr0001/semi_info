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

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 0. 페이지 설정
# ==========================================
st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

CATEGORIES = ["Daily Report", "P&C 소재", "EDTW 소재", "PKG 소재"]

if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}

if 'keywords' not in st.session_state:
    st.session_state.keywords = {cat: [] for cat in CATEGORIES}

if 'daily_history' not in st.session_state:
    st.session_state.daily_history = []

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        html, body, .stApp { font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; color: #1E293B; }
        
        .report-box { background-color: #FFFFFF; padding: 50px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 30px; line-height: 1.8; color: #334155; font-size: 16px; }
        .report-box h2 { color: #1E3A8A; border-bottom: 2px solid #3B82F6; padding-bottom: 10px; margin-top: 30px; margin-bottom: 20px; font-size: 24px; font-weight: 700; }
        
        .news-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 10px; }
        .news-title { font-size: 16px !important; font-weight: 700 !important; color: #111827 !important; text-decoration: none; display: block; margin-bottom: 6px; }
        .news-title:hover { color: #2563EB !important; text-decoration: underline; }
        .news-meta { font-size: 12px !important; color: #94A3B8 !important; }

        .stock-row { display: flex; justify-content: space-between; align-items: center; font-size: 14px; padding: 5px 0; border-bottom: 1px dashed #e2e8f0; }
        .stock-name { font-weight: 600; color: #334155; }
        .stock-price { font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; }
        .up-color { color: #DC2626; }
        .down-color { color: #2563EB; }
        .flat-color { color: #64748B; }
        .stock-header { font-size: 13px; font-weight: 700; color: #475569; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }
        
        .ref-link { font-size: 0.9em; color: #555; text-decoration: none; display: block; margin-bottom: 6px; padding: 5px; border-radius: 4px; transition: background 0.2s; }
        .ref-link:hover { background-color: #F1F5F9; color: #2563EB; }
        .ref-number { font-weight: bold; color: #3B82F6; margin-right: 8px; background: #DBEAFE; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    </style>
""", unsafe_allow_html=True)

STOCK_CATEGORIES = {
    "🏭 Chipmakers": {"Samsung": "005930.KS", "SK Hynix": "000660.KS", "Micron": "MU", "TSMC": "TSM", "Intel": "INTC", "SMIC": "0981.HK"},
    "🧠 Fabless": {"Nvidia": "NVDA", "Broadcom": "AVGO", "Qnity (Q)": "Q"},
    "🧪 Materials": {"Soulbrain": "357780.KQ", "Dongjin": "005290.KQ", "Hana Mat": "166090.KQ", "Wonik Mat": "104830.KQ", "TCK": "064760.KQ", "Foosung": "093370.KS", "PI Adv": "178920.KS", "ENF": "102710.KQ", "TEMC": "425040.KQ", "YC Chem": "112290.KQ", "Samsung SDI": "006400.KS", "Shin-Etsu": "4063.T", "Sumco": "3436.T", "Merck": "MRK.DE", "Entegris": "ENTG", "TOK": "4186.T", "Resonac": "4004.T", "Air Prod": "APD", "Linde": "LIN", "Qnity": "Q", "Nissan Chem": "4021.T", "Sumitomo": "4005.T"},
    "⚙️ Equipment": {"ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T", "KLA": "KLAC", "Advantest": "6857.T", "Hitachi HT": "8036.T", "Hanmi": "042700.KS", "Wonik IPS": "240810.KQ", "Jusung": "036930.KQ", "EO Tech": "039030.KQ", "Techwing": "089030.KQ", "Eugene": "084370.KQ", "PSK": "319660.KQ", "Zeus": "079370.KQ", "Top Eng": "065130.KQ"}
}

# ==========================================
# 1. 데이터 관리 함수
# ==========================================
KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json'

@st.cache_data(ttl=300)
def get_stock_prices_grouped():
    result_map = {}
    for cat, items in STOCK_CATEGORIES.items():
        for name, symbol in items.items():
            try:
                ticker = yf.Ticker(symbol)
                try: 
                    current = ticker.fast_info['last_price']
                    prev = ticker.fast_info['previous_close']
                except:
                    try:
                        hist = ticker.history(period="1d", interval="1m")
                        if not hist.empty:
                            current = hist['Close'].iloc[-1]
                            prev = ticker.info.get('previousClose', current)
                        else: raise ValueError
                    except:
                        hist = ticker.history(period="5d")
                        if len(hist) >= 2:
                            current = hist['Close'].iloc[-1]
                            prev = hist['Close'].iloc[-2]
                        else: continue

                change = current - prev
                pct = (change / prev) * 100
                
                if ".KS" in symbol or ".KQ" in symbol: cur_sym = "₩"
                elif ".T" in symbol: cur_sym = "¥"
                elif ".HK" in symbol: cur_sym = "HK$"
                elif ".DE" in symbol: cur_sym = "€"
                else: cur_sym = "$"
                
                fmt_price = f"{cur_sym}{current:,.0f}" if cur_sym in ["₩", "¥"] else f"{cur_sym}{current:,.2f}"
                
                if change > 0: color_class, arrow, sign = "up-color", "▲", "+"
                elif change < 0: color_class, arrow, sign = "down-color", "▼", ""
                else: color_class, arrow, sign = "flat-color", "-", ""
                
                html_str = f"""<div class="stock-row"><span class="stock-name">{name}</span><span class="stock-price {color_class}">{fmt_price} <span style="font-size:0.9em; margin-left:3px;">{arrow} {sign}{pct:.2f}%</span></span></div>"""
                result_map[name] = html_str
            except Exception: pass
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
    if not data.get("Daily Report"): data["Daily Report"] = ["반도체", "삼성전자", "SK하이닉스"]
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
    # 날짜 중복 시 덮어쓰기 (기존 것 제거)
    history = [h for h in history if h['date'] != new_report_data['date']]
    # 최신이 위로 오게 추가
    history.insert(0, new_report_data)
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass

# ==========================================
# 2. 뉴스 수집 함수
# ==========================================
def fetch_news(keywords, days=1, limit=20, strict_time=False, start_dt=None, end_dt=None):
    all_items = []
    if strict_time and start_dt and end_dt: pass
    else:
        end_dt = datetime.utcnow() + timedelta(hours=9)
        start_dt = end_dt - timedelta(days=days)
    
    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={quote(kw)}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            for item in items:
                try:
                    pub_date_str = item.pubDate.text
                    pub_date_gmt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                    pub_date_kst = pub_date_gmt + timedelta(hours=9)
                    if start_dt <= pub_date_kst <= end_dt:
                        all_items.append({
                            'Title': item.title.text,
                            'Link': item.link.text,
                            'Date': item.pubDate.text,
                            'Source': item.source.text if item.source else "Google News",
                            'ParsedDate': pub_date_kst
                        })
                except: continue
        except: pass
        time.sleep(0.1)
    
    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['Title'])
        df = df.sort_values(by='ParsedDate', ascending=False)
        return df.head(limit).to_dict('records')
    return []

# ==========================================
# 2-1. 글로벌 뉴스 수집 (5개국 + 번역)
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
                for item in items:
                    all_raw_items.append({
                        'Title': item.title.text,
                        'Link': item.link.text,
                        'Date': item.pubDate.text,
                        'Source': f"[{country}] {item.source.text if item.source else 'Google News'}",
                        'Lang': conf['key']
                    })
            except: pass
            time.sleep(0.1)

    if not all_raw_items: return []
    df = pd.DataFrame(all_raw_items)
    df = df.drop_duplicates(subset=['Title'])
    items_to_process = df.head(30).to_dict('records')
    
    titles_to_translate = [x['Title'] for x in items_to_process if x['Lang'] != "KR"]
    indices_to_translate = [i for i, x in enumerate(items_to_process) if x['Lang'] != "KR"]
    
    if titles_to_translate:
        translated_titles = translate_text_batch(api_key, titles_to_translate)
        for idx, new_title in zip(indices_to_translate, translated_titles):
            if idx < len(items_to_process):
                items_to_process[idx]['Title'] = f"{new_title} <span style='font-size:0.8em; color:#999;'>({items_to_process[idx]['Title']})</span>"
    return items_to_process

# ==========================================
# 3. AI 리포트 생성
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
                return f"[[{match.group(1)}]]({link})"
        except: pass
        return match.group(0)
    return re.sub(r'\[(\d+)\]', replace_match, report_text)

def generate_report_with_citations(api_key, news_data):
    models = get_available_models(api_key)
    if not models: models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    news_context = ""
    for i, item in enumerate(news_data):
        clean_title = re.sub(r'<[^>]+>', '', item['Title'])
        news_context += f"[{i+1}] {clean_title} (Source: {item['Source']})\n"

    prompt = f"""
    당신은 글로벌 반도체 투자 및 전략 수석 애널리스트입니다. 
    제공된 뉴스 데이터를 바탕으로 전문가 수준의 **[일일 반도체 심층 분석 보고서]**를 작성하세요.

    **[작성 원칙]**
    1. **서술형 작성**: 이슈별로 현상/원인/전망을 자연스러운 논리적 흐름(Narrative)으로 서술하세요.
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
if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()

with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    selected_category = st.radio("카테고리", CATEGORIES, index=0, label_visibility="collapsed")
    st.divider()
    
    with st.expander("🔐 API Key"):
        user_key = st.text_input("Key", type="password")
        if user_key: api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
        else: api_key = ""
    
    st.markdown("---")
    
    with st.expander("📉 Global Stock", expanded=True):
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
    st.caption("ℹ️ '시세 업데이트' 버튼을 누르면 최신가로 갱신됩니다.")

c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

# ----------------------------------
# [Mode 1] Daily Report (완벽 복원 + 기능 추가)
# ----------------------------------
if selected_category == "Daily Report":
    st.info("ℹ️ 매일 오전 6시 기준 반도체 소재관련 정보 Report 입니다.")
    now_kst = datetime.utcnow() + timedelta(hours=9)
    if now_kst.hour < 6: target_date = (now_kst - timedelta(days=1)).date()
    else: target_date = now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info: st.markdown(f"<div style='text-align:right; color:#888;'>Report Date<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    # [기능 1] 검색어 유지 관리
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        new_kw = c1.text_input("수집 키워드 추가", placeholder="예: HBM, 패키징", label_visibility="collapsed")
        if c2.button("추가", use_container_width=True):
            if new_kw and new_kw not in st.session_state.keywords["Daily Report"]:
                st.session_state.keywords["Daily Report"].append(new_kw)
                save_keywords(st.session_state.keywords) # [저장]
                st.rerun()
        
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            cols = st.columns(len(daily_kws) if len(daily_kws) < 8 else 8)
            for i, kw in enumerate(daily_kws):
                if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords) # [저장]
                    st.rerun()
        st.caption("⚠️ 관심 키워드는 자동 저장됩니다.")
    
    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    # 금일 리포트 상태 표시
    if not today_report:
        st.info(f"📢 {target_date} 리포트가 아직 생성되지 않았습니다.")
        if st.button("🚀 금일 리포트 생성 시작", type="primary"):
            status_box = st.status("🚀 리포트 생성 프로세스...", expanded=True)
            end_dt = datetime.combine(target_date, dt_time(6, 0))
            start_dt = end_dt - timedelta(hours=18)
            status_box.write(f"📡 뉴스 수집 중 ({start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')})...")
            news_items = fetch_news(daily_kws, days=2, strict_time=True, start_dt=start_dt, end_dt=end_dt)
            
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
        # [덮어쓰기 버튼]
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

    # [기능 2] 리포트 날짜별 하단 저장 (Expander 방식)
    if history:
        st.markdown("---")
        st.subheader("🗂️ 지난 리포트 기록")
        for entry in history:
            with st.expander(f"📅 {entry['date']} Daily Report", expanded=(entry['date'] == target_date_str)):
                st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
                # 원문 링크 표시
                st.markdown("#### 📚 기사 원문 링크")
                ref_cols = st.columns(2)
                for i, item in enumerate(entry.get('articles', [])):
                    col = ref_cols[i % 2]
                    with col:
                        st.markdown(f"""<a href="{item['Link']}" target="_blank" class="ref-link"><span class="ref-number">[{i+1}]</span> {item['Title']}</a>""", unsafe_allow_html=True)

# ----------------------------------
# [Mode 2] General Category (P&C, EDTW, PKG)
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
        
        search_days = c3.slider("검색 기간(일)", min_value=1, max_value=30, value=3, help="최근 N일간 뉴스를 검색")

        if st.button("실행 (5개국 검색 + 번역)", type="primary", use_container_width=True, disabled=not bool(api_key)):
            kws = st.session_state.keywords[selected_category]
            if kws:
                with st.spinner("🌍 5개국(KR/US/JP/TW/CN) 뉴스 수집 및 번역 중..."):
                    news = fetch_news_global(api_key, kws, days=search_days)
                    st.session_state.news_data[selected_category] = news
                    st.rerun()
        
        curr_kws = st.session_state.keywords.get(selected_category, [])
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
        st.write(f"총 {len(data)}건 수집됨 (최근 {search_days}일)")
        for item in data:
            st.markdown(f"""<div class="news-card"><div class="news-meta">{item['Source']} | {item['Date']}</div><a href="{item['Link']}" target="_blank" class="news-title" style="text-decoration:none;">{item['Title']}</a></div>""", unsafe_allow_html=True)
    else:
        st.info("상단의 '실행' 버튼을 눌러 뉴스를 수집하세요. (API Key 필요)")
