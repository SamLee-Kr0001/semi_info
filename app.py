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
import html  # HTML 특수문자 깨짐 방지용

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 CSS (디자인 핵심)
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# CSS 주입
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }
        
        /* 1. 사이드바 라디오 버튼 -> "메뉴 버튼" 스타일로 변신 */
        [data-testid="stSidebar"] {
            background-color: #F8FAFC;
            border-right: 1px solid #E2E8F0;
        }
        /* 라디오 버튼의 동그라미 숨기기 */
        div.row-widget.stRadio > div[role="radiogroup"] > label > div:first-child {
            display: none;
        }
        /* 버튼 모양 만들기 */
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            background-color: transparent;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 4px;
            border: 1px solid transparent;
            transition: all 0.2s ease;
            cursor: pointer;
            width: 100%;
            display: flex; /* 텍스트 정렬 */
            align-items: center;
        }
        /* 마우스 올렸을 때 */
        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
            background-color: #FFFFFF;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            color: #2563EB;
        }
        /* 선택되었을 때 (Active) */
        div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
            background-color: #EFF6FF; /* 연한 파란색 */
            border: 1px solid #BFDBFE;
            color: #1D4ED8; /* 진한 파란색 텍스트 */
            font-weight: 700;
        }
        
        /* 2. 뉴스 카드 스타일 (HTML 오류 방지 구조) */
        .news-card-container {
            background-color: #FFFFFF !important; /* 다크모드 무시하고 흰 배경 */
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 0px; /* Grid 간격 조절 */
            height: 100%;
            min-height: 220px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .news-card-container:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.08);
            border-color: #6366F1;
        }
        
        /* 텍스트 스타일 강제 지정 (다크모드 호환성) */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .card-source {
            font-size: 0.75rem;
            font-weight: 600;
            color: #64748B !important;
            background-color: #F1F5F9;
            padding: 4px 8px;
            border-radius: 6px;
        }
        .card-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1E293B !important;
            text-decoration: none;
            line-height: 1.4;
            margin-bottom: 8px;
            display: block;
        }
        .card-title:hover {
            color: #4F46E5 !important;
            text-decoration: underline;
        }
        .card-snippet {
            font-size: 0.9rem;
            color: #475569 !important;
            line-height: 1.5;
            margin-bottom: 16px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
        }
        .card-footer {
            border-top: 1px solid #F1F5F9;
            padding-top: 12px;
            font-size: 0.8rem;
            color: #94A3B8 !important;
            display: flex;
            justify-content: space-between;
        }

        /* 3. 컨트롤 패널 */
        .control-panel {
            background-color: white;
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            margin-bottom: 25px;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 데이터 관리 및 유틸리티
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
# 2. 로직: 크롤링 & AI (안정성 강화)
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
            # 특수문자 제거하여 프롬프트 오류 방지
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
    
    with st.spinner(f"🌐 [{category}] 글로벌 뉴스 수집 및 AI 분석 중..."):
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
# 3. 사이드바 UI (메뉴 스타일 라디오 버튼)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2331/2331966.png", width=40)
    st.markdown("<h3 style='margin-top:0'>Semi-Insight Hub</h3>", unsafe_allow_html=True)
    st.caption("Global Market Intelligence")
    st.markdown("---")
    
    st.markdown("#### 📂 Target Domain")
    # 라디오 버튼이지만 CSS로 버튼 메뉴처럼 보이게 처리됨
    selected_category = st.radio(
        "카테고리 선택", 
        CATEGORIES, 
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    with st.expander("🔐 API Settings", expanded=False):
        api_key = st.text_input("Gemini API Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("API Key Loaded")
    
    st.markdown("<div style='font-size:0.8em; color:#888; margin-top:20px'>Developed by LSH</div>", unsafe_allow_html=True)

# ==========================================
# 4. 메인 UI (컨트롤 패널 & 카드 그리드)
# ==========================================

# 상단 헤더
c_h1, c_h2 = st.columns([3, 1])
with c_h1: st.title(selected_category)
with c_h2: 
    if st.session_state.last_update:
        st.caption(f"Last Update: {st.session_state.last_update}")

# 컨트롤 패널
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([2, 3, 1, 1.5])

with c1:
    period = st.selectbox("기간 설정", ["1 Month", "3 Months", "Custom"], label_visibility="collapsed")
    today = datetime.now().date()
    if period == "1 Month": s_date, e_date = today - timedelta(days=30), today
    elif period == "3 Months": s_date, e_date = today - timedelta(days=90), today
    else: s_date, e_date = today - timedelta(days=7), today

with c2:
    new_kw = st.text_input("키워드", placeholder="Add keyword...", label_visibility="collapsed")
with c3:
    if st.button("추가", use_container_width=True):
        if new_kw and new_kw not in st.session_state.keywords[selected_category]:
            st.session_state.keywords[selected_category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
with c4:
    if st.button("🚀 실행", type="primary", use_container_width=True):
        perform_crawling(selected_category, s_date, e_date, api_key)
        st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.rerun()

# 키워드 칩 표시
kws = st.session_state.keywords.get(selected_category, [])
if kws:
    st.write("Watching:")
    # 키워드 삭제 버튼 그리드
    cols = st.columns(8)
    for i, kw in enumerate(kws):
        if cols[i%8].button(f"{kw} ✖", key=f"d_{kw}"):
            st.session_state.keywords[selected_category].remove(kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 결과 표시 (HTML 오류 수정 적용)
# ==========================================
data = st.session_state.news_data.get(selected_category, [])

if data:
    # 요약 지표
    m1, m2 = st.columns(2)
    m1.metric("Collected Articles", len(data))
    ai_count = sum(1 for d in data if d.get('AI_Verified'))
    m2.metric("AI Verified", ai_count)
    st.divider()

    # Grid Layout Loop
    # HTML 문자열 생성 시 불필요한 공백을 없애고 한 줄로 만드는 것이 핵심
    for i in range(0, len(data), 2):
        row_items = data[i : i+2]
        cols = st.columns(2)
        
        for idx, item in enumerate(row_items):
            with cols[idx]:
                # 1. HTML Escape (내용에 따옴표나 괄호가 있으면 깨짐 방지)
                safe_title = html.escape(item['Title'])
                safe_snip = html.escape(item.get('Snippet', ''))
                safe_src = html.escape(item['Source'])
                link = item['Link']
                date_str = item['Date'].strftime('%Y-%m-%d')
                
                # 2. 뱃지 HTML
                ai_badge = '<span style="background:#EEF2FF; color:#4F46E5; padding:2px 6px; border-radius:4px; font-size:0.7em; font-weight:bold; border:1px solid #C7D2FE; margin-left:5px;">✨ AI Pick</span>' if item.get('AI_Verified') else ''
                
                # 3. HTML 조립 (f-string 들여쓰기 문제 해결을 위해 붙여씀)
                html_code = f"""
<div class="news-card-container">
    <div>
        <div class="card-header">
            <span class="card-source">{safe_src}</span>
            {ai_badge}
        </div>
        <a href="{link}" target="_blank" class="card-title">{safe_title}</a>
        <div class="card-snippet">{safe_snip}</div>
    </div>
    <div class="card-footer">
        <span>{date_str}</span>
        <span>#{item['Keyword']}</span>
    </div>
</div>
"""
                # 4. 렌더링 (unsafe_allow_html 필수)
                st.markdown(html_code, unsafe_allow_html=True)

else:
    st.info("데이터가 없습니다. 상단의 '🚀 실행' 버튼을 눌러주세요.")
