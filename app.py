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
# 2. 유틸리티 (파일 I/O, AI)
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
    if not data["Daily"]: data["Daily"] = DAILY_DEFAULT_KEYWORDS
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

def make_smart_query(keyword, country_code):
    base_kw = keyword
    negatives = "-TikTok -틱톡 -douyin -dance -shorts -reels -viral -music -game -soccer"
    contexts = {
        'KR': "(반도체 OR 소자 OR 공정 OR 소재 OR 파운드리 OR 팹 OR 양산)",
        'CN': "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)",
        'HK': "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)",
        'US': "(semiconductor OR chip OR fab OR foundry OR wafer OR lithography)",
        'JP': "(semiconductor OR chip OR fab OR wafer OR resist)",
        'TW': "(semiconductor OR chip OR wafer OR foundry)"
    }
    context = contexts.get(country_code, contexts['US'])
    return f'{base_kw} AND {context} {negatives}'

def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-pro')

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        model = get_gemini_model(api_key)
        content_text = ""
        for i, item in enumerate(articles[:30]): 
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

# [수정] 강력한 크롤링 함수 (헤더 보강 + 타임아웃 연장)
def crawl_single_rss_robust(keyword, country_code, language):
    smart_query = make_smart_query(keyword, country_code)
    url = f"https://news.google.com/rss/search?q={quote(smart_query)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    # 봇 차단 방지를 위한 리얼 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://news.google.com/'
    }
    
    try:
        # [핵심] timeout 10초로 연장
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:3] # 부하 방지를 위해 3개만
            
            parsed_items = []
            for item in items:
                src = item.source.text if item.source else "Google"
                snip = BeautifulSoup(item.description.text if item.description else "", "html.parser").get_text(strip=True)[:200]
                
                # 날짜 파싱 실패해도 무조건 현재 시간으로 채워서 데이터 유실 방지
                pub_date = item.pubDate.text if item.pubDate else str(datetime.now())
                try: dt_obj = pd.to_datetime(pub_date).to_pydatetime()
                except: dt_obj = datetime.now()
                
                parsed_items.append({
                    'Title': item.title.text, 'Source': src, 'Date': dt_obj,
                    'Link': item.link.text, 'Keyword': keyword, 'Snippet': snip,
                    'AI_Verified': False, 'Country': country_code
                })
            return parsed_items
    except Exception as e:
        print(f"Crawl Error: {e}")
    return []

# [핵심] 리포트 생성 (진행률 표시 및 순차 처리)
def process_daily_report_with_progress(target_date, keywords, api_key):
    # 날짜 필터링 제거 (최신순 수집 후 상위 n개 사용)
    # 이유: 날짜 필터가 너무 엄격해서 데이터가 0개가 되는 현상 방지
    
    all_news = []
    search_kws = keywords[:8] 
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_steps = len(search_kws) * 4 
    current_step = 0
    
    # 1. 순차 크롤링
    for kw in search_kws:
        for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW'), ('CN', 'zh-CN')]:
            current_step += 1
            progress_bar.progress(current_step / total_steps)
            status_text.text(f"📡 수집 중... {kw} ({cc})")
            
            # 수집 실행
            news_items = crawl_single_rss_robust(kw, cc, lang)
            all_news.extend(news_items)
            
            # 봇 탐지 방지 지연
            time.sleep(0.2)
            
    df = pd.DataFrame(all_news)
    final_articles = []
    report_text = ""
    
    if not df.empty:
        # 날짜 정렬만 하고 필터링은 하지 않음 (최신 뉴스 30개 무조건 확보)
        df = df.sort_values('Date', ascending=False)
        df = df.drop_duplicates(subset=['Title'])
        
        final_articles = df.head(30).to_dict('records')
        
        if final_articles: 
            status_text.text(f"✅ {len(final_articles)}개 기사 분석 중... AI 리포트 생성 시작")
            progress_bar.progress(0.95)
            
            try:
                model = get_gemini_model(api_key)
                context = ""
                for i, item in enumerate(final_articles):
                    context += f"- [{item['Country']}] {item['Title']}: {item.get('Snippet', '')}\n"
                
                prompt = f"""
                당신은 글로벌 반도체 산업 수석 애널리스트입니다. 
                아래 제공된 다국어 뉴스들을 읽고, '{target_date.strftime('%Y-%m-%d')}' 기준 [일일 반도체 산업 브리핑]을 한국어로 작성하세요.
                
                [뉴스 데이터]
                {context}
                
                [작성 지침]
                1. 언어: **한국어**
                2. 형식: Markdown
                3. 내용:
                   - 🚨 **Key Headlines**: 핵심 뉴스 3가지
                   - 🌍 **Global Issues**: 공급망, 지정학, 규제
                   - 📈 **Tech & Market**: 기술 및 기업 동향
                   - 💡 **Analyst Note**: 종합 의견
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
                
            except Exception as e:
                report_text = f"⚠️ 리포트 생성 실패: {str(e)}"
    else:
        report_text = "해당 키워드로 수집된 뉴스가 없습니다. 키워드를 변경해보세요."
    
    progress_bar.empty()
    status_text.empty()
    
    return final_articles, report_text

def perform_crawling(category, start_date, end_date, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    
    progress_bar = st.progress(0)
    all_news = []
    total_steps = len(kws)
    
    for i, kw in enumerate(kws):
        progress_bar.progress((i+1)/total_steps)
        for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW'), ('CN', 'zh-CN')]:
            all_news.extend(crawl_single_rss_robust(kw, cc, lang))
    
    progress_bar.empty()
    df = pd.DataFrame(all_news)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    if not df.empty:
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        df = df.drop_duplicates(subset=['Title']).sort_values('Date', ascending=False)
        final_list = df.head(50).to_dict('records')
        
        # 일반 모드에서는 사용자 편의를 위해 번역 함수 사용 (여기서는 병렬처리 안함)
        if api_key and final_list: final_list = filter_with_gemini(final_list, api_key)
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
            st.caption("⏳ Loading...")

# ==========================================
# 4. Main UI & Logic
# ==========================================
c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

if selected_category == "Daily":
    now = datetime.now()
    target_date = (now - timedelta(days=1)).date() if now.hour < 6 else now.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Target Date<br><b>{target_date} (06:00 AM)</b></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("##### ⚙️ Daily Settings")
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

    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if not today_report:
        if api_key:
            st.info(f"📢 아직 {target_date}자 리포트가 없습니다.")
            if st.button("🚀 리포트 지금 생성하기", type="primary"):
                 _, _ = process_daily_report_with_progress(target_date, daily_kws, api_key)
                 st.rerun()
        else:
            st.error("API Key가 필요합니다.")
            
    if not history:
        st.write("")
    else:
        for idx, entry in enumerate(history):
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            
            with st.expander(f"🔗 Reference Articles ({len(entry.get('articles', []))})"):
                for i, item in enumerate(entry.get('articles', [])):
                    st.markdown(f"{i+1}. [{item['Title']}]({item['Link']}) <span style='color:#999; font-size:0.8em'> | {item['Source']}</span>", unsafe_allow_html=True)

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
                        st.markdown(f"""<div class="news-meta" style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>📰 {item['Source']}</span><span>{item['Date'].strftime('%Y-%m-%d')}</span></div>""", unsafe_allow_html=True)
                        st.markdown(f'<a href="{item["Link"]}" target="_blank" class="news-title">{item["Title"]}</a>', unsafe_allow_html=True)
                        if item.get('Snippet'): st.markdown(f'<div class="news-snippet">{item["Snippet"]}</div>', unsafe_allow_html=True)
                        st.markdown("---")
                        ft1, ft2 = st.columns([3, 1])
                        with ft1: st.markdown(f"<span style='background:#F1F5F9; color:#64748B; padding:3px 8px; border-radius:4px; font-size:11px;'>#{item['Keyword']}</span>", unsafe_allow_html=True)
                        with ft2:
                            if item.get('AI_Verified'): st.markdown("<span style='color:#4F46E5; font-size:11px; font-weight:bold;'>✨ AI Pick</span>", unsafe_allow_html=True)
    else:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding:30px; color:#999;'>데이터가 없습니다.<br>상단의 '실행' 버튼을 눌러주세요.</div>", unsafe_allow_html=True)
