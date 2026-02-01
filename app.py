import streamlit as st
import pandas as pd
from datetime import datetime, time
import time as time_module
from utils import stock_manager, news_crawler, ai_analyst

# Page Config
st.set_page_config(
    page_title="SemiInfo - Semiconductor Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .stock-up { color: #28a745; font-weight: bold; }
    .stock-down { color: #dc3545; font-weight: bold; }
    .stSidebar {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'keywords' not in st.session_state:
    st.session_state['keywords'] = ['Semiconductor', 'Wafer', 'EUV'] # Default
if 'news_data' not in st.session_state:
    st.session_state['news_data'] = pd.DataFrame()
if 'daily_reports' not in st.session_state:
    st.session_state['daily_reports'] = []

# Valid API Key check
if 'GEMINI_API_KEY' in st.secrets:
    ai_analyst.configure_gemini(st.secrets['GEMINI_API_KEY'])
else:
    # Sidebar input for API key if not in secrets
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    if api_key:
        ai_analyst.configure_gemini(api_key)

# Sidebar - Global Stock
st.sidebar.title("🌍 Global Stock")
st.sidebar.markdown("---")

@st.cache_data(ttl=300) # 5 minutes cache
def get_cached_stocks():
    return stock_manager.get_stock_data()

if st.sidebar.button("🔄 Update Indices"):
    get_cached_stocks.clear()

stock_data = get_cached_stocks()

for sector, companies in stock_data.items():
    with st.sidebar.expander(sector, expanded=False):
        for item in companies:
            color_class = "stock-up" if item['change'] >= 0 else "stock-down"
            icon = "🔼" if item['change'] >= 0 else "🔽"
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                    <span>{item['name']}</span>
                    <span class="{color_class}">{item['price']:.2f} {icon} ({item['pct_change']:.2f}%)</span>
                </div>
                """, 
                unsafe_allow_html=True
            )

st.sidebar.markdown("---")
# Navigation
menu = st.sidebar.radio("Menu", ["Daily Report", "P&C Material", "ED&T Material"])

# Main Content
st.title(f"📊 {menu}")

# Shared Keyword Manager (Visual only for now, logic can be centralized)
with st.expander("🛠️ Keyword & Settings Manager", expanded=False):
    col1, col2 = st.columns([3, 1])
    new_kw = col1.text_input("Add Keyword")
    if col2.button("Add"):
        if new_kw and new_kw not in st.session_state['keywords']:
            st.session_state['keywords'].append(new_kw)
            st.rerun()
            
    st.write("Current Keywords:")
    for kw in st.session_state['keywords']:
        st.write(f"- {kw}")
        # Add remove logic if needed

# 1. Daily Report
if menu == "Daily Report":
    st.info("💡 Daily Report generated at 6:00 AM automatically. Click below to generate manually.")
    
    col1, col2 = st.columns(2)
    with col1:
        report_date = st.date_input("Select Date", datetime.now())
    with col2:
        if st.button("Generate Today's Report"):
            with st.spinner("Crawling news and analyzing with Gemini..."):
                # Simulation: Fetch news from yesterday 12pm to today 6am
                # For demo, just fetching recent news
                news_df = news_crawler.fetch_news(st.session_state['keywords'], ["USA", "Korea", "Japan"])
                st.session_state['news_data'] = news_df
                
                report = ai_analyst.generate_report(news_df, st.session_state['keywords'])
                st.session_state['daily_reports'].append({
                    "date": str(datetime.now().date()),
                    "content": report,
                    "links": news_df[['title', 'url']].to_dict('records')
                })
                st.success("Report Generated!")
    
    st.markdown("### 📑 Latest Report")
    if st.session_state['daily_reports']:
        latest = st.session_state['daily_reports'][-1]
        st.markdown(latest['content'])
        
        st.markdown("#### 🔗 Original Sources")
        for link in latest['links']:
            st.markdown(f"- [{link['title']}]({link['url']})")
    else:
        st.write("No reports generated yet.")

# 2. P&C Material & 3. ED&T Material (Similar Logic)
elif menu in ["P&C Material", "ED&T Material"]:
    st.write(f"Search and Monitor for {menu}")
    
    col_a, col_b, col_c = st.columns(3)
    target_countries = col_a.multiselect("Countries", ["USA", "Korea", "Japan", "Taiwan", "China"], default=["USA", "Korea"])
    period = col_b.selectbox("Period", ["1m", "3m", "6m", "Custom"])
    
    if st.button("🔍 Search News"):
        with st.spinner("Searching..."):
            df = news_crawler.fetch_news(st.session_state['keywords'], target_countries, period_str=period)
            st.dataframe(df, use_container_width=True)
            
            for index, row in df.iterrows():
                with st.container():
                    st.markdown(f"**[{row['date']}] {row['title']}**")
                    st.write(row['summary'])
                    st.markdown(f"[Read more]({row['url']})")
                    st.divider()

