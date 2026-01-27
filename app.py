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

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 기본 CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# 복잡한 HTML 카드 CSS를 제거하고, 전체적인 폰트와 레이아웃만 다듬습니다.
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }

        /* 링크 스타일 */
        a {
            text-decoration: none;
            color: #2563EB !important;
            transition: color 0.2s;
        }
        a:hover {
            color: #1D4ED8 !important;
            text-decoration: underline;
        }

        /* 컨트롤 패널 스타일 */
        .control-panel-container {
            background-color: var(--secondary-background-color);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            margin-bottom: 25px;
        }
        
        /* 사이드바 라디오 버튼 스타일 */
         div.row-widget.stRadio > div[role="radiogroup"] > label > div:first-child {
            display: none;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 4px;
            transition: background-color 0.2s;
            cursor: pointer;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
             background-color: var(--secondary-background-color);
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
            background-color: var(--primary-color-light);
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 데이터 관리 및 유틸리티 (기존 유지)
# ==========================================
KEYWORD_FILE = 'keywords.json'

def load_keywords():
    data = {cat: [] for cat in CATEGORIES}
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in data: data[k] = v
        except: pass
    return data

def save_keywords(data):
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None

# ==========================================
# 2. 크롤링 및 AI 로직 (기존 유지)
# ==========================================
def make_smart_query(keyword, country_code):
    base_kw = keyword
    negatives = "-TikTok -틱톡 -douyin -dance -shorts -reels -viral -music -game -soccer"
    contexts = {
        'KR': "(반도체 OR 소자 OR 공정 OR 소재 OR 파운드리 OR 팹 OR 양산)",
        'CN': "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)",
        'HK': "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)",
        'TW': "(半導體 OR 晶片 OR 晶圓 OR 光阻 OR 蝕刻 OR 封裝)",
        'JP': "(半導体 OR シリコン OR ウェーハ OR レジスト)",
        'US': "(semiconductor OR chip OR fab OR foundry OR wafer OR lithography)"
    }
    context = contexts.get(country_code, contexts['US'])
    return f'{base_kw} AND {context} {negatives}'

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        content_text = ""
        for i, item in enumerate(articles[:40]):
            safe_snip = re.sub(r'[^\w\s]', '', item.get('Snippet', ''))[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {safe_snip}\n"
            
        prompt = f"""
        Role: Semiconductor B2B Analyst.
        Task: Identify valid industry news.
        Rules: Keep Fab, Tech, Materials, Equipment. Reject Consumer gadgets/Games/Stocks.
        Data: {content_text}
        Output: Return ONLY the IDs (e.g., 1, 3, 5) of valid articles.
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

def crawl_google_rss(keyword, country_code, language):
    results = []
    smart_query = make_smart_query(keyword, country_code)
    url = f"https://news.google.com/rss/search?q={quote(smart_query)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            for item in soup.find_all('item')[:5]:
                src = item.source.text if item.source else "Google"
                raw_d = item.description.text if item.description else ""
                snip = BeautifulSoup(raw_d, "html.parser").get_text(strip=True)[:200]
                pub_date = item.pubDate.text if item.pubDate else str(datetime.now())
                try: dt_obj = pd.to_datetime(pub_date).to_pydatetime()
                except: dt_obj = datetime.now()

                results.append({
                    'Title': item.title.text, 'Source': src, 'Date': dt_obj,
                    'Link': item.link.text, 'Keyword': keyword, 'Snippet': snip,
                    'AI_Verified': False
                })
    except: pass
    return results

def perform_crawling(category, start_date, end_date, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    with st.spinner(f"🌐 뉴스 수집 중... ({category})"):
        all_news = []
        for kw in kws:
            for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW')]:
                all_news.extend(crawl_google_rss(kw, cc, lang))
        
        df = pd.DataFrame(all_news)
        if not df.empty:
            df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
            df = df.drop_duplicates(subset=['Title']).sort_values('Date', ascending=False)
            final_list = df.head(60).to_dict('records')
            if api_key and final_list:
                final_list = filter_with_gemini(final_list, api_key)
            st.session_state.news_data[category] = final_list
        else:
             st.session_state.news_data[category] = []

# ==========================================
# 3. 사이드바 & 컨트롤 패널
# ==========================================
with st.sidebar:
    st.header("Semi-Insight")
    st.caption("Global Market Intelligence")
    st.divider()
    selected_category = st.radio("Target Domain", CATEGORIES)
    st.divider()
    with st.expander("API Key"):
        api_key = st.text_input("Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.caption("Auto-loaded from secrets")

# 메인 헤더
c_head, c_date = st.columns([3, 1])
with c_head: st.title(selected_category)
with c_date: 
    if st.session_state.last_update: st.caption(f"Updated: {st.session_state.last_update}")

# 컨트롤 패널 (네이티브 컨테이너 활용)
with st.container():
    # CSS 클래스 적용을 위한 트릭 (st.markdown으로 감싸기)
    st.markdown('<div class="control-panel-container">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2, 3, 1, 1.5])
    with c1:
        period = st.selectbox("기간", ["1 Month", "3 Months", "Custom"], label_visibility="collapsed")
        today = datetime.now().date()
        if period == "1 Month": s_date, e_date = today - timedelta(days=30), today
        elif period == "3 Months": s_date, e_date = today - timedelta(days=90), today
        else: s_date, e_date = today - timedelta(days=7), today
    with c2:
        new_kw = st.text_input("키워드", placeholder="예: HBM", label_visibility="collapsed")
    with c3:
        if st.button("추가", use_container_width=True):
            if new_kw and new_kw not in st.session_state.keywords[selected_category]:
                st.session_state.keywords[selected_category].append(new_kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
    with c4:
        if st.button("🚀 실행", type="primary", use_container_width=True):
            perform_crawling(selected_category, s_date, e_date, api_key)
            st.session_state.last_update = datetime.now().strftime("%H:%M")
            st.rerun()

    # 키워드 칩
    kws = st.session_state.keywords.get(selected_category, [])
    if kws:
        st.write("") # 간격 띄우기
        cols = st.columns(8)
        for i, kw in enumerate(kws):
            if cols[i%8].button(f"{kw} ✖", key=f"d_{kw}", help="삭제"):
                st.session_state.keywords[selected_category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True) # 컨테이너 닫기

# ==========================================
# 4. 결과 디스플레이 (완전히 새로운 방식)
# ==========================================
data = st.session_state.news_data.get(selected_category, [])

if data:
    st.divider()
    
    # 2열 그리드 루프 (안정적인 방식)
    for i in range(0, len(data), 2):
        row_items = data[i : i+2]
        cols = st.columns(2) # 2개의 컬럼 생성
        
        for idx, item in enumerate(row_items):
            with cols[idx]:
                # [핵심 변경] HTML 문자열 대신 Streamlit 네이티브 컨테이너 사용
                # border=True 옵션으로 깔끔한 카드 모양 구현 (테마 자동 대응)
                with st.container(border=True):
                    # 1. 상단 정보 (출처 및 날짜)
                    meta_c1, meta_c2 = st.columns([3, 2])
                    with meta_c1:
                        st.caption(f"📰 {item['Source']}")
                    with meta_c2:
                        st.caption(f"🗓️ {item['Date'].strftime('%Y-%m-%d')}")
                    
                    # 2. 제목 (링크 포함된 마크다운 헤더)
                    st.markdown(f"#### [{item['Title']}]({item['Link']})")
                    
                    # 3. 본문 요약
                    if item.get('Snippet'):
                        st.write(item['Snippet'])
                        
                    st.divider()
                    
                    # 4. 하단 정보 (키워드 및 AI 뱃지)
                    foot_c1, foot_c2 = st.columns([3, 1])
                    with foot_c1:
                        st.caption(f"🏷️ #{item['Keyword']}")
                    with foot_c2:
                        if item.get('AI_Verified'):
                            # 네이티브 방식으로 AI 뱃지 표시
                            st.markdown(":sparkles: **AI Pick**")

else:
    st.info("표시할 데이터가 없습니다. 상단의 '🚀 실행' 버튼을 눌러주세요.")
