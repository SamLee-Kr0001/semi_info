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
import html
import textwrap  # [핵심 수정] 들여쓰기 제거용 모듈

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# CSS: 카드 스타일 및 다크모드 대응
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }

        /* 뉴스 카드 컨테이너 */
        .news-card-box {
            background-color: #ffffff; 
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 0px;
            height: 100%; 
            min-height: 240px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s;
        }
        
        .news-card-box:hover {
            transform: translateY(-5px);
            border-color: #6366f1;
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }

        /* 텍스트 스타일 (다크모드에서도 강제로 잘 보이게 설정) */
        .card-title-link {
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            color: #111827 !important; /* 검정 계열 */
            text-decoration: none;
            margin-bottom: 10px;
            display: block;
            line-height: 1.4;
        }
        .card-title-link:hover {
            color: #4f46e5 !important; /* 인디고 색상 */
        }
        
        .card-snippet-text {
            font-size: 0.95rem !important;
            color: #4b5563 !important; /* 회색 */
            line-height: 1.6;
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .card-meta-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem !important;
            color: #9ca3af !important;
            border-top: 1px solid #f3f4f6;
            padding-top: 12px;
            margin-top: auto;
        }

        .badge-source {
            background-color: #f3f4f6;
            color: #374151;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.75rem;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 데이터 및 유틸리티
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
# 2. 크롤링 및 AI 로직
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
    
    with st.spinner(f"🌐 수집 중..."):
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
    st.divider()
    # 요청하신 대로 '라디오 버튼' 양식 유지하되 스타일 적용
    selected_category = st.radio("Target Domain", CATEGORIES)
    st.divider()
    with st.expander("API Key"):
        api_key = st.text_input("Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.caption("Auto-loaded")

# 메인 화면
c_head, c_date = st.columns([3, 1])
with c_head: st.title(selected_category)
with c_date: 
    if st.session_state.last_update: st.caption(f"Updated: {st.session_state.last_update}")

# 컨트롤 바
with st.container():
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

# 키워드 삭제 버튼
kws = st.session_state.keywords.get(selected_category, [])
if kws:
    cols = st.columns(8)
    for i, kw in enumerate(kws):
        if cols[i%8].button(f"{kw} ✖", key=f"d_{kw}"):
            st.session_state.keywords[selected_category].remove(kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
st.divider()

# ==========================================
# 4. 결과 디스플레이 (수정된 핵심 부분)
# ==========================================
data = st.session_state.news_data.get(selected_category, [])

if data:
    # 2열 그리드 루프
    for i in range(0, len(data), 2):
        row_items = data[i : i+2]
        cols = st.columns(2)
        
        for idx, item in enumerate(row_items):
            with cols[idx]:
                # 1. HTML 특수문자 이스케이프 (필수)
                safe_title = html.escape(item['Title'])
                safe_snippet = html.escape(item.get('Snippet', ''))
                safe_source = html.escape(item['Source'])
                link = item['Link']
                date_str = item['Date'].strftime('%Y-%m-%d')
                
                ai_badge = ""
                if item.get('AI_Verified'):
                    ai_badge = '<span style="color:#4F46E5; font-weight:bold; font-size:0.8em; margin-left:5px;">✨ AI Pick</span>'

                # [핵심 수정] textwrap.dedent를 사용하여 들여쓰기(공백)를 완벽하게 제거
                # 이것이 없으면 Streamlit은 들여쓰기된 HTML을 '코드 블록'으로 인식하여 텍스트로 출력해버림
                card_html = textwrap.dedent(f"""
                    <div class="news-card-box">
                        <div>
                            <div style="margin-bottom:8px; display:flex; justify-content:space-between;">
                                <span class="badge-source">{safe_source}</span>
                                {ai_badge}
                            </div>
                            <a href="{link}" target="_blank" class="card-title-link">{safe_title}</a>
                            <div class="card-snippet-text">{safe_snippet}</div>
                        </div>
                        <div class="card-meta-info">
                            <span>📅 {date_str}</span>
                            <span>#{item['Keyword']}</span>
                        </div>
                    </div>
                """)
                
                st.markdown(card_html, unsafe_allow_html=True)
else:
    st.info("데이터가 없습니다.")
