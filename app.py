import streamlit as st
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import quote
import json
import datetime

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Final Fix", layout="wide")

# ==========================================
# 1. 심플 크롤러
# ==========================================
def get_news():
    url = f"https://news.google.com/rss/search?q={quote('삼성전자 반도체')}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=5, verify=False)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')[:5]
        return [item.title.text for item in items]
    except:
        return []

# ==========================================
# 2. AI 호출 (v1 정식 주소 사용)
# ==========================================
def call_ai_v1(api_key, news_list):
    # [핵심] v1beta가 아니라 v1을 사용해야 1.5 모델 404가 안 뜸
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    반도체 전문가로서 아래 뉴스를 3줄로 요약해.
    {json.dumps(news_list, ensure_ascii=False)}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [ # 안전장치 해제
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        res = requests.post(url, json=data, timeout=30)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"에러 발생: {res.status_code}\n{res.text}"
    except Exception as e:
        return f"통신 에러: {e}"

# ==========================================
# 3. UI 실행
# ==========================================
st.title("💠 Last Attempt: v1 Stable Endpoint")

with st.sidebar:
    api_key = st.text_input("API Key", value="AIzaSyCBSqIQBIYQbWtfQAxZ7D5mwCKFx-7VDJo", type="password")
    
if st.button("🚀 리포트 생성 (Gemini 1.5 Flash / v1)", type="primary"):
    status = st.empty()
    
    # 1. 수집
    status.info("📡 뉴스 수집 중...")
    news = get_news()
    if not news:
        status.error("뉴스 수집 실패")
        st.stop()
        
    # 2. 생성
    status.info("🧠 AI 분석 중 (Gemini 1.5 Flash - v1 Endpoint)...")
    result = call_ai_v1(api_key, news)
    
    # 3. 결과
    if "에러" in result:
        status.error("실패")
        st.error(result)
        # 429 에러(Quota)면 잠시 쉬어야 함을 안내
        if "429" in result:
            st.warning("⚠️ 'Quota Exceeded'는 무료 사용량을 다 썼다는 뜻입니다. 5분 뒤에 다시 시도하면 됩니다.")
    else:
        status.success("완료!")
        st.markdown("### 📝 Daily Report")
        st.write(result)
        st.divider()
        st.caption("참고 뉴스: " + ", ".join(news))
