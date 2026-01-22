import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
import time
import random
import json
import os

# Selenium & Webdriver Manager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ==========================================
# 0. 설정 및 CSS 스타일링 (공백 최소화, 폰트 조정)
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semiconductor News Crawler")

# [CSS 수정] 상단 공백 최소화 및 폰트 사이즈 조절
st.markdown("""
    <style>
        /* 메인 컨테이너 상단 패딩 줄이기 */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        /* 전체 폰트 사이즈 약간 축소 (80%) */
        html, body, [class*="css"] {
            font-size: 0.95rem;
        }
        /* 제목(H1) 크기 조절 */
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.5rem !important;
        }
        /* 부제목(H3) 크기 조절 */
        h3 {
            font-size: 1.3rem !important;
            padding-top: 0.5rem !important;
        }
        /* Made by LSH 푸터 스타일 (사이드바 하단 고정) */
        .sidebar-footer {
            position: fixed;
            bottom: 10px;
            left: 20px;
            font-size: 10px;
            color: #888888;
            z-index: 999;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 키워드 저장/로드 함수 (JSON 파일 활용)
# ==========================================
KEYWORD_FILE = 'keywords.json'

def load_keywords():
    """파일에서 키워드를 불러오거나 기본값 반환"""
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass # 파일 읽기 실패 시 기본값 사용
    
    # 기본 키워드 (초기값)
    return {cat: [] for cat in CATEGORIES}

def save_keywords(keywords_dict):
    """키워드 변경 시 파일에 저장"""
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(keywords_dict, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"키워드 저장 실패: {e}")

# 세션 상태 초기화 (저장된 키워드 불러오기)
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
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
    ]
    return {'User-Agent': random.choice(user_agents)}

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str).to_pydatetime()
    except:
        return datetime.now()

def crawl_ijiwei(keyword, debug_mode=False):
    results = []
    base_url = f"https://www.ijiwei.com/search?keyword={quote(keyword)}"
    
    if debug_mode:
        st.markdown(f"**[Ijiwei]** 접속 시도: `{base_url}`")

    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(base_url)
        
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "search-item"))
            )
        except:
            time.sleep(2)
        
        if debug_mode:
            st.image(driver.get_screenshot_as_png(), caption=f"Ijiwei 화면 캡처: {keyword}", width=400)
            
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        articles = soup.find_all('div', class_='search-item')
        if not articles:
             articles = soup.find_all('li', class_='news-item')
        
        if debug_mode:
            st.write(f"👉 **[Ijiwei]** 발견된 태그 수: {len(articles)}개")

        for item in articles:
            try:
                title_tag = item.find('a', class_='title')
                date_tag = item.find('span', class_='date')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    if not link.startswith('http'):
                        link = "https://www.ijiwei.com" + link
                    date_str = date_tag.get_text(strip=True) if date_tag else str(datetime.now().date())
                    
                    results.append({
                        'Title': title,
                        'Source': 'Ijiwei (China)',
                        'Date': parse_date(date_str),
                        'Link': link,
                        'Keyword': keyword
                    })
            except Exception:
                continue
    except Exception as e:
        if debug_mode:
            st.error(f"[Ijiwei Error] {e}")
        print(f"Ijiwei Selenium error: {e}")
    finally:
        if driver:
            driver.quit()
    return results

def crawl_google_news(keyword, country_code, language, debug_mode=False):
    results = []
    base_url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    if debug_mode:
        st.write(f"📡 **[Google-{country_code}]** 요청 URL: `{base_url}`")

    try:
        response = requests.get(base_url, headers=get_headers(), timeout=10, verify=False)
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        if debug_mode:
            st.write(f"👉 발견된 기사 수: {len(items)}개")
        
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
            st.error(f"[Google Error] {e}")
    return results

def perform_crawling(category, start_date, end_date, debug_mode):
    keywords = st.session_state.keywords[category]
    collected_data = []
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    progress_bar = st.progress(0)
    
    if not keywords:
        st.warning("등록된 키워드가 없습니다.")
        return

    total_steps = len(keywords) * 4
    step = 0
    
    status_text = st.empty()

    for kw in keywords:
        status_text.text(f"🔍 '{kw}' 검색 중... (Ijiwei)")
        collected_data.extend(crawl_ijiwei(kw, debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
        status_text.text(f"🔍 '{kw}' 검색 중... (Korea)")
        collected_data.extend(crawl_google_news(kw, 'KR', 'ko', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
        status_text.text(f"🔍 '{kw}' 검색 중... (USA)")
        collected_data.extend(crawl_google_news(kw, 'US', 'en', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
        status_text.text(f"🔍 '{kw}' 검색 중... (Japan)")
        collected_data.extend(crawl_google_news(kw, 'JP', 'ja', debug_mode))
        step += 1; progress_bar.progress(step / total_steps)
        
    progress_bar.empty()
    status_text.empty()
    
    total_found = len(collected_data)
    
    df = pd.DataFrame(collected_data)
    if not df.empty:
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        filtered_count = len(df)
        
        if debug_mode:
            st.info(f"📊 **통계 리포트**\n\n- 전체 수집된 기사: {total_found}개\n- 날짜 필터({start_date}~{end_date}) 후: {filtered_count}개")

        df = df.sort_values(by='Date', ascending=False)
        df = df.head(50)
        st.session_state.news_data[category] = df.to_dict('records')
    else:
        if debug_mode:
            st.warning("수집된 데이터가 0건입니다.")
        st.session_state.news_data[category] = []

# ==========================================
# 3. UI 레이아웃
# ==========================================

with st.sidebar:
    st.header("📂 Categories")
    selected_category = st.radio("항목을 선택하세요:", CATEGORIES)
    
    st.divider()
    
    st.subheader("🛠️ Debug Tools")
    debug_mode = st.checkbox("🐞 디버깅 모드 활성화", value=False)
    
    st.divider()
    st.info("""
    💡 **검색 팁:**
    - `Samsung HBM` (AND)
    - `Samsung OR TSMC` (OR)
    """)
    
    # [수정] 하단 "Made by LSH" 문구 추가
    st.markdown("<div class='sidebar-footer'>Made by LSH</div>", unsafe_allow_html=True)

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title(f"{selected_category} News")

with col_btn:
    st.write("") 
    update_clicked = st.button("🔄 Update News", type="primary")

st.divider()

st.subheader("⚙️ Search Settings & Keywords")
col_settings, col_keywords = st.columns([1, 1.5])

with col_settings:
    st.markdown("##### 📅 수집 기간 설정")
    period_option = st.radio(
        "기간 선택",
        ["1개월", "3개월", "6개월", "기간지정"],
        horizontal=True
    )
    
    today = datetime.now().date()
    start_date = today
    end_date = today
    
    if period_option == "1개월":
        start_date = today - timedelta(days=30)
    elif period_option == "3개월":
        start_date = today - timedelta(days=90)
    elif period_option == "6개월":
        start_date = today - timedelta(days=180)
    elif period_option == "기간지정":
        date_range = st.date_input("시작일 - 종료일 선택", (today - timedelta(days=7), today), max_value=today)
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = date_range[0]; end_date = start_date

with col_keywords:
    st.markdown("##### 🔑 키워드 관리")
    c_input, c_add = st.columns([3, 1])
    with c_input:
        new_keyword = st.text_input("새 키워드 입력", key="new_kw_input")
    with c_add:
        if st.button("추가", use_container_width=True):
            if new_keyword and new_keyword not in st.session_state.keywords[selected_category]:
                st.session_state.keywords[selected_category].append(new_keyword)
                # [수정] 키워드 추가 시 파일 저장 호출
                save_keywords(st.session_state.keywords)
                st.rerun()

    current_keywords = st.session_state.keywords[selected_category]
    if current_keywords:
        st.write("등록된 키워드:")
        kw_cols = st.columns(4)
        for i, kw in enumerate(current_keywords):
            if kw_cols[i % 4].button(f"❌ {kw}", key=f"del_{kw}"):
                st.session_state.keywords[selected_category].remove(kw)
                # [수정] 키워드 삭제 시 파일 저장 호출
                save_keywords(st.session_state.keywords)
                st.rerun()
    else:
        st.caption("등록된 키워드가 없습니다.")

# ==========================================
# 4. 크롤링 실행
# ==========================================
if update_clicked:
    if debug_mode:
        st.warning("🐞 디버깅 모드가 켜져 있습니다. 상세 로그가 아래에 표시됩니다.")
        
    st.info(f"기간: {start_date} ~ {end_date} | 키워드 수: {len(current_keywords)}개")
    
    with st.spinner(f"'{selected_category}' 기사 수집 중..."):
        perform_crawling(selected_category, start_date, end_date, debug_mode)
        
    st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()

st.divider()

if st.session_state.last_update:
    st.caption(f"Last Updated: {st.session_state.last_update}")

st.subheader(f"📰 Latest Articles")
data = st.session_state.news_data.get(selected_category, [])

if data:
    df_display = pd.DataFrame(data)
    df_display['Date'] = df_display['Date'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M'))
    
    for index, row in df_display.iterrows():
        with st.container():
            st.markdown(f"**[{row['Title']}]({row['Link']})**")
            st.caption(f"{row['Source']} | {row['Date']} | Keyword: {row['Keyword']}")
            st.divider()
else:
    if st.session_state.last_update:
        st.warning("해당 기간에 수집된 기사가 없습니다.")
    else:
        st.info("Update News 버튼을 눌러주세요.")
