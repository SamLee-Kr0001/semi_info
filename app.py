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
import concurrent.futures # [NEW] 병렬 처리를 위한 모듈

# [필수] 번역 라이브러리
from deep_translator import GoogleTranslator

# Google Gemini
import google.generativeai as genai

# ==========================================
# 0. 페이지 설정 및 CSS
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            background-color: #F8FAFC;
            color: #1E293B;
        }
        
        .stApp { background-color: #F8FAFC; }

        /* 뉴스 카드 스타일 */
        .news-title {
            font-size: 16px !important;
            font-weight: 700 !important;
            color: #111827 !important;
            text-decoration: none;
            line-height: 1.4;
            display: block;
            margin-bottom: 6px;
        }
        .news-title:hover {
            color: #2563EB !important;
            text-decoration: underline;
        }
        
        .news-snippet {
            font-size: 13.5px !important;
            color: #475569 !important;
            line-height: 1.5;
            margin-bottom: 10px;
        }

        .news-meta {
            font-size: 12px !important;
            color: #94A3B8 !important;
        }

        .control-box {
            background-color: #FFFFFF;
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            margin-bottom: 20px;
        }
        
        button[kind="secondary"] {
            height: 28px !important;
            font-size: 12px !important;
            padding: 0 10px !important;
            border-radius: 14px !important;
        }
    </style>
""", unsafe_allow_html=True)

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

if 'keywords' not in st.session_state: st.session_state.keywords = load_keywords()
if 'news_data' not in st.session_state: st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'last_update' not in st.session_state: st.session_state.last_update = None

# ==========================================
# 2. 로직: 크롤링 & 병렬 번역 & AI
# ==========================================

# [NEW] 단일 텍스트 번역 함수 (에러 처리 강화)
def safe_translate(text):
    if not text: return ""
    try:
        # 1000자 제한
        return GoogleTranslator(source='auto', target='ko').translate(text[:999])
    except:
        return text

# [NEW] 기사 리스트 병렬 번역 처리기 (속도 개선의 핵심)
def parallel_translate_articles(articles):
    # 번역이 필요한 기사(해외)만 식별
    tasks = []
    for article in articles:
        # KR이 아닌 경우에만 번역 대상
        if 'KR' not in article.get('Country', 'KR'):
            tasks.append(article)
    
    if not tasks:
        return articles

    # ThreadPool로 병렬 처리 (최대 10개 동시 작업)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 제목 번역 Future 생성
        title_futures = {executor.submit(safe_translate, a['Title']): a for a in tasks}
        # 요약 번역 Future 생성
        snip_futures = {executor.submit(safe_translate, a['Snippet']): a for a in tasks}
        
        # 결과 수집 (제목)
        for future in concurrent.futures.as_completed(title_futures):
            article = title_futures[future]
            try:
                trans_title = future.result()
                if trans_title and trans_title != article['Title']:
                    article['Title'] = trans_title
            except: pass

        # 결과 수집 (요약)
        for future in concurrent.futures.as_completed(snip_futures):
            article = snip_futures[future]
            try:
                trans_snip = future.result()
                if trans_snip and trans_snip != article['Snippet']:
                    article['Snippet'] = f"🌐 {trans_snip}"
            except: pass
            
    return articles

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
        Role: Semiconductor Analyst.
        Task: Filter noise. Keep B2B Tech/Fab/Materials.
        Data: {content_text}
        Output: IDs ONLY (e.g., 1, 3).
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
            for item in soup.find_all('item')[:5]: # 키워드 당 5개 제한
                src = item.source.text if item.source else "Google"
                raw_d = item.description.text if item.description else ""
                snip = BeautifulSoup(raw_d, "html.parser").get_text(strip=True)[:200]
                title = item.title.text

                # [최적화] 여기서 번역하지 않고 원본만 저장
                pub_date = item.pubDate.text if item.pubDate else str(datetime.now())
                try: dt_obj = pd.to_datetime(pub_date).to_pydatetime()
                except: dt_obj = datetime.now()

                results.append({
                    'Title': title, 'Source': src, 'Date': dt_obj,
                    'Link': item.link.text, 'Keyword': keyword, 'Snippet': snip,
                    'AI_Verified': False,
                    'Country': country_code # 번역 대상 식별용
                })
    except: pass
    return results

def perform_crawling(category, start_date, end_date, api_key):
    kws = st.session_state.keywords.get(category, [])
    if not kws: return
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    with st.spinner(f"🚀 '{category}' 뉴스 고속 수집 중..."):
        all_news = []
        for kw in kws:
            # KR, US, TW, CN 등 수집
            for cc, lang in [('KR','ko'), ('US','en'), ('TW','zh-TW'), ('CN', 'zh-CN')]:
                all_news.extend(crawl_google_rss(kw, cc, lang))
        
        # 1. 데이터 정리 (날짜 필터 및 중복 제거)
        df = pd.DataFrame(all_news)
        if not df.empty:
            df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
            df = df.drop_duplicates(subset=['Title']).sort_values('Date', ascending=False)
            
            # 2. 상위 60개만 남김 (번역 대상 최소화)
            final_list = df.head(60).to_dict('records')
            
            # 3. [최적화] 살아남은 기사만 병렬 번역 실행
            if final_list:
                final_list = parallel_translate_articles(final_list)

            # 4. AI 필터링
            if api_key and final_list:
                final_list = filter_with_gemini(final_list, api_key)
            
            st.session_state.news_data[category] = final_list
        else:
             st.session_state.news_data[category] = []

# ==========================================
# 3. Sidebar
# ==========================================
with st.sidebar:
    st.header("Semi-Insight")
    st.divider()
    st.subheader("📂 Category")
    selected_category = st.radio("카테고리", CATEGORIES, label_visibility="collapsed")
    st.divider()
    with st.expander("🔐 API Key"):
        api_key = st.text_input("Key", type="password")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.caption("Loaded")

# ==========================================
# 4. Main UI
# ==========================================
c_head, c_info = st.columns([3, 1])
with c_head: st.title(selected_category)
with c_info: 
    if st.session_state.last_update:
        st.markdown(f"<div style='text-align:right; font-size:12px; color:#888;'>Last Update<br><b>{st.session_state.last_update}</b></div>", unsafe_allow_html=True)

# 컨트롤 패널
with st.container(border=True):
    c1, c2, c3 = st.columns([1.5, 2.5, 1])
    with c1:
        period = st.selectbox("기간", ["1 Month", "3 Months", "Custom"], label_visibility="collapsed")
        today = datetime.now().date()
        if period == "1 Month": s, e = today - timedelta(days=30), today
        elif period == "3 Months": s, e = today - timedelta(days=90), today
        else:
            dr = st.date_input("날짜", (today-timedelta(7), today), label_visibility="collapsed")
            if len(dr)==2: s, e = dr
            else: s, e = dr[0], dr[0]
            
    with c2:
        new_kw = st.text_input("키워드", placeholder="예: HBM", label_visibility="collapsed")
        
    with c3:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("추가", use_container_width=True):
                if new_kw and new_kw not in st.session_state.keywords[selected_category]:
                    st.session_state.keywords[selected_category].append(new_kw)
                    save_keywords(st.session_state.keywords)
                    st.rerun()
        with b2:
            if st.button("실행", type="primary", use_container_width=True):
                perform_crawling(selected_category, s, e, api_key)
                st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.rerun()

    # 키워드 태그
    curr_kws = st.session_state.keywords.get(selected_category, [])
    if curr_kws:
        st.write("")
        cols = st.columns(8)
        for i, kw in enumerate(curr_kws):
            if cols[i%8].button(f"{kw} ×", key=f"d_{kw}", type="secondary"):
                st.session_state.keywords[selected_category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

# 결과 리스트
data = st.session_state.news_data.get(selected_category, [])

if data:
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Collected", len(data))
    m2.metric("AI Verified", sum(1 for d in data if d.get('AI_Verified')))
    st.markdown("<br>", unsafe_allow_html=True)
    
    for i in range(0, len(data), 2):
        row_items = data[i : i+2]
        cols = st.columns(2)
        for idx, item in enumerate(row_items):
            with cols[idx]:
                with st.container(border=True):
                    # 메타 정보
                    st.markdown(f"""
                        <div class="news-meta" style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span>📰 {item['Source']}</span>
                            <span>{item['Date'].strftime('%Y-%m-%d')}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 제목 (16px)
                    st.markdown(f'<a href="{item["Link"]}" target="_blank" class="news-title">{item["Title"]}</a>', unsafe_allow_html=True)
                    
                    # 요약 (13.5px)
                    if item.get('Snippet'):
                        st.markdown(f'<div class="news-snippet">{item["Snippet"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 하단 태그
                    ft1, ft2 = st.columns([3, 1])
                    with ft1:
                        st.markdown(f"<span style='background:#F1F5F9; color:#64748B; padding:3px 8px; border-radius:4px; font-size:11px;'>#{item['Keyword']}</span>", unsafe_allow_html=True)
                    with ft2:
                        if item.get('AI_Verified'):
                            st.markdown("<span style='color:#4F46E5; font-size:11px; font-weight:bold;'>✨ AI Pick</span>", unsafe_allow_html=True)
else:
    with st.container(border=True):
        st.markdown("<div style='text-align:center; padding:30px; color:#999;'>데이터가 없습니다.<br>상단의 '실행' 버튼을 눌러주세요.</div>", unsafe_allow_html=True)
