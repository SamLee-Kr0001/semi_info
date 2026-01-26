import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import json
import os
import re

# Google Gemini
import google.generativeai as genai

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ==========================================
# 0. 설정 및 CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semiconductor News Crawler")

st.markdown("""
    <style>
        .block-container {
            padding-top: 4.5rem !important; 
            padding-bottom: 2rem !important;
        }
        h1 {
            font-size: clamp(1.5rem, 2.5vw, 3rem) !important;
            margin-bottom: 1rem !important;
            line-height: 1.2 !important;
        }
        h3 { font-size: clamp(1rem, 1.5vw, 1.8rem) !important; }
        .sidebar-footer { position: fixed; bottom: 10px; left: 20px; font-size: 10px; color: #888; z-index: 999; }
        a { text-decoration: none; color: #0366d6; }
        a:hover { text-decoration: underline; }
        .ai-tag {
            background-color: #092C4C;
            color: #FFFFFF;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.7em;
            font-weight: bold;
            margin-left: 8px;
            vertical-align: middle;
        }
        .snippet-text {
            color: #555;
            font-size: 0.85em;
            margin-top: 4px;
            line-height: 1.4;
            border-left: 3px solid #eee;
            padding-left: 10px;
        }
        div.stButton > button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 키워드 관리
# ==========================================
KEYWORD_FILE = 'keywords.json'

def load_keywords():
    data = {cat: [] for cat in CATEGORIES}
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            for key, val in loaded_data.items():
                if key in data: data[key] = val
        except: pass
    return data

def save_keywords(keywords_dict):
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(keywords_dict, f, ensure_ascii=False, indent=4)
    except: pass

if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None

# ==========================================
# 2. 스마트 쿼리 생성기 (Pre-Screening)
# ==========================================
def make_smart_query(keyword, country_code):
    """
    [핵심 기능]
    검색어에 '반도체 문맥'을 강제로 주입하고 '노이즈(틱톡)'를 제외하는 쿼리 생성
    """
    # 1. 기본 키워드 보호 (따옴표 처리 등은 검색엔진 유연성을 위해 제거)
    base_kw = keyword

    # 2. 강력한 제외어 (Negative Keywords) - 틱톡, 댄스, SNS 등 원천 차단
    negatives = "-TikTok -틱톡 -douyin -dance -shorts -reels -viral -music -influencer -fashion"

    # 3. 문맥 강제 주입 (Context Injection)
    # 국가별로 반도체 관련 용어를 OR 조건으로 묶어서 AND 결합
    if country_code == 'KR':
        context = "(반도체 OR 소자 OR 공정 OR 소재 OR 파운드리 OR 팹)"
    elif country_code == 'CN':
        context = "(半导体 OR 芯片 OR 晶圆 OR 光刻胶)"
    elif country_code == 'JP':
        context = "(半導体 OR 　シリコン OR ウェーハ)" # 일본어 전각 띄어쓰기 고려
    else: # US/Global
        context = "(semiconductor OR chip OR fab OR foundry OR wafer OR lithography)"

    # 최종 쿼리 조합: "TOK" AND (반도체 OR ...) -TikTok
    final_query = f'{base_kw} AND {context} {negatives}'
    
    return final_query

# ==========================================
# 3. AI 필터링 엔진 (Post-Screening)
# ==========================================
def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        content_text = ""
        for i, item in enumerate(articles):
            snippet = item.get('Snippet', '')
            content_text += f"ID_{i+1} | KW: {item['Keyword']} | Title: {item['Title']} | Snippet: {snippet}\n"
            
        prompt = f"""
        Role: Strict Semiconductor Intelligence Analyst.
        Task: Identify strictly relevant articles for B2B Semiconductor Manufacturing.

        *** DOUBLE CHECK RULES ***
        1. [Homonym Check] 'TOK' = 'Tokyo Ohka Kogyo'. REJECT 'TikTok', 'Social Media' immediately.
        2. [Context Check] Must be related to Fab, Materials, Equipment, or Chip Tech.
        3. [Noise Check] Reject stock buzz without technical reason.

        *** DATA ***
        {content_text}

        *** OUTPUT ***
        Return IDs of valid articles separated by commas (e.g., 1, 3). If none, return None.
        """
        
        response = model.generate_content(prompt)
        response_text = response.text
        if "None" in response_text and len(response_text) < 10: return []
            
        valid_indices = [int(num) - 1 for num in re.findall(r'\d+', response_text)]
        
        filtered = []
        for idx in valid_indices:
            if 0 <= idx < len(articles):
                articles[idx]['AI_Verified'] = True 
                filtered.append(articles[idx])
        return filtered
    except Exception as e:
        print(f"AI Error: {e}")
        return articles

# ==========================================
# 4. 크롤링 엔진
# ==========================================
def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def parse_date(date_str):
    try:
        now = datetime.now()
        date_str = str(date_str).strip()
        if any(x in date_str for x in ['시간', 'hour', '분', 'min']): return now
        if any(x in date_str for x in ['일 전', 'day']):
            days = int(re.search(r'\d+', date_str).group())
            return now - timedelta(days=days)
        return pd.to_datetime(date_str).to_pydatetime()
    except: return datetime.now()

def crawl_bing_china(keyword, debug_mode=False):
    results = []
    # [수정] 스마트 쿼리 적용 (중국)
    smart_query = make_smart_query(keyword, 'CN')
    # Ijiwei 사이트 타겟팅 + 스마트 쿼리
    search_query = f"site:ijiwei.com {smart_query}"
    base_url = f"https://cn.bing.com/news/search?q={quote(search_query)}"
    
    if debug_mode: st.write(f"🇨🇳 [Bing Query] `{smart_query}`")

    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=zh-CN")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(base_url)
        try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "news-card")))
        except: time.sleep(1)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        articles = soup.find_all('div', class_='news-card')
        for item in articles:
            try:
                title = item.find('a', class_='title').get_text(strip=True)
                link = item.find('a', class_='title')['href']
                snippet_tag = item.find('div', class_='snippet')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                source_tag = item.find('div', class_='source'); date_str = str(datetime.now().date())
                if source_tag:
                    spans = source_tag.find_all('span')
                    if len(spans) >= 1: date_str = spans[-1].get_text(strip=True)
                
                results.append({
                    'Title': title, 'Source': "Ijiwei (via Bing)", 'Date': parse_date(date_str), 
                    'Link': link, 'Keyword': keyword, 'Snippet': snippet, 'AI_Verified': False
                })
            except: continue
    except: pass
    finally:
        if driver: driver.quit()
    return results

def crawl_google_news(keyword, country_code, language, debug_mode=False):
    results = []
    # [수정] 스마트 쿼리 적용 (국가별)
    smart_query = make_smart_query(keyword, country_code)
    
    base_url = f"https://news.google.com/rss/search?q={quote(smart_query)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    if debug_mode: st.write(f"📡 [{country_code} Query] `{smart_query}`")
    
    try:
        response = requests.get(base_url, headers=get_headers(), timeout=5, verify=False)
        soup = BeautifulSoup(response.content, 'xml')
        for item in soup.find_all('item'):
            source = item.source.text if item.source else "Google News"
            raw_desc = item.description.text if item.description else ""
            snippet = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)

            results.append({
                'Title': item.title.text, 
                'Source': f"{source} ({country_code})", 
                'Date': parse_date(item.pubDate.text), 
                'Link': item.link.text, 
                'Keyword': keyword,
                'Snippet': snippet[:300], 
                'AI_Verified': False
            })
    except: pass
    return results

def perform_crawling(category, start_date, end_date, debug_mode, api_key):
    keywords = st.session_state.keywords.get(category, [])
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    progress_bar = st.progress(0); status_text = st.empty()
    if not keywords: st.warning("키워드가 없습니다."); return

    total_steps = len(keywords) * 4; step = 0
    raw_articles = []
    
    for kw in keywords:
        status_text.text(f"🔍 스마트 수집 중: {kw}")
        raw_articles.extend(crawl_bing_china(kw, debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        raw_articles.extend(crawl_google_news(kw, 'KR', 'ko', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        raw_articles.extend(crawl_google_news(kw, 'US', 'en', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        raw_articles.extend(crawl_google_news(kw, 'JP', 'ja', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
    
    df = pd.DataFrame(raw_articles)
    if not df.empty:
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        df = df.sort_values(by='Date', ascending=False)
        df = df.drop_duplicates(subset=['Title'])
        candidates = df.head(60).to_dict('records')
    else: candidates = []

    if candidates and api_key:
        status_text.text(f"🤖 AI가 {len(candidates)}개의 기사를 최종 검수 중...")
        final_data = filter_with_gemini(candidates, api_key)
        if len(final_data) == 0:
            status_text.error("모든 기사가 필터링되었습니다.")
    else:
        final_data = candidates[:50]

    progress_bar.empty(); status_text.empty()
    st.session_state.news_data[category] = final_data

# ==========================================
# 5. UI 구성
# ==========================================
with st.sidebar:
    st.header("📂 Categories")
    selected_category = st.radio("항목 선택:", CATEGORIES)
    st.divider()
    
    st.subheader("🤖 Gemini AI Filter")
    gemini_api_key = None
    if "GEMINI_API_KEY" in st.secrets:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔐 API Key 로드 완료 (Secrets)")
    else:
        gemini_api_key = st.text_input("Google API Key", type="password")
        if not gemini_api_key: st.info("🔑 키를 입력하면 AI가 작동합니다.")
        
    st.divider()
    st.info("💡 **스마트 필터 작동 중**\n검색어에 '반도체 문맥'이 자동으로 추가되며, TikTok 등 노이즈는 원천 차단됩니다.")
    st.markdown("<div class='sidebar-footer'>Made by LSH</div>", unsafe_allow_html=True)

st.title(f"{selected_category} News")
st.divider()

col_set, col_kw = st.columns([1, 2])
with col_set:
    st.markdown("##### 📅 기간 설정")
    period = st.radio("기간", ["1개월", "3개월", "6개월", "기간지정"], horizontal=True, label_visibility="collapsed")
    today = datetime.now().date(); start_date, end_date = today, today
    if period == "1개월": start_date = today - timedelta(days=30)
    elif period == "3개월": start_date = today - timedelta(days=90)
    elif period == "6개월": start_date = today - timedelta(days=180)
    elif period == "기간지정":
        dr = st.date_input("날짜", (today - timedelta(days=7), today))
        if len(dr) == 2: start_date, end_date = dr
        else: start_date = end_date = dr[0]

with col_kw:
    st.markdown("##### 🔑 키워드 관리 및 실행")
    c1, c2, c3 = st.columns([3, 1, 1.5])
    with c1: new_kw = st.text_input("입력 (예: TOK)", key="new_kw", label_visibility="collapsed")
    with c2: add_clicked = st.button("추가", use_container_width=True)
    with c3: update_clicked = st.button("🔄 뉴스 수집", type="primary", use_container_width=True)

    if add_clicked and new_kw:
        if new_kw not in st.session_state.keywords.get(selected_category, []):
            st.session_state.keywords[selected_category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
    
    kws = st.session_state.keywords.get(selected_category, [])
    if kws:
        cols = st.columns(5)
        for i, kw in enumerate(kws):
            if cols[i%5].button(f"❌ {kw}", key=f"d_{kw}"):
                st.session_state.keywords[selected_category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

if update_clicked:
    perform_crawling(selected_category, start_date, end_date, False, gemini_api_key)
    st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()

st.divider()
if st.session_state.last_update: st.caption(f"Last Updated: {st.session_state.last_update}")

data = st.session_state.news_data.get(selected_category, [])
if data:
    for row in data:
        with st.container():
            ai_badge = "<span class='ai-tag'>✨ VALIDATED</span>" if row.get('AI_Verified') else ""
            st.markdown(f"**[{row['Title']}]({row['Link']})** {ai_badge}", unsafe_allow_html=True)
            st.markdown(f"<div class='snippet-text'>{row.get('Snippet', '')}</div>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#888; font-size:0.8em'>{row['Source']} | {row['Date'].strftime('%Y-%m-%d')} | {row['Keyword']}</span>", unsafe_allow_html=True)
            st.divider()
else:
    if st.session_state.last_update: st.warning("조건에 맞는 기사가 없습니다.")
    else: st.info("상단의 '뉴스 수집' 버튼을 눌러주세요.")
