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
# 0. 페이지 설정 및 Modern CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semiconductor Insight Hub", page_icon="💾")

# 커스텀 CSS 주입
st.markdown("""
    <style>
        /* 전체 폰트 및 배경 설정 */
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }
        
        /* 메인 타이틀 스타일 */
        .main-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1E3A8A; /* Navy Blue */
            margin-bottom: 0.5rem;
        }
        .sub-title {
            font-size: 1.1rem;
            color: #64748B;
            margin-bottom: 2rem;
        }

        /* 뉴스 카드 스타일 (핵심) */
        .news-card {
            background-color: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .news-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
            border-color: #3B82F6;
        }
        
        /* 카드 내부 요소 */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .news-link {
            font-size: 1.15rem;
            font-weight: 700;
            color: #1E293B;
            text-decoration: none;
            line-height: 1.4;
        }
        .news-link:hover {
            color: #2563EB;
        }
        .snippet {
            font-size: 0.9rem;
            color: #475569;
            line-height: 1.5;
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .meta-info {
            font-size: 0.8rem;
            color: #94A3B8;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #F1F5F9;
            padding-top: 10px;
        }
        
        /* 태그 스타일 */
        .tag-pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 99px;
            font-size: 0.7rem;
            font-weight: 600;
        }
        .tag-ai { background-color: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE; }
        .tag-kw { background-color: #F1F5F9; color: #475569; }
        .source-badge { font-weight: 600; color: #64748B; }

        /* 사이드바 스타일 */
        [data-testid="stSidebar"] {
            background-color: #F8FAFC;
            border-right: 1px solid #E2E8F0;
        }
        
        /* 버튼 스타일 오버라이드 */
        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 데이터 관리 로직 (기존 유지)
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
# 2. 로직: 쿼리 생성 & Gemini 필터 & 크롤링
# ==========================================
def make_smart_query(keyword, country_code):
    base_kw = keyword
    negatives = "-TikTok -틱톡 -douyin -dance -shorts -reels -viral -music -influencer -game"
    
    if country_code == 'KR':
        context = "(반도체 OR 소자 OR 공정 OR 소재 OR 파운드리 OR 팹 OR 양산)"
    elif country_code in ['CN', 'HK']: 
        context = "(半导体 OR 芯片 OR 晶圆 OR 光刻胶 OR 蚀刻 OR 封装)"
    elif country_code == 'TW':
        context = "(半導體 OR 晶片 OR 晶圓 OR 光阻 OR 蝕刻 OR 封裝)"
    elif country_code == 'JP':
        context = "(半導体 OR シリコン OR ウェーハ OR レジスト)"
    else: 
        context = "(semiconductor OR chip OR fab OR foundry OR wafer OR lithography)"

    return f'{base_kw} AND {context} {negatives}'

def filter_with_gemini(articles, api_key):
    if not articles or not api_key: return articles
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        content_text = ""
        for i, item in enumerate(articles):
            snippet = item.get('Snippet', '')
            content_text += f"ID_{i+1} | KW: {item['Keyword']} | Src: {item['Source']} | Title: {item['Title']} | Snip: {snippet}\n"
            
        prompt = f"""
        Role: Strict Semiconductor Intelligence Analyst.
        Goal: Filter out noise. Keep B2B Tech/Fab/Materials.
        *** RULES ***
        1. Reject 'TikTok', 'Douyin', purely consumer gadgets.
        2. Keep Fab, Lithography, Materials, Equipment, Market share, Yield.
        *** DATA ***
        {content_text}
        *** OUTPUT ***
        Return IDs of valid articles (e.g., 1, 3). If none, return None.
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

def crawl_google_rss(keyword, country_code, language):
    results = []
    smart_query = make_smart_query(keyword, country_code)
    base_url = f"https://news.google.com/rss/search?q={quote(smart_query)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    try:
        response = requests.get(base_url, headers=get_headers(), timeout=10, verify=False)
        if response.status_code == 200:
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
                    'Snippet': snippet[:200], # 스니펫 길이 조정
                    'AI_Verified': False
                })
    except: pass
    return results

def perform_crawling(category, start_date, end_date, api_key):
    keywords = st.session_state.keywords.get(category, [])
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Progress UI
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)
    
    if not keywords: 
        st.toast("키워드가 없습니다.", icon="⚠️")
        return

    total_steps = len(keywords) * 6
    step = 0 
    raw_articles = []
    
    for kw in keywords:
        targets = [
            ('CN', 'zh-CN'), ('HK', 'zh-CN'), ('TW', 'zh-TW'),
            ('KR', 'ko'), ('US', 'en'), ('JP', 'ja')
        ]
        for cc, lang in targets:
            step += 1
            my_bar.progress(step / total_steps, text=f"🔍 Searching '{kw}' in {cc}...")
            raw_articles.extend(crawl_google_rss(kw, cc, lang))
    
    df = pd.DataFrame(raw_articles)
    if not df.empty:
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        df = df.sort_values(by='Date', ascending=False)
        df = df.drop_duplicates(subset=['Title'])
        candidates = df.head(80).to_dict('records')
    else: candidates = []

    if candidates and api_key:
        my_bar.progress(0.95, text=f"🤖 Gemini AI is verifying {len(candidates)} articles...")
        final_data = filter_with_gemini(candidates, api_key)
    else:
        final_data = candidates[:50]

    my_bar.empty()
    st.session_state.news_data[category] = final_data
    if final_data:
        st.toast(f"{len(final_data)}개의 뉴스를 찾았습니다!", icon="✅")
    else:
        st.toast("검색 결과가 없습니다.", icon="📭")

# ==========================================
# 3. UI 구성 (Sidebar & Main)
# ==========================================

# 사이드바
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.markdown("---")
    
    st.markdown("### 📂 Category")
    selected_category = st.radio("Select Target:", CATEGORIES, index=0)
    
    st.markdown("### 🤖 Intelligence")
    gemini_api_key = None
    if "GEMINI_API_KEY" in st.secrets:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔐 API Connected")
    else:
        gemini_api_key = st.text_input("Gemini API Key", type="password", placeholder="Paste API Key here")
        if not gemini_api_key: st.info("ℹ️ Enter key for AI filtering")
        
    st.markdown("---")
    st.caption("Coverage: CN / HK / TW / KR / US / JP")
    st.caption("Developed by LSH")

# 메인 영역
st.markdown(f'<div class="main-title">{selected_category} Insights</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Global Semiconductor Market Intelligence & News Feed</div>', unsafe_allow_html=True)

# 컨트롤 패널 (상단 배치)
with st.container():
    col1, col2, col3 = st.columns([1.5, 3, 1])
    
    with col1:
        st.markdown("##### 📅 Date Range")
        period = st.selectbox("기간 설정", ["1개월", "3개월", "6개월", "직접입력"], label_visibility="collapsed")
        today = datetime.now().date()
        if period == "1개월": start_date = today - timedelta(days=30); end_date = today
        elif period == "3개월": start_date = today - timedelta(days=90); end_date = today
        elif period == "6개월": start_date = today - timedelta(days=180); end_date = today
        else:
            dr = st.date_input("날짜 선택", (today - timedelta(days=7), today), label_visibility="collapsed")
            if len(dr) == 2: start_date, end_date = dr
            else: start_date = end_date = dr[0]

    with col2:
        st.markdown("##### 🔑 Keywords")
        c_kw1, c_kw2 = st.columns([3, 1])
        new_kw = c_kw1.text_input("New Keyword", placeholder="Add keyword...", label_visibility="collapsed")
        if c_kw2.button("Add", use_container_width=True):
            if new_kw and new_kw not in st.session_state.keywords.get(selected_category, []):
                st.session_state.keywords[selected_category].append(new_kw)
                save_keywords(st.session_state.keywords)
                st.rerun()
        
        # 키워드 칩 표시 (Expander로 숨김 처리 가능)
        current_kws = st.session_state.keywords.get(selected_category, [])
        with st.expander(f"Active Keywords ({len(current_kws)})", expanded=False):
            if current_kws:
                # 5열 그리드로 키워드 나열
                k_cols = st.columns(5)
                for idx, kw in enumerate(current_kws):
                    if k_cols[idx % 5].button(f"🗑️ {kw}", key=f"del_{kw}", help="Click to remove"):
                        st.session_state.keywords[selected_category].remove(kw)
                        save_keywords(st.session_state.keywords)
                        st.rerun()
            else:
                st.caption("No keywords registered.")

    with col3:
        st.markdown("##### 🚀 Action")
        if st.button("Run Crawler", type="primary", use_container_width=True):
            perform_crawling(selected_category, start_date, end_date, gemini_api_key)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()

st.markdown("---")

# 결과 표시 영역 (Card Layout)
data = st.session_state.news_data.get(selected_category, [])

# 대시보드 요약 (데이터가 있을 때만)
if data:
    m1, m2, m3 = st.columns(3)
    verified_count = sum(1 for d in data if d.get('AI_Verified'))
    m1.metric("Total Articles", len(data))
    m2.metric("AI Verified", f"{verified_count} cases")
    m3.metric("Last Updated", st.session_state.last_update.split(' ')[1] if st.session_state.last_update else "-")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Grid Layout (2 columns for desktop)
    grid_cols = st.columns(2)
    
    for index, row in enumerate(data):
        with grid_cols[index % 2]:
            # AI 뱃지 로직
            ai_badge_html = "<span class='tag-pill tag-ai'>✨ AI Verified</span>" if row.get('AI_Verified') else ""
            date_str = row['Date'].strftime('%Y-%m-%d')
            
            # HTML Card Injection
            html_card = f"""
            <div class="news-card">
                <div>
                    <div class="card-header">
                        <span class="source-badge">📰 {row['Source']}</span>
                        {ai_badge_html}
                    </div>
                    <a href="{row['Link']}" target="_blank" class="news-link">{row['Title']}</a>
                    <p class="snippet">{row.get('Snippet', 'No content available.')}</p>
                </div>
                <div class="meta-info">
                    <span>📅 {date_str}</span>
                    <span class="tag-pill tag-kw">#{row['Keyword']}</span>
                </div>
            </div>
            """
            st.markdown(html_card, unsafe_allow_html=True)

else:
    # 데이터 없을 때 Empty State
    st.markdown("""
        <div style='text-align: center; padding: 50px; color: #64748B;'>
            <h2>📭 No Data Available</h2>
            <p>상단의 'Run Crawler' 버튼을 눌러 최신 뉴스를 수집해주세요.</p>
        </div>
    """, unsafe_allow_html=True)
