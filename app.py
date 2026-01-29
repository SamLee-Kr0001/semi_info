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

# [필수] 라이브러리
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
        .status-log {
            font-family: monospace;
            font-size: 0.85em;
            background: #f1f5f9;
            padding: 8px;
            border-radius: 5px;
            margin-bottom: 5px;
            border-left: 3px solid #3b82f6;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package", "Daily Report"
]

DAILY_DEFAULT_KEYWORDS = [
    "반도체 소재", "소재 공급망", "희토류 제한", "EUV", 
    "중국 반도체", "일본 반도체", "중국 광물", "반도체 규제", "삼성전자 파운드리", "SK하이닉스 HBM"
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
# 1. 데이터 관리 (주식, 키워드, 히스토리)
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
    if "Daily" in data: data["Daily Report"] = data.pop("Daily")
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
    # 날짜 중복 시 덮어쓰기
    history = [h for h in history if h['date'] != new_report_data['date']]
    history.insert(0, new_report_data) 
    try: 
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f: 
            json.dump(history, f, ensure_ascii=False, indent=4)
    except: pass
    return history

def get_gemini_model(api_key):
    genai.configure(api_key=api_key)
    try: return genai.GenerativeModel('gemini-1.5-flash')
    except: return genai.GenerativeModel('gemini-pro')

def clean_text(text):
    """HTML 태그 제거 및 텍스트 정리"""
    if not text: return ""
    clean = re.sub('<.*?>', '', text) # 태그 제거
    clean = re.sub('\s+', ' ', clean).strip() # 공백 정리
    return clean

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        model = get_gemini_model(api_key)
        content_text = ""
        for i, item in enumerate(articles[:20]): 
            safe_snip = clean_text(item.get('Snippet', ''))[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {safe_snip}\n"
        prompt = f"Role: Analyst. Task: Filter noise. Output: IDs ONLY (e.g., 1, 3). Data:\n{content_text}"
        response = model.generate_content(prompt)
        nums = re.findall(r'\d+', response.text)
        valid_indices = [int(n)-1 for n in nums]
        filtered = [articles[idx] for idx in valid_indices if 0 <= idx < len(articles)]
        return filtered if filtered else articles
    except: return articles

# ==========================================
# 3. 핵심: 안정적 데이터 수집 및 리포트 로직
# ==========================================

def fetch_rss_feed(keyword, days_back=2):
    """구글 뉴스 RSS를 가져오는 기본 함수"""
    url = f"https://news.google.com/rss/search?q={quote(keyword)}+when:{days_back}d&hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            return soup.find_all('item')
    except Exception as e:
        pass
    return []

def parse_and_filter_news(items, keyword, start_dt, end_dt):
    """RSS 아이템 파싱 및 날짜 필터링"""
    parsed_items = []
    for item in items:
        try:
            pub_date_str = item.pubDate.text
            pub_date_utc = pd.to_datetime(pub_date_str).replace(tzinfo=timezone.utc)
            pub_date_kst = pub_date_utc + timedelta(hours=9)
            pub_date_kst_naive = pub_date_kst.replace(tzinfo=None)
            
            # 본문 정리 (HTML 제거)
            raw_desc = item.description.text if item.description else ""
            clean_snip = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)[:500] # 길이 넉넉하게
            
            if start_dt <= pub_date_kst_naive <= end_dt:
                src = item.source.text if item.source else "Google"
                parsed_items.append({
                    'Title': item.title.text,
                    'Source': src,
                    'Date': pub_date_kst_naive,
                    'Link': item.link.text,
                    'Keyword': keyword,
                    'Snippet': clean_snip,
                    'Country': 'KR'
                })
        except Exception: continue
    return parsed_items

def generate_daily_report_process(target_date, keywords, api_key, status_container):
    end_dt = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6)
    start_dt = end_dt - timedelta(hours=18)
    
    log_messages = []
    log_messages.append(f"📅 기준 시간: {start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')} (KST)")
    status_container.markdown("\n".join([f"<div class='status-log'>{msg}</div>" for msg in log_messages]), unsafe_allow_html=True)
    
    all_news = []
    progress_bar = st.progress(0)
    
    # 1. 수집 단계
    for idx, kw in enumerate(keywords):
        items = fetch_rss_feed(kw, days_back=2)
        filtered = parse_and_filter_news(items, kw, start_dt, end_dt)
        
        # [Fallback] 수집된게 없으면 24시간 내 데이터로 범위 확장
        if len(filtered) == 0:
            fallback_items = parse_and_filter_news(items, kw, end_dt - timedelta(hours=24), end_dt + timedelta(hours=24))
            if fallback_items:
                log_messages.append(f"⚠️ '{kw}': 시간내 데이터 없음 → 최근 데이터 {len(fallback_items)}건 대체")
                all_news.extend(fallback_items)
            else:
                log_messages.append(f"❌ '{kw}': 뉴스 없음")
        else:
            log_messages.append(f"✅ '{kw}': {len(filtered)}건 수집")
            all_news.extend(filtered)
            
        status_container.markdown("\n".join([f"<div class='status-log'>{msg}</div>" for msg in log_messages]), unsafe_allow_html=True)
        progress_bar.progress((idx + 1) / len(keywords))
        time.sleep(0.2)

    if not all_news:
        status_container.error("수집된 뉴스가 전혀 없어 리포트를 생성할 수 없습니다.")
        return [], None

    # 2. 데이터 전처리 (AI 입력 최적화)
    df = pd.DataFrame(all_news)
    df = df.drop_duplicates(subset=['Title']).sort_values(by='Date', ascending=False)
    
    # [중요] AI에게 보낼 기사 개수를 20개로 제한하여 안정성 확보 (Too many tokens 에러 방지)
    final_articles = df.head(20).to_dict('records')
    
    log_messages.append(f"🤖 총 {len(final_articles)}건(최신순) 기반 AI 분석 시작... (잠시만 기다려주세요)")
    status_container.markdown("\n".join([f"<div class='status-log'>{msg}</div>" for msg in log_messages]), unsafe_allow_html=True)
    
    try:
        model = get_gemini_model(api_key)
        
        # 문맥 생성 (깔끔하게 정리)
        context = ""
        for i, item in enumerate(final_articles):
            d_str = item['Date'].strftime('%H:%M')
            clean_s = clean_text(item['Snippet'])
            # 제목과 요약을 합쳐서 전달
            context += f"Article {i+1}: [{d_str}] {item['Title']}\nContent: {clean_s}\n\n"
            
        prompt = f"""
        당신은 한국 반도체 산업 전문 애널리스트입니다.
        아래 데이터는 **{start_dt.strftime('%m월 %d일 %H:%M')}부터 {end_dt.strftime('%m월 %d일 %H:%M')}까지** 수집된 뉴스입니다.
        정보를 바탕으로 **{target_date.strftime('%Y년 %m월 %d일')} Daily Report**를 작성하세요.
        
        [작성 양식]
        ## 📊 Executive Summary
        (전체 흐름을 3문장으로 요약)
        
        ## 🚨 Top Headlines
        (가장 중요한 이슈 3가지 심층 분석)
        
        ## 📉 시장 및 공급망 동향
        (기업, 소재/부품/장비 동향 정리)
        
        ## 💡 Analyst Insight
        (투자자 및 업계 관계자를 위한 한 줄 평)

        [뉴스 데이터]
        {context}
        """
        
        # [안정성] 타임아웃 방지를 위해 생성 설정 (stream=False)
        response = model.generate_content(prompt)
        
        if not response.text:
            raise Exception("AI가 빈 응답을 보냈습니다.")
            
        report_text = response.text
        
        save_data = {
            'date': target_date.strftime('%Y-%m-%d'),
            'report': report_text,
            'articles': final_articles
        }
        save_daily_history(save_data)
        
        return final_articles, report_text
        
    except Exception as e:
        status_container.error(f"⚠️ AI 리포트 생성 실패: {str(e)}")
        # 에러가 나도 수집된 기사 목록은 반환하여 보여줌
        return final_articles, None

def perform_crawling_general(category, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    prog = st.progress(0)
    all_res = []
    
    def crawl_simple(kw, cc, lang):
        url = f"https://news.google.com/rss/search?q={quote(kw)}&hl={lang}&gl={cc}&ceid={cc}:{lang}"
        try:
            r = requests.get(url, timeout=5, verify=False)
            if r.status_code == 200:
                s = BeautifulSoup(r.content, 'xml')
                items = s.find_all('item')[:3]
                parsed = []
                for it in items:
                    parsed.append({
                        'Title': it.title.text, 'Source': "Google", 'Date': datetime.now(),
                        'Link': it.link.text, 'Keyword': kw, 'Snippet': "", 'AI_Verified': False
                    })
                return parsed
        except: return []
        return []

    for i, kw in enumerate(kws):
        prog.progress((i+1)/len(kws))
        all_res.extend(crawl_simple(kw, 'KR', 'ko'))
        all_res.extend(crawl_simple(kw, 'US', 'en'))
        time.sleep(0.1)
    prog.empty()
    
    if all_res:
        df = pd.DataFrame(all_res)
        df = df.drop_duplicates('Title')
        final_list = df.head(40).to_dict('records')
        if api_key: final_list = filter_with_gemini(final_list, api_key)
        st.session_state.news_data[category] = final_list
    else:
        st.session_state.news_data[category] = []

# ==========================================
# 4. 앱 초기화
# ==========================================
if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None
if 'daily_history' not in st.session_state: st.session_state.daily_history = load_daily_history()

# ==========================================
# 5. UI Layout
# ==========================================
with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    selected_category = st.radio("카테고리", CATEGORIES, index=len(CATEGORIES)-1, label_visibility="collapsed")
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

c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)

if selected_category == "Daily Report":
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_date = (now_kst - timedelta(days=1)).date() if now_kst.hour < 6 else now_kst.date()
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    with c_info:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Report Date (KST)<br><b>{target_date}</b></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("##### ⚙️ Settings (Korea Focus)")
        c_k1, c_k2 = st.columns([3, 1])
        with c_k1: new_kw = st.text_input("키워드 추가", label_visibility="collapsed")
        with c_k2:
            if st.button("추가", use_container_width=True):
                if new_kw and new_kw not in st.session_state.keywords["Daily Report"]:
                    st.session_state.keywords["Daily Report"].append(new_kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        
        daily_kws = st.session_state.keywords["Daily Report"]
        if daily_kws:
            st.write("")
            cols = st.columns(8)
            for i, kw in enumerate(daily_kws):
                if cols[i%8].button(f"{kw} ×", key=f"d_{kw}", type="secondary"):
                    st.session_state.keywords["Daily Report"].remove(kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()

    history = load_daily_history()
    today_report = next((h for h in history if h['date'] == target_date_str), None)
    
    if today_report:
        st.success(f"✅ {target_date} 리포트가 이미 발행되었습니다.")
    else:
        st.info(f"📢 {target_date} 리포트가 없습니다.")
        if api_key:
            if st.button("🚀 리포트 생성 시작 (전일 12:00 ~ 금일 06:00)", type="primary"):
                status_container = st.status("작업 시작...", expanded=True)
                _, _ = generate_daily_report_process(target_date, daily_kws, api_key, status_container)
                st.rerun()
        else:
            st.error("API Key가 필요합니다.")

    if history:
        for idx, entry in enumerate(history):
            st.markdown(f"<div class='history-header'>📅 {entry['date']} Daily Report</div>", unsafe_allow_html=True)
            if entry.get('report'):
                st.markdown(f"<div class='report-box'>{entry['report']}</div>", unsafe_allow_html=True)
            else:
                st.warning("리포트 내용이 없습니다.")
                
            with st.expander(f"🔗 Reference Articles ({len(entry.get('articles', []))})"):
                for i, item in enumerate(entry.get('articles', [])):
                    d_str = pd.to_datetime(item['Date']).strftime('%m/%d %H:%M')
                    st.markdown(f"{i+1}. **[{item['Title']}]({item['Link']})** <span style='color:#999; font-size:0.8em'> | {item['Source']} ({d_str})</span>", unsafe_allow_html=True)

else:
    with c_info: 
        if st.session_state.last_update:
            st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Updated: {st.session_state.last_update}</div>", unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 2.5, 1])
        with c1: st.write("")
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
