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

# Selenium (Bing 검색용)
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
    </style>
""", unsafe_allow_html=True)

# 카테고리 설정
CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 키워드 관리 (JSON 저장)
# ==========================================
KEYWORD_FILE = 'keywords.json'

def load_keywords():
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {cat: [] for cat in CATEGORIES}

def save_keywords(keywords_dict):
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(keywords_dict, f, ensure_ascii=False, indent=4)
    except:
        pass

if 'keywords' not in st.session_state:
    st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# ==========================================
# 2. 크롤링 엔진
# ==========================================
def get_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return {'User-Agent': random.choice(user_agents)}

def parse_date(date_str):
    """날짜 파싱 (상대시간 처리 포함)"""
    try:
        now = datetime.now()
        date_str = str(date_str).strip()
        
        if '시간' in date_str or 'hour' in date_str:
            return now
        if '분' in date_str or 'min' in date_str:
            return now
        if '일 전' in date_str or 'day' in date_str:
            days_match = re.search(r'\d+', date_str)
            if days_match:
                days = int(days_match.group())
                return now - timedelta(days=days)
            
        return pd.to_datetime(date_str).to_pydatetime()
    except:
        return datetime.now()

def crawl_bing_china(keyword, debug_mode=False):
    """Bing News China를 이용한 Ijiwei 기사 수집"""
    results = []
    search_query = f"site:ijiwei.com {keyword}"
    base_url = f"https://cn.bing.com/news/search?q={quote(search_query)}"
    
    if debug_mode:
        st.write(f"🇨🇳 **[Bing China]** 검색: `{search_query}`")

    # Selenium 설정
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
        
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "news-card"))
            )
        except:
            time.sleep(1)

        if debug_mode:
            st.image(driver.get_screenshot_as_png(), caption="Bing CN 화면", width=300)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        articles = soup.find_all('div', class_='news-card')
        
        for item in articles:
            try:
                title_tag = item.find('a', class_='title')
                if not title_tag: continue
                
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                
                source_tag = item.find('div', class_='source')
                date_str = str(datetime.now().date())
                source_name = "Ijiwei (via Bing)"
                
                if source_tag:
                    spans = source_tag.find_all('span')
                    if len(spans) >= 2:
                        date_str = spans[-1].get_text(strip=True)
                    elif len(spans) == 1:
                         date_str = spans[0].get_text(strip=True)

                results.append({
                    'Title': title,
                    'Source': source_name,
                    'Date': parse_date(date_str),
                    'Link': link,
                    'Keyword': keyword
                })
            except Exception:
                continue
                
    except Exception as e:
        if debug_mode:
            st.error(f"[Bing CN Error] {e}")
    finally:
        if driver:
            driver.quit()
            
    return results

def crawl_google_news(keyword, country_code, language, debug_mode=False):
    """Google News 크롤링"""
    results = []
    base_url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    if debug_mode:
        st.write(f"📡 **[{country_code}]** 검색: `{base_url}`")

    try:
        response = requests.get(base_url, headers=get_headers(), timeout=5, verify=False)
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date = item.pubDate.text
            source = item.source.text if item.source else "Google News"
            
            results.append({
                'Title': title,
                'Source': f"{source} ({country_code})",
                'Date': parse_date(pub_date),
                'Link': link,
                'Keyword': keyword
            })
    except Exception as e:
        if debug_mode:
            st.error(f"[{country_code} Error] {e}")
            
    return results

def perform_crawling(category, start_date, end_date, debug_mode):
    keywords = st.session_state.keywords[category]
    collected_data = []
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    if not keywords:
        st.warning("등록된 키워드가 없습니다.")
        return

    total_steps = len(keywords) * 4
    step = 0
    
    for kw in keywords:
        # 1. 중국 (Bing News)
        status_text.text(f"🇨🇳 검색 중... [Ijiwei] {kw}")
        collected_data.extend(crawl_bing_china(kw, debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
        # 2. 한국 (Google)
        status_text.text(f"🇰🇷 검색 중... {kw}")
        collected_data.extend(crawl_google_news(kw, 'KR', 'ko', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
        # 3. 미국 (Google)
        status_text.text(f"🇺🇸 검색 중... {kw}")
        collected_data.extend(crawl_google_news(kw, 'US', 'en', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
        # 4. 일본 (Google)
        status_text.text(f"🇯🇵 검색 중... {kw}")
        collected_data.extend(crawl_google_news(kw, 'JP', 'ja', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
    progress_bar.empty()
    status_text.empty()
    
    # 데이터 정리
    df = pd.DataFrame(collected_data)
    if not df.empty:
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        df = df.sort_values(by='Date', ascending=False)
        df = df.head(50)
        st.session_state.news_data[category] = df.to_dict('records')
    else:
        st.session_state.news_data[category] = []
        if debug_mode:
            st.warning("조건에 맞는 기사가 없습니다.")

# ==========================================
# 3. UI 구성
# ==========================================
with st.sidebar:
    st.header("📂 Categories")
    selected_category = st.radio("항목을 선택하세요:", CATEGORIES)
    st.divider()
    
    st.subheader("🛠️ Debug Tools")
    debug_mode = st.checkbox("🐞 디버깅 모드", value=False)
    st.divider()
    
    st.info("💡 **Tip:**\n중국 기사는 Bing News를 통해\n'Ijiwei.com'을 집중 검색합니다.")
    st.markdown("<div class='sidebar-footer'>Made by LSH</div>", unsafe_allow_html=True)

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title(f"{selected_category} News")
with col_btn:
    st.write("") 
    update_clicked = st.button("🔄 Update News", type="primary")

st.divider()

col_settings, col_keywords = st.columns([1, 1.5])
with col_settings:
    st.markdown("##### 📅 기간 설정")
    period_option = st.radio("기간 선택", ["1개월", "3개월", "6개월", "기간지정"], horizontal=True)
    today = datetime.now().date()
    start_date, end_date = today, today
    
    if period_option == "1개월": start_date = today - timedelta(days=30)
    elif period_option == "3개월": start_date = today - timedelta(days=90)
    elif period_option == "6개월": start_date = today - timedelta(days=180)
    elif period_option == "기간지정":
        dr = st.date_input("날짜 선택", (today - timedelta(days=7), today), max_value=today)
        if len(dr) == 2: start_date, end_date = dr
        else: start_date = end_date = dr[0]

with col_keywords:
    st.markdown("##### 🔑 키워드 관리")
    c1, c2 = st.columns([3, 1])
    new_kw = c1.text_input("키워드 입력", key="new_kw")
    if c2.button("추가", use_container_width=True) and new_kw:
        if new_kw not in st.session_state.keywords[selected_category]:
            st.session_state.keywords[selected_category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()

    kws = st.session_state.keywords[selected_category]
    if kws:
        st.write("등록된 키워드:")
        cols = st.columns(4)
        for i, kw in enumerate(kws):
            if cols[i%4].button(f"❌ {kw}", key=f"d_{kw}"):
                st.session_state.keywords[selected_category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

# 실행 및 출력
if update_clicked:
    st.info(f"뉴스 수집 중... (중국: Bing / 그 외: Google)")
    perform_crawling(selected_category, start_date, end_date, debug_mode)
    st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()

st.divider()
if st.session_state.last_update:
    st.caption(f"Last Updated: {st.session_state.last_update}")

data = st.session_state.news_data.get(selected_category, [])
if data:
    for row in data:
        with st.container():
            st.markdown(f"**[{row['Title']}]({row['Link']})**")
            st.markdown(f"<span style='color:#666; font-size:0.8em'>{row['Source']} | {row['Date'].strftime('%Y-%m-%d')} | {row['Keyword']}</span>", unsafe_allow_html=True)
            st.divider()
else:
    if st.session_state.last_update:
        st.warning("기사가 없습니다.")
    else:
        st.info("Update 버튼을 눌러주세요.")
