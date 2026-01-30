import streamlit as st
import pandas as pd
import requests
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import time
import random
import yfinance as yf

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 페이지 설정
st.set_page_config(layout="wide", page_title="Semi-Insight Hub (Debug)", page_icon="🔧")

# 세션 상태 초기화 (화면 증발 방지용)
if 'debug_logs' not in st.session_state: st.session_state.debug_logs = []
if 'report_result' not in st.session_state: st.session_state.report_result = None

# ==========================================
# 1. 핵심 기능: 블랙박스 로깅 & 통신
# ==========================================
def log(message, level="info"):
    """화면에 로그를 남기고 세션에 저장함"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    st.session_state.debug_logs.append((level, log_entry))
    
    # 즉시 출력
    if level == "error": st.error(log_entry)
    elif level == "success": st.success(log_entry)
    elif level == "warning": st.warning(log_entry)
    else: st.info(log_entry)

def get_available_models(api_key):
    """내 키로 사용 가능한 모델 명단을 구글에 직접 물어봄"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # generateContent를 지원하는 모델만 필터링
            models = [m['name'].split('/')[-1] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            return models
        else:
            log(f"모델 리스트 조회 실패: {res.text}", "error")
            return []
    except Exception as e:
        log(f"모델 조회 중 통신 에러: {e}", "error")
        return []

def run_debug_process(api_key):
    st.session_state.debug_logs = [] # 로그 초기화
    st.session_state.report_result = None
    
    log("🚀 [1단계] 프로세스 시작...", "info")
    
    # 1. 사용 가능한 모델 확인
    available_models = get_available_models(api_key)
    if not available_models:
        log("❌ 사용 가능한 모델을 찾을 수 없습니다. API Key를 확인하세요.", "error")
        return
    
    log(f"✅ 사용 가능 모델 확인됨: {', '.join(available_models[:3])}...", "success")
    
    # 우선순위 모델 선정 (gemini-2.0-flash가 있으면 그거 쓰고, 없으면 리스트의 첫번째 거)
    target_model = "gemini-2.0-flash"
    if target_model not in available_models:
        # 2.0이 없으면 1.5 flash 시도
        if "gemini-1.5-flash" in available_models:
            target_model = "gemini-1.5-flash"
        else:
            target_model = available_models[0] # 아무거나 되는거
            
    log(f"🎯 타겟 모델 설정: {target_model}", "info")

    # 2. 뉴스 수집 (한국어, 삼성전자 예시)
    log("🚀 [2단계] 뉴스 수집 시작 (Keyword: 삼성전자 파운드리)", "info")
    
    url = f"https://news.google.com/rss/search?q={quote('삼성전자 파운드리')}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=5, verify=False)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')[:5] # 5개만
        
        if not items:
            log("❌ 뉴스 수집 실패 (0건)", "error")
            return
            
        news_data = []
        for item in items:
            news_data.append(f"- {item.title.text}")
            
        log(f"✅ 뉴스 {len(items)}건 수집 완료:\n" + "\n".join(news_data), "success")
        
    except Exception as e:
        log(f"❌ 크롤링 에러: {e}", "error")
        return

    # 3. AI 리포트 생성 요청
    log(f"🚀 [3단계] AI({target_model})에게 요약 요청 전송...", "info")
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    다음 뉴스 제목들을 바탕으로 '반도체 시장 동향'을 3줄로 요약해.
    
    [뉴스 목록]
    {json.dumps(news_data, ensure_ascii=False)}
    """
    
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
        ai_res = requests.post(api_url, headers=headers, json=data, timeout=30)
        
        if ai_res.status_code == 200:
            result_json = ai_res.json()
            
            # 응답 구조 확인
            if 'candidates' in result_json and result_json['candidates']:
                content = result_json['candidates'][0]['content']['parts'][0]['text']
                st.session_state.report_result = content # 결과 박제
                log("🎉 [4단계] 리포트 생성 성공!", "success")
            else:
                log(f"⚠️ AI 응답은 왔으나 내용이 없습니다 (차단됨).\nRaw Response: {ai_res.text}", "warning")
        else:
            log(f"❌ AI 요청 실패 (HTTP {ai_res.status_code}):\n{ai_res.text}", "error")
            
    except Exception as e:
        log(f"❌ AI 통신 중 치명적 오류: {e}", "error")

# ==========================================
# UI 구성
# ==========================================
with st.sidebar:
    st.header("🔧 Emergency Debug Mode")
    
    # API 키 입력 (기본값 설정)
    user_key = st.text_input("Google API Key", value="AIzaSyCBSqIQBIYQbWtfQAxZ7D5mwCKFx-7VDJo", type="password")
    
    if st.button("🚨 진단 및 리포트 강제 실행", type="primary"):
        run_debug_process(user_key)

# 메인 화면
st.title("💠 Semi-Insight Hub (Debug Console)")

# 1. 저장된 로그 출력 (화면이 깜빡여도 유지됨)
st.subheader("📋 실행 로그")
if st.session_state.debug_logs:
    for level, msg in st.session_state.debug_logs:
        if level == "error": st.error(msg)
        elif level == "success": st.success(msg)
        elif level == "warning": st.warning(msg)
        else: st.info(msg)
else:
    st.info("사이드바의 '🚨 진단 및 리포트 강제 실행' 버튼을 눌러주세요.")

# 2. 결과 리포트 출력 (성공 시에만 표시)
if st.session_state.report_result:
    st.divider()
    st.subheader("📑 생성된 리포트")
    st.markdown(f"""
    <div style="background:white; padding:20px; border-radius:10px; border:1px solid #ddd;">
        {st.session_state.report_result}
    </div>
    """, unsafe_allow_html=True)
