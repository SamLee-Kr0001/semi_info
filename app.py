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
import html # HTML 이스케이프용

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 Modern CSS (Advanced)
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

# 세련된 UI를 위한 Custom CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            color: #1E293B;
        }
        
        /* 전체 배경색 조정 */
        .stApp {
            background-color: #F8FAFC;
        }

        /* 1. 컨트롤 패널 스타일 (상단 검색바) */
        .control-panel {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 25px;
            border: 1px solid #E2E8F0;
        }

        /* 2. 뉴스 카드 스타일 (Shadow & Hover) */
        .news-card {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 24px;
            height: 100%;
            border: 1px solid #F1F5F9;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .news-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border-color: #6366f1; /* Indigo highlight */
        }
        
        .news-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #0F172A;
            text-decoration: none;
            margin-bottom: 10px;
            display: block;
            line-height: 1.4;
        }
        .news-title:hover {
            color: #4F46E5; /* Indigo-600 */
        }
        
        .news-snippet {
            font-size: 0.95rem;
            color: #64748B;
            line-height: 1.6;
            margin-bottom: 20px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
        }

        .news-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 16px;
            border-top: 1px solid #F1F5F9;
            font-size: 0.85rem;
            color: #94A3B8;
        }

        /* 뱃지 스타일 */
        .badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.75rem;
        }
        .badge-ai { background-color: #EEF2FF; color: #4F46E5; border: 1px solid #C7D2FE; }
        .badge-src { background-color: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; }
        
        /* Sidebar 스타일링 */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E2E8F0;
        }
        
        /* 버튼 커스텀 */
        div.stButton > button {
            border-radius: 8px;
            height: 42px;
            font-weight: 600;
        }
        
        /* Expander 커스텀 */
        .streamlit-expanderHeader {
            font-weight: 600;
            color: #334155;
        }
    </style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "기업정보", "반도체 정보", "Photoresist", "Wet chemical", "CMP Slurry", 
    "Process Gas", "Precursor", "Metal target", "Wafer"
]

# ==========================================
# 1. 데이터 및 유틸리티 (기존 로직 유지)
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

# 크롤링 및 AI 로직 (핵심 기능 유지)
def make_smart_query(keyword, country_code):
    base_kw = keyword
    negatives = "-TikTok -틱톡 -douyin -dance -shorts -reels -viral -music -influencer -game -soccer"
    
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
        
        # 텍스트가 너무 길면 오류가 날 수 있으니 적당히 자름
        content_text = ""
        for i, item in enumerate(articles[:40]): # API 비용/속도 고려하여 최대 40개만 검사
            snippet = item.get('Snippet', '')[:100]
            content_text += f"ID_{i+1} | Title: {item['Title']} | Snip: {snippet}\n"
            
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
        return filtered if filtered else articles # 너무 많이 걸러지면 원본 반환 안전장치
    except Exception:
        return articles

def crawl_google_rss(keyword, country_code, language):
    results = []
    smart_query = make_smart_query(keyword, country_code)
    url = f"https://news.google.com/rss/search?q={quote(smart_query)}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            for item in soup.find_all('item')[:5]: # 키워드 당 최대 5개로 제한 (속도 향상)
                src = item.source.text if item.source else "Google"
                raw_d = item.description.text if item.description else ""
                snip = BeautifulSoup(raw_d, "html.parser").get_text(strip=True)[:200]
                
                # 날짜 파싱 단순화
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
    
    with st.spinner(f"🌐 Scanning global news for {len(kws)} keywords..."):
        all_news = []
        for kw in kws:
            # 주요 3개국만 우선 타겟팅 (속도 최적화)
            for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW')]:
                all_news.extend(crawl_google_rss(kw, cc, lang))
        
        # 필터링 및 정렬
        df = pd.DataFrame(all_news)
        if not df.empty:
            df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
            df = df.drop_duplicates(subset=['Title']).sort_values('Date', ascending=False)
            final_list = df.head(60).to_dict('records') # 최대 60개 유지
            
            if api_key and final_list:
                final_list = filter_with_gemini(final_list, api_key)
            
            st.session_state.news_data[category] = final_list
        else:
             st.session_state.news_data[category] = []

# ==========================================
# 2. Sidebar UI (Clean & Compact)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6182/6182650.png", width=50) # 임시 로고
    st.markdown("### Semi-Insight Hub")
    st.caption("Global Market Intelligence")
    st.divider()
    
    # 카테고리 선택 - Selectbox가 더 깔끔함
    st.markdown("#### 📂 Target Domain")
    selected_category = st.selectbox("Select Category", CATEGORIES, label_visibility="collapsed")
    
    st.divider()
    
    # API Key 입력
    with st.expander("🔐 API Settings", expanded=False):
        api_key = st.text_input("Gemini API Key", type="password", key="s_api_key")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("Secrets Key Loaded")
    
    st.info(f"Current: **{selected_category}**\n\nCN/TW/KR/US Coverage")

# ==========================================
# 3. Main Dashboard UI
# ==========================================

# (1) 헤더 영역
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title(f"{selected_category}")
with col_h2:
    if st.session_state.last_update:
        st.caption(f"Last updated:\n{st.session_state.last_update}")

# (2) 컨트롤 패널 (Toolbar 스타일)
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([2, 3, 1, 1.5])

with c1:
    # 날짜
    period = st.selectbox("📅 Period", ["1 Month", "3 Months", "Custom"], label_visibility="collapsed")
    today = datetime.now().date()
    if period == "1 Month": s_date, e_date = today - timedelta(days=30), today
    elif period == "3 Months": s_date, e_date = today - timedelta(days=90), today
    else: s_date, e_date = today - timedelta(days=7), today

with c2:
    # 키워드 입력
    new_kw = st.text_input("➕ Add Keyword", placeholder="Type keyword (e.g., HBM)", label_visibility="collapsed")

with c3:
    # 키워드 추가 버튼
    if st.button("Add", use_container_width=True):
        if new_kw and new_kw not in st.session_state.keywords[selected_category]:
            st.session_state.keywords[selected_category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()

with c4:
    # 실행 버튼
    if st.button("🚀 Scrape Now", type="primary", use_container_width=True):
        perform_crawling(selected_category, s_date, e_date, api_key)
        st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.rerun()

# 활성 키워드 표시 (Chips 형태)
current_kws = st.session_state.keywords.get(selected_category, [])
if current_kws:
    st.write("Active Keywords:")
    kw_cols = st.columns(8) # 한 줄에 여러 개
    for i, kw in enumerate(current_kws):
        if kw_cols[i % 8].button(f"{kw} ✖", key=f"k_{kw}", help="Remove"):
            st.session_state.keywords[selected_category].remove(kw)
            save_keywords(st.session_state.keywords)
            st.rerun()
else:
    st.warning("등록된 키워드가 없습니다. 키워드를 추가해주세요.")

st.markdown('</div>', unsafe_allow_html=True) # End Control Panel

# (3) 데이터 그리드 (Bug Fix: Safer Rendering)
data = st.session_state.news_data.get(selected_category, [])

if data:
    # Metric 요약
    m1, m2 = st.columns(2)
    m1.metric("Collected News", f"{len(data)}")
    verified_cnt = sum(1 for d in data if d.get('AI_Verified'))
    m2.metric("AI Verified", f"{verified_cnt}")
    
    st.divider()

    # Grid Layout Logic (오류 방지 로직 적용)
    # columns를 미리 선언하지 않고, 데이터를 2개씩 쪼개서 반복문 안에서 columns 생성
    for i in range(0, len(data), 2):
        row_items = data[i : i+2] # 2개씩 슬라이싱
        cols = st.columns(2)
        
        for idx, item in enumerate(row_items):
            with cols[idx]:
                # HTML 이스케이프 (특수문자로 인한 깨짐 방지)
                safe_title = html.escape(item['Title'])
                safe_snip = html.escape(item.get('Snippet', ''))
                safe_src = html.escape(item['Source'])
                link = item['Link']
                date_str = item['Date'].strftime('%Y-%m-%d')
                
                # AI 뱃지
                ai_html = '<span class="badge badge-ai">✨ AI Pick</span>' if item.get('AI_Verified') else ''
                
                # Card HTML
                card_html = f"""
                <div class="news-card">
                    <div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                            <span class="badge badge-src">{safe_src}</span>
                            {ai_html}
                        </div>
                        <a href="{link}" target="_blank" class="news-title">{safe_title}</a>
                        <p class="news-snippet">{safe_snip}</p>
                    </div>
                    <div class="news-meta">
                        <span>🗓 {date_str}</span>
                        <span>#{item['Keyword']}</span>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
else:
    st.info("👋 'Scrape Now' 버튼을 눌러 뉴스를 수집하세요.")

