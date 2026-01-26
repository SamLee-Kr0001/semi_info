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
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
        html, body, [class*="css"] { font-size: 0.95rem; }
        h1 { font-size: 1.8rem !important; margin-bottom: 0.5rem !important; }
        .sidebar-footer { position: fixed; bottom: 10px; left: 20px; font-size: 8px; color: #888888; z-index: 999; }
        a { text-decoration: none; color: #0366d6; }
        a:hover { text-decoration: underline; }
        .ai-tag {
            background-color: #e6f3ff;
            color: #0066cc;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: bold;
            border: 1px solid #cce5ff;
        }
        .snippet-text {
            color: #555;
            font-size: 0.85em;
            margin-top: 2px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
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
# 2. AI 필터링 엔진 (Google Gemini)
# ==========================================
def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 제목 + 요약문을 합쳐서 AI에게 전달
        content_block = []
        for i, item in enumerate(articles):
            snippet = item.get('Snippet', '')
            content_block.append(f"Item {i+1}:\n- Title: {item['Title']}\n- Snippet: {snippet}\n- Keyword: {item['Keyword']}")
            
        full_text = "\n\n".join(content_block)
        
        prompt = f"""
        Act as a strict Senior Semiconductor Analyst.
        Filter out noise. Keep ONLY articles strictly related to B2B Semiconductor Manufacturing/Materials.

        *** RULES ***
        1. REJECT 'TikTok', 'Social Media', 'Music', 'App' (Even if keyword is TOK).
        2. REJECT 'Precursor' if it means 'forerunner' (Must be chemical).
        3. REJECT general stock buzz unless it discusses fab/tech.
        4. KEEP new materials, yield, lithography, fab equipment.

        *** DATA ***
        {full_text}

        *** OUTPUT ***
        Return ONLY numbers of valid items (e.g., 1, 3, 5). If none, return 'None'.
        """
        
        response = model.generate_content(prompt)
        # 응답에서 숫자만 추출
        valid_indices = [int(num) - 1 for num in re.findall(r'\d+', response.text)]
        
        filtered = []
        for idx in valid_indices:
            if 0 <= idx < len(articles):
                articles[idx]['AI_Verified'] = True
                filtered.append(articles[idx])
        return filtered
    except Exception as e:
        # AI 에러나면 그냥 원본 반환 (멈추지 않게)
        print(f"AI Error: {e}")
        return articles

# ==========================================
# 3. 크롤링 엔진 (Snippet 수집)
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
    search_query = f"site:ijiwei.com {keyword}"
    base_url = f"https://cn.bing.com/news/search?q={quote(search_query)}"
    
    if debug_mode: st.write(f"🇨🇳 [Bing] `{search_query}`")

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
                results.append({'Title': title, 'Source': "Ijiwei (via Bing)", 'Date': parse_date(date_str), 'Link': link, 'Keyword': keyword, 'Snippet': snippet, 'AI_Verified': False})
            except: continue
    except: pass
    finally:
        if driver: driver.quit()
    return results

def crawl_google_news(keyword, country_code, language, debug_mode=False):
    results = []
    base_url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    if debug_mode: st.write(f"📡 [{country_code}] `{keyword}`")
    
    try:
        response = requests.get(base_url, headers=get_headers(), timeout=5, verify=False)
        soup = BeautifulSoup(response.content, 'xml')
        for item in soup.find_all('item'):
            source = item.source.text if item.source else "Google News"
            
            # HTML 태그 제거하고 Snippet 추출
            raw_desc = item.description.text if item.description else ""
            snippet = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)

            results.append({
                'Title': item.title.text, 
                'Source': f"{source} ({country_code})", 
                'Date': parse_date(item.pubDate.text), 
                'Link': item.link.text, 
                'Keyword': keyword,
                'Snippet': snippet[:200], 
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
        status_text.text(f"🔍 수집 중: {kw}")
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
        # AI 검증용 60개 추출
        candidates = df.head(60).to_dict('records')
    else: candidates = []

    if candidates and api_key:
        status_text.text("🤖 AI가 요약문을 읽고 정밀 검증 중...")
        final_data = filter_with_gemini(candidates, api_key)
    else:
        final_data = candidates[:50]

    progress_bar.empty(); status_text.empty()
    st.session_state.news_data[category] = final_data

# ==========================================
# 4. UI 구성
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
    st.subheader("🛠️ Debug")
    debug_mode = st.checkbox("디버깅 모드", value=False)
    st.markdown("<div class='sidebar-footer'>Made by LSH</div>", unsafe_allow_html=True)

col_title, col_btn = st.columns([4, 1])
with col_title: st.title(f"{selected_category} News")
with col_btn:
    st.write(""); update_clicked = st.button("🔄 Update News", type="primary")

st.divider()

col_set, col_kw = st.columns([1, 1.5])
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
    st.markdown("##### 🔑 키워드 관리")
    c1, c2 = st.columns([3, 1])
    new_kw = c1.text_input("입력 (예: TOK)", key="new_kw", label_visibility="collapsed")
    if c2.button("추가", use_container_width=True) and new_kw:
        if new_kw not in st.session_state.keywords.get(selected_category, []):
            st.session_state.keywords[selected_category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
    
    kws = st.session_state.keywords.get(selected_category, [])
    if kws:
        cols = st.columns(4)
        for i, kw in enumerate(kws):
            if cols[i%4].button(f"❌ {kw}", key=f"d_{kw}"):
                st.session_state.keywords[selected_category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

if update_clicked:
    perform_crawling(selected_category, start_date, end_date, debug_mode, gemini_api_key)
    st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()

st.divider()
if st.session_state.last_update: st.caption(f"Last Updated: {st.session_state.last_update}")

data = st.session_state.news_data.get(selected_category, [])
if data:
    for row in data:
        with st.container():
            ai_badge = "<span class='ai-tag'>✨ AI Verified</span>" if row.get('AI_Verified') else ""
            st.markdown(f"**[{row['Title']}]({row['Link']})** {ai_badge}", unsafe_allow_html=True)
            st.markdown(f"<div class='snippet-text'>{row.get('Snippet', '')[:150]}...</div>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#888; font-size:0.8em'>{row['Source']} | {row['Date'].strftime('%Y-%m-%d')} | {row['Keyword']}</span>", unsafe_allow_html=True)
            st.divider()
else:
    if st.session_state.last_update: st.warning("기사가 없습니다.")
    else: st.info("Update 버튼을 눌러주세요.")
