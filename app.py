import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 페이지 설정
st.set_page_config(layout="wide", page_title="Semi-Insight Hub (Final Fix)", page_icon="🛡️")

if 'debug_logs' not in st.session_state: st.session_state.debug_logs = []
if 'report_result' not in st.session_state: st.session_state.report_result = None

# ==========================================
# 1. 로깅 함수
# ==========================================
def log(message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append((level, f"[{timestamp}] {message}"))

# ==========================================
# 2. 핵심: 모델 자동 우회 호출 함수
# ==========================================
def try_generate_content(api_key, prompt):
    # 시도할 모델 순서 (무료 할당량이 넉넉한 순서로 배치)
    # 1.5-flash-8b는 가장 가볍고 할당량이 많음 -> 성공 확률 최고
    models_chain = [
        "gemini-1.5-flash-8b", 
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-2.0-flash-exp" # 이건 할당량이 적으므로 마지막에
    ]
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    for model in models_chain:
        log(f"🔄 모델 시도 중: {model}...", "info")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            # 성공 (200 OK)
            if response.status_code == 200:
                res_json = response.json()
                if 'candidates' in res_json and res_json['candidates']:
                    content = res_json['candidates'][0]['content']['parts'][0]['text']
                    log(f"✅ 성공! ({model} 모델이 응답함)", "success")
                    return content
                else:
                    log(f"⚠️ {model}: 응답은 왔으나 내용이 빔 (Safety Block 등)", "warning")
            
            # 실패 분석
            elif response.status_code == 429:
                log(f"⛔ {model}: 용량 초과 (Quota Exceeded). 다음 모델로 전환합니다.", "warning")
                continue # 다음 모델 시도
            
            elif response.status_code == 404:
                log(f"🚫 {model}: 모델을 찾을 수 없음 (404). 다음 모델로 전환합니다.", "warning")
                continue
                
            else:
                log(f"❌ {model} 오류 (HTTP {response.status_code}): {response.text[:100]}...", "error")
                continue

        except Exception as e:
            log(f"💥 통신 오류 ({model}): {str(e)}", "error")
            continue
            
    return None # 모든 모델 실패

# ==========================================
# 3. 전체 프로세스 실행
# ==========================================
def run_full_process(api_key):
    st.session_state.debug_logs = [] 
    st.session_state.report_result = None
    
    # 1. 뉴스 수집
    log("📡 [1단계] 뉴스 데이터 수집 시작...", "info")
    target_kw = "삼성전자 파운드리 반도체"
    url = f"https://news.google.com/rss/search?q={quote(target_kw)}+when:2d&hl=ko&gl=KR&ceid=KR:ko"
    
    news_titles = []
    try:
        res = requests.get(url, timeout=5, verify=False)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')[:5] # 5개만 (토큰 절약)
        
        if not items:
            log("❌ 수집된 뉴스가 없습니다. 검색어/기간 확인 필요.", "error")
            return
            
        for item in items:
            news_titles.append(f"- {item.title.text}")
        
        log(f"✅ 뉴스 {len(items)}건 수집 완료.", "success")
        
    except Exception as e:
        log(f"❌ 크롤링 실패: {e}", "error")
        return

    # 2. AI 리포트 생성
    log("🧠 [2단계] AI 분석 시작 (자동 모델 우회 적용)...", "info")
    
    prompt = f"""
    당신은 반도체 시장 전문가입니다. 
    아래 뉴스 제목들을 보고 [일일 시장 브리핑]을 한국어로 작성하세요.
    
    [뉴스 데이터]
    {chr(10).join(news_titles)}
    
    [작성 양식]
    1. 📝 핵심 3줄 요약
    2. 🚨 주요 이슈 분석
    3. 💡 향후 전망 (한 줄)
    """
    
    result_text = try_generate_content(api_key, prompt)
    
    if result_text:
        st.session_state.report_result = result_text
        log("🎉 [완료] 리포트 생성이 성공적으로 끝났습니다!", "success")
    else:
        log("💀 [실패] 모든 AI 모델이 응답하지 않았습니다. (할당량 완전 소진 가능성)", "error")

# ==========================================
# UI 구성
# ==========================================
with st.sidebar:
    st.header("🛠️ Final Debugger")
    user_key = st.text_input("API Key", value="AIzaSyCBSqIQBIYQbWtfQAxZ7D5mwCKFx-7VDJo", type="password")
    
    if st.button("🚨 진단 및 리포트 강제 실행", type="primary"):
        run_full_process(user_key)

st.title("💠 Semi-Insight Hub (Recovery Mode)")

st.info("왼쪽 사이드바의 **[🚨 진단 및 리포트 강제 실행]** 버튼을 누르세요.\n시스템이 자동으로 사용 가능한 AI 모델을 찾아 리포트를 생성합니다.")

# 로그 출력
if st.session_state.debug_logs:
    st.divider()
    st.subheader("📋 처리 로그")
    for level, msg in st.session_state.debug_logs:
        if level == "error": st.error(msg)
        elif level == "success": st.success(msg)
        elif level == "warning": st.warning(msg)
        else: st.info(msg)

# 결과 출력
if st.session_state.report_result:
    st.divider()
    st.subheader("📑 AI Daily Report")
    st.markdown(f"""
    <div style="background-color: white; padding: 30px; border-radius: 10px; border: 1px solid #ddd; line-height: 1.6;">
        {st.session_state.report_result}
    </div>
    """, unsafe_allow_html=True)
