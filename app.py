import streamlit as st
import pandas as pd
from datetime import datetime
import time as time_module
# 내부 모듈 임포트 (파일이 실제 존재해야 합니다)
try:
    from utils import stock_manager, news_crawler, ai_analyst
except ImportError:
    st.error("utils 폴더 내의 모듈을 찾을 수 없습니다. 파일 구성을 확인해주세요.")

# Page Config
st.set_page_config(
    page_title="SemiInfo - Semiconductor Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff; padding: 10px;
        border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .stock-up { color: #28a745; font-weight: bold; }
    .stock-down { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Session State 초기화
if 'keywords' not in st.session_state:
    st.session_state['keywords'] = ['Semiconductor', 'Wafer', 'EUV']
if 'news_data' not in st.session_state:
    st.session_state['news_data'] = pd.DataFrame()
if 'daily_reports' not in st.session_state:
    st.session_state['daily_reports'] = []

# Gemini API Key 설정
api_key = st.secrets.get('GEMINI_API_KEY') or st.sidebar.text_input("Gemini API Key", type="password")
if api_key:
    ai_analyst.configure_gemini(api_key)

# Sidebar - Global Stock
st.sidebar.title("🌍 Global Stock")
st.sidebar.markdown("---")

@st.cache_data(ttl=300)
def get_cached_stocks():
    # stock_manager.get_stock_data()가 사전 형태의 데이터를 반환한다고 가정합니다.
    return stock_manager.get_stock_data()

if st.sidebar.button("🔄 Update Indices"):
    st.cache_data.clear() # 전체 캐시 초기화 혹은 특정 함수 초기화

stock_data = get_cached_stocks()

if stock_data:
    for sector, companies in stock_data.items():
        with st.sidebar.expander(sector, expanded=False):
            for item in companies:
                # 데이터 타입 방어 코드
                price = item.get('price', 0)
                change = item.get('change', 0)
                pct = item.get('pct_change', 0)
                
                color_class = "stock-up" if change >= 0 else "stock-down"
                icon = "🔼" if change >= 0 else "🔽"
                
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 5px;">
                        <span>{item['name']}</span>
                        <span class="{color_class}">{price:.2f} {icon} ({pct:.2f}%)</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

st.sidebar.markdown("---")
menu = st.sidebar.radio("Menu", ["Daily Report", "P&C Material", "ED&T Material"])

st.title(f"📊 {menu}")

# Keyword Manager
with st.expander("🛠️ Keyword & Settings Manager", expanded=False):
    col1, col2 = st.columns([3, 1])
    new_kw = col1.text_input("Add Keyword", key="new_kw_input")
    if col2.button("Add"):
        if new_kw and new_kw not in st.session_state['keywords']:
            st.session_state['keywords'].append(new_kw)
            st.rerun()
            
    st.write("Current Keywords:")
    cols = st.columns(4)
    for i, kw in enumerate(st.session_state['keywords']):
        cols[i % 4].info(f" {kw}")

# 1. Daily Report
if menu == "Daily Report":
    st.info("💡 Daily Report는 매일 아침 자동 생성되거나 수동으로 생성할 수 있습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        report_date = st.date_input("Select Date", datetime.now())
    with col2:
        if st.button("Generate Today's Report"):
            with st.spinner("Gemini가 뉴스를 분석 중입니다..."):
                news_df = news_crawler.fetch_news(st.session_state['keywords'], ["USA", "Korea", "Japan"])
                if not news_df.empty:
                    st.session_state['news_data'] = news_df
                    report = ai_analyst.generate_report(news_df, st.session_state['keywords'])
                    st.session_state['daily_reports'].append({
                        "date": str(datetime.now().date()),
                        "content": report,
                        "links": news_df[['title', 'url']].to_dict('records')
                    })
                    st.success("보고서 생성 완료!")
                else:
                    st.warning("수집된 뉴스 데이터가 없습니다.")
    
    st.markdown("---")
    if st.session_state['daily_reports']:
        latest = st.session_state['daily_reports'][-1]
        st.subheader(f"📑 {latest['date']} 리포트")
        st.markdown(latest['content'])
        
        with st.expander("🔗 출처 목록 확인"):
            for link in latest['links']:
                st.markdown(f"- [{link['title']}]({link['url']})")
    else:
        st.write("생성된 리포트가 없습니다.")

# 2. Materials 메뉴
elif menu in ["P&C Material", "ED&T Material"]:
    st.subheader(f"🔍 {menu} 분석 및 모니터링")
    col_a, col_b = st.columns(2)
    target_countries = col_a.multiselect("대상 국가", ["USA", "Korea", "Japan", "Taiwan", "China"], default=["USA", "Korea"])
    period = col_b.selectbox("조회 기간", ["1d", "1w", "1m", "3m"])
    
    if st.button("뉴스 검색 수행"):
        with st.spinner("데이터를 불러오는 중..."):
            df = news_crawler.fetch_news(st.session_state['keywords'], target_countries, period_str=period)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                for _, row in df.iterrows():
                    with st.container():
                        st.markdown(f"**{row['title']}** ({row.get('date', 'N/A')})")
                        st.write(row.get('summary', '요약 정보 없음'))
                        st.markdown(f"[기사 원문 보기]({row['url']})")
                        st.divider()
            else:
                st.info("검색 결과가 없습니다.")
