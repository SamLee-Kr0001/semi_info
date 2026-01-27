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

# [NEW] 번역 라이브러리 추가
from deep_translator import GoogleTranslator

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 Modern CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# 디자인 CSS: Light Gray 테마, 깔끔한 카드, 간격 조정
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            background-color: #F8FAFC;
            color: #334155;
        }
        
        /* 메인 영역 배경 */
        .stApp {
            background-color: #F8FAFC;
        }

        /* 1. 컨트롤 패널 (상단 박스) */
        .control-box {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }

        /* 2. 네이티브 컨테이너(카드) 스타일 리파인 */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        
        /* 3. 사이드바 라디오 버튼 -> 메뉴 스타일 */
        div.row-widget.stRadio > div[role="radiogroup"] > label > div:first-child {
            display: none;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 4px;
            border: 1px solid transparent;
            transition: all 0.2s;
            cursor: pointer;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
            background-color: #F1F5F9;
            color: #2563EB;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
            background-color: #EFF6FF;
            border: 1px solid #BFDBFE;
            color: #1D4ED8;
            font-weight: 600;
        }

        /* 4. 키워드 태그 (간격 좁게) */
        button[kind="secondary"] {
            height: 32px;
            font-size: 0.8rem;
            border-radius: 20px;
            padding: 0 12px;
            border: 1px solid #E2E8F0;
            background-color: #FFFFFF;
        }
        button[kind="secondary"]:hover {
            border-color: #EF4444; /* 삭제 느낌의 붉은색 호버 */
            color: #EF4444;
            background-color: #FEF2F2;
        }

        /* 링크 스타일 */
        a { color: #2563EB; text-decoration: none; font-weight: 600; }
        a:hover { text-decoration: underline; color: #1D4ED8; }
        
        /* 제목 폰트 조정 */
        h1, h2, h3 { letter-spacing: -0.02em; color: #0F172A; }
    </style>
""", unsafe_allow_html=True)

# [수정] 카테고리: Package 추가
CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer", "Package"
]

# ==========================================
# 1. 유틸리티 함수
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

# [NEW] 번역 함수 (오류 방지 처리 포함)
def translate_text(text, target_lang='ko'):
    try:
        if not text: return ""
        # 텍스트가 너무 길면 잘라서 번역 (속도 최적화)
        return GoogleTranslator(source='auto', target=target_lang).translate(text[:900])
    except:
        return text # 에러나면 원문 반환

if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None

# ==========================================
# 2. 로직: 쿼리 생성 & AI 필터 & 크롤링
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
                snip = BeautifulSoup(raw_d, "html.parser").get_text(strip=True)[:250]
                
                # [NEW] 해외 뉴스(영어/중국어)의 Snippet을 한국어로 번역 (Insights 강화)
                if country_code not in ['KR']:
                    try:
                        snip = "🌐 " + translate_text(snip)
                    except: pass

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
    
    with st.spinner(f"🔍 '{category}' 관련 글로벌 뉴스 수집 및 분석 중..."):
        all_news = []
        for kw in kws:
            # 주요 3개국 (속도 고려)
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
# 3. Sidebar UI (Category Menu)
# ==========================================
with st.sidebar:
    st.header("Semi-Insight")
    st.caption("Global Market Intelligence")
    st.divider()
    
    # [수정] Target Domain -> Category
    st.subheader("📂 Category")
    
    # 라디오 버튼 (메뉴 스타일 CSS 적용됨)
    selected_category = st.radio("카테고리 선택", CATEGORIES, label_visibility="collapsed")
    
    st.divider()
    with st.expander("🔐 API Settings"):
        api_key = st.text_input("Gemini Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.caption("Auto-loaded")

# ==========================================
# 4. Main UI (Control Panel & Grid)
# ==========================================

# 헤더
c_head, c_info = st.columns([3, 1])
with c_head: 
    st.title(selected_category)
with c_info: 
    if st.session_state.last_update:
        st.markdown(f"<div style='text-align:right; color:#64748B; font-size:0.85em;'>Last Update<br><b>{st.session_state.last_update}</b></div>", unsafe_allow_html=True)

# ------------------------------------
# [수정] 컨트롤 패널 (Native Container)
# ------------------------------------
with st.container(border=True):
    # Row 1: 기간 설정 & 키워드 입력 & 실행 버튼
    c_date, c_kw, c_act = st.columns([1.5, 2.5, 1])
    
    with c_date:
        # [수정] Custom 선택 시 날짜 입력창이 바로 뜨도록 로직 변경
        period = st.selectbox("기간 설정", ["1 Month", "3 Months", "Custom"], label_visibility="collapsed")
        
        today = datetime.now().date()
        if period == "1 Month":
            start_date, end_date = today - timedelta(days=30), today
        elif period == "3 Months":
            start_date, end_date = today - timedelta(days=90), today
        else:
            # Custom 선택 시 아래에 날짜 선택기 표시
            dr = st.date_input("날짜 선택", (today - timedelta(days=7), today), label_visibility="collapsed")
            if len(dr) == 2: start_date, end_date = dr
            else: start_date = end_date = dr[0]

    with c_kw:
        new_kw = st.text_input("키워드 입력", placeholder="추가할 키워드 (예: CoWoS)", label_visibility="collapsed")

    with c_act:
        b_add, b_run = st.columns(2)
        with b_add:
            if st.button("추가", use_container_width=True):
                if new_kw and new_kw not in st.session_state.keywords[selected_category]:
                    st.session_state.keywords[selected_category].append(new_kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        with b_run:
            if st.button("실행", type="primary", use_container_width=True):
                perform_crawling(selected_category, start_date, end_date, api_key)
                st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.rerun()

    # Row 2: 키워드 태그 (간격 좁게)
    current_kws = st.session_state.keywords.get(selected_category, [])
    if current_kws:
        st.write("") # 간격
        st.caption(f"Watching ({len(current_kws)})")
        # [수정] st.columns를 많이 쪼개서 간격을 좁힘
        cols = st.columns(8)
        for i, kw in enumerate(current_kws):
            # 버튼 텍스트를 "키워드 ×" 형태로 심플하게
            if cols[i % 8].button(f"{kw} ×", key=f"del_{kw}", type="secondary", help="삭제"):
                st.session_state.keywords[selected_category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

# ------------------------------------
# [수정] 결과 카드 리스트 (No HTML Strings)
# ------------------------------------
data = st.session_state.news_data.get(selected_category, [])

if data:
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Collected", len(data))
    m2.metric("AI Verified", sum(1 for d in data if d.get('AI_Verified')))
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Grid Loop
    for i in range(0, len(data), 2):
        row_items = data[i : i+2]
        cols = st.columns(2)
        
        for idx, item in enumerate(row_items):
            with cols[idx]:
                # Streamlit Native Container 사용 (깨짐 방지 100%)
                with st.container(border=True):
                    # 1. 메타 정보
                    mc1, mc2 = st.columns([1, 1])
                    with mc1: st.caption(f"📰 {item['Source']}")
                    with mc2: st.caption(f"🗓️ {item['Date'].strftime('%Y-%m-%d')}")
                    
                    # 2. 제목 (링크)
                    st.markdown(f"#### [{item['Title']}]({item['Link']})")
                    
                    # 3. 요약문 (번역된 내용 포함)
                    if item.get('Snippet'):
                        st.markdown(f"<span style='color:#475569; font-size:0.9em;'>{item['Snippet']}</span>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 4. 하단 태그
                    bc1, bc2 = st.columns([3, 1])
                    with bc1:
                        st.markdown(f"<span style='background:#F1F5F9; color:#64748B; padding:4px 8px; border-radius:4px; font-size:0.8em;'>#{item['Keyword']}</span>", unsafe_allow_html=True)
                    with bc2:
                        if item.get('AI_Verified'):
                            st.markdown("✨ **AI**")

else:
    # 빈 상태 (Empty State)
    with st.container(border=True):
        st.markdown("""
            <div style='text-align:center; padding: 40px; color:#94A3B8;'>
                <h3>📭 데이터가 없습니다</h3>
                <p>상단의 '실행' 버튼을 눌러 최신 뉴스를 수집해보세요.</p>
            </div>
        """, unsafe_allow_html=True)
