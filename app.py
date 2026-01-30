import streamlit as st
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import quote
import json
import time

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Auto-Discovery Mode", layout="wide")

# ==========================================
# 1. 내 키로 사용 가능한 모델 명단 조회 (가장 중요)
# ==========================================
def get_available_models(api_key):
    # v1beta 엔드포인트에서 모델 리스트를 조회합니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # 'generateContent' 기능을 지원하는 모델만 추출
            valid_models = [
                m['name'].replace("models/", "") 
                for m in data.get('models', []) 
                if 'generateContent' in m.get('supportedGenerationMethods', [])
            ]
            return valid_models
        else:
            return []
    except:
        return []

# ==========================================
# 2. 뉴스 수집
# ==========================================
def get_news():
    url = f"https://news.google.com/rss/search?q={quote('삼성전자 파운드리')}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=5, verify=False)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')[:5]
        return [f"- {item.title.text}" for item in items]
    except:
        return []

# ==========================================
# 3. AI 실행 (조회된 모델 리스트 순회)
# ==========================================
def run_ai(api_key, news_data):
    # 1. 모델 리스트 확보
    models = get_available_models(api_key)
    
    if not models:
        st.error("❌ API Key로 조회 가능한 모델이 하나도 없습니다. (키 권한 문제)")
        return

    st.info(f"📋 사용 가능 모델 목록 확인됨: {', '.join(models)}")
    
    prompt = f"""
    [뉴스 데이터]
    {chr(10).join(news_data)}
    
    위 뉴스를 바탕으로 반도체 시장 동향을 3줄로 요약해.
    """
    
    # 2. 모델 순서대로 시도
    for model in models:
        # gemini-pro-vision 등 텍스트 전용이 아닌건 스킵할 수도 있으나, 일단 시도
        if "vision" in model: continue 
        
        status_msg = st.empty()
        status_msg.write(f"🔄 시도 중: {model}...")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()['candidates'][0]['content']['parts'][0]['text']
                    status_msg.empty()
                    st.success(f"✅ 성공! (모델: {model})")
                    st.markdown("### 📝 리포트 결과")
                    st.write(result)
                    return # 성공하면 종료
                except:
                    # 200인데 내용이 없는 경우 (안전 필터 등)
                    pass
            elif response.status_code == 429:
                status_msg.write(f"⛔ {model}: 사용량 초과 (Pass)")
            else:
                status_msg.write(f"❌ {model}: {response.status_code} 에러")
                
        except Exception as e:
            print(e)
            
    st.error("💀 모든 모델 시도 실패. (잠시 후 다시 시도해보세요)")

# ==========================================
# 4. UI
# ==========================================
st.title("💠 AI Model Auto-Discovery")

with st.sidebar:
    api_key = st.text_input("API Key", value="AIzaSyCBSqIQBIYQbWtfQAxZ7D5mwCKFx-7VDJo", type="password")

if st.button("🚀 실행 (모델 자동 탐색)", type="primary"):
    # 뉴스 수집
    news = get_news()
    if not news:
        st.error("뉴스 수집 실패")
    else:
        st.success(f"뉴스 {len(news)}건 수집 완료")
        # AI 실행
        run_ai(api_key, news)
