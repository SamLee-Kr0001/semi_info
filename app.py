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
import html  # HTML 이스케이프용

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 Modern CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# 세련된 UI를 위한 Custom CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }
        
        /* 메인 배경색 */
        .stApp {
            background-color: #F8FAFC;
        }

        /* ----------------------------------------------------
           1. 사이드바 라디오 버튼 커스텀 (세련된 메뉴 스타일)
           ---------------------------------------------------- */
        /* 라디오 버튼 선택 항목 박스 스타일 */
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            background-color: transparent;
            border: 1px solid transparent;
            padding: 10px 12px;
            border-radius: 8px;
            transition: all 0.2s ease;
            margin-bottom: 4px;
        }
        
        /* 마우스 호버 시 효과 */
        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
            background-color: #F1F5F9;
            color: #3B82F6;
        }

        /* 선택된 항목 강조 (Streamlit 기본 동작과 CSS 조합) */
        div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
            background-color: #EFF6FF; /* 연한 파란색 배경 */
            border: 1px solid #BFDBFE;
            color: #1D4ED8;
            font-weight: 600;
        }

        /* ----------------------------------------------------
           2. 뉴스 카드 스타일 (오류 수정 및 디자인 강화)
           ---------------------------------------------------- */
        .news-card {
            background-color: #FFFFFF !important; /* 다크모드 방지 강제 흰색 */
            border-radius: 12px;
            padding: 20px;
            height: 100%;
            min-height: 200px; /* 높이 통일감 */
            border: 1px solid #E2E8F0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .news-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border-color: #6366f1;
        }

        /* 텍스트 색상 강제 지정 (다크모드에서도 잘 보이게) */
        .news-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .news-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #0F172A !important; 
            text-decoration: none;
            line-height: 1.4;
            display: block;
            margin-bottom: 8px;
        }
        .news-title:hover {
            color: #4F46E5 !important;
            text-decoration: underline;
        }
        
        .news-snippet {
            font-size: 0.9rem;
            color: #475569 !important;
            line-height: 1.5;
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3; /* 3줄 이상 말줄임 */
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .news-footer {
            border-top: 1px solid #F1F5F9;
            padding-top: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: #94A3B8 !important;
        }

        /* 뱃지 스타일 */
        .badge-src { 
            background-color: #F1F5F9; 
            color: #475569; 
            padding: 4px 8px; 
            border-radius: 6px; 
            font-size: 0.75rem; 
            font-weight: 600;
        }
        .badge-ai { 
            background-color: #EEF2FF; 
            color: #4F46E5; 
            padding: 4px 8px; 
            border-radius: 6px; 
            font-size: 0.75rem; 
            font-weight: 700; 
            border: 1px solid #C7D2FE;
        }
        
        /* 컨트롤 패널 스타일 */
        .control-panel {
            background-color: white;
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 데이터 관리 (기존 로직)
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
# 2. 크롤링 엔진 & AI 필터
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
            # 텍스트 전처리 (오류 방지)
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
    
    with st.spinner(f"🌐 {category} 관련 뉴스 수집 중..."):
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
# 3. 사이드바 UI (Refined Radio Style)
# ==========================================
with st.sidebar:
    st.markdown("### 💠 Semi-Insight Hub")
    st.markdown("Global Market Intelligence")
    st.divider()
    
    st.markdown("#### 📂 Target Domain")
    # 라디오 버튼을 사용하되, CSS로 스타일링하여 버튼처럼 보이게 함
    selected_category = st.radio(
        "카테고리를 선택하세요", 
        CATEGORIES, 
        label_visibility="collapsed"
    )
    
    st.divider()
    with st.expander("🔐 API Settings", expanded=False):
        api_key = st.text_input("Gemini API Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("API Key Loaded")
    
    st.caption("Copyright © LSH")

# ==========================================
# 4. 메인 대시보드
# ==========================================

# 헤더
c_h1, c_h2 = st.columns([3, 1])
with c_h1: st.title(selected_category)
with c_h2: 
    if st.session_state.last_update:
        st.caption(f"Last update: {st.session_state.last_update}")

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
    new_kw = st.text_input("키워드 추가", placeholder="예: HBM, EUV", label_visibility="collapsed")
with c3:
    if st.button("추가", use_container_width=True):
        if new_kw and new_kw not in st.session_state.keywords[selected_category]:
            st.session_state.keywords[selected_category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
with c4:
    if st.button("🚀 뉴스 수집 시작", type="primary", use_container_width=True):
        perform_crawling(selected_category, s_date, e_date, api_key)
        st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.rerun()

# 키워드 칩
curr_kws = st.session_state.keywords.get(selected_category, [])
if curr_kws:
    st.write("Watching Keywords:")
    cols = st.columns(8)
    for i, kw in enumerate(curr_kws):
        if cols[i%8].button(f"{kw} ✖", key=f"del_{kw}"):
            st.session_state.keywords[selected_category].remove(kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# 뉴스 카드 그리드
data = st.session_state.news_data.get(selected_category, [])
if data:
    m1, m2 = st.columns(2)
    m1.metric("Collected", len(data))
    m2.metric("AI Verified", sum(1 for d in data if d.get('AI_Verified')))
    st.markdown("<br>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # [수정] HTML 렌더링 오류 해결을 위한 명확한 구조
    # ----------------------------------------------------
    for i in range(0, len(data), 2):
        row_items = data[i : i+2]
        cols = st.columns(2)
        
        for idx, item in enumerate(row_items):
            with cols[idx]:
                # 1. 특수문자 이스케이프 (필수)
                title = html.escape(item['Title'])
                snippet = html.escape(item.get('Snippet', ''))
                source = html.escape(item['Source'])
                link = item['Link']
                date = item['Date'].strftime('%Y-%m-%d')
                
                # 2. AI 뱃지 생성
                badge_html = f'<span class="badge-ai">✨ AI Pick</span>' if item.get('AI_Verified') else ''
                
                # 3. HTML 조립 (들여쓰기 및 태그 닫힘 주의)
                # 다크모드에서도 보이도록 글자색 스타일(!important)이 적용된 클래스 사용
                card_html = f"""
                <div class="news-card">
                    <div>
                        <div class="news-header">
                            <span class="badge-src">{source}</span>
                            {badge_html}
                        </div>
                        <a href="{link}" target="_blank" class="news-title">{title}</a>
                        <p class="news-snippet">{snippet}</p>
                    </div>
                    <div class="news-footer">
                        <span>🗓 {date}</span>
                        <span>#{item['Keyword']}</span>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
else:
    st.info("데이터가 없습니다. 상단의 '뉴스 수집 시작' 버튼을 눌러주세요.")
