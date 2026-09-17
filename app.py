import streamlit as st
import pandas as pd
import base64
import markdown as md
import requests
import urllib3
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time as dt_time, timezone
import json
import os
import re
import time
import logging
from github import Github
import concurrent.futures

# ==========================================
# 로깅 설정
# ==========================================
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# SSL 경고 무시 (Google News RSS 수집 전용)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 0. 페이지 설정
# ==========================================
st.set_page_config(layout="wide", page_title="Semi-Insight Terminal", page_icon="🖥️")

DAILY_REPORT = "Daily Report"
KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json'
MAX_HISTORY = 30   # 아카이브 최대 보관 수 (generate_report.py와 동일하게 유지)
NEWS_LIMIT = 40    # 기사 제목 40건은 입력 토큰 몇 천 개 수준 → 무료 티어에서도 여유 있음.
                    # 과거 응답 절단 문제의 실제 원인은 기사 수가 아니라 gemini-2.5의
                    # "thinking" 토큰이 출력 예산을 잠식한 것이었고 thinkingBudget=0으로 해결됨.

# [수정] api_key 전역 기본값 선언 → NameError 방지
api_key = ""

# ==========================================
# 다크모드 session_state 초기화
# ==========================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ── 테마별 토큰 (금융/리서치 터미널 팔레트, hex 고정값) ──────────
def get_theme():
    if st.session_state.dark_mode:
        return {
            "bg":           "#080B0A",
            "surface":      "#0F1412",
            "surface2":     "#141A17",
            "border":       "#1E2723",
            "border2":      "#2C3833",
            "text":         "#DCEFE4",
            "text2":        "#7C9A8B",
            "muted":        "#4B5F56",
            "accent":       "#2BE28A",
            "accent_soft":  "#0B2318",
            "badge_bg":     "#0B2318",
            "badge_fg":     "#2BE28A",
            "shadow":       "none",
        }
    else:
        return {
            "bg":           "#F1F0EA",
            "surface":      "#FFFFFF",
            "surface2":     "#F7F6F1",
            "border":       "#D9D6C9",
            "border2":      "#C4C0AF",
            "text":         "#121815",
            "text2":        "#5B6B62",
            "muted":        "#8B9089",
            "accent":       "#0E8F5D",
            "accent_soft":  "#E6F4EC",
            "badge_bg":     "#E6F4EC",
            "badge_fg":     "#0E8F5D",
            "shadow":       "none",
        }

T = get_theme()

# ── CSS 주입 ─────────────────────────────────────────────────
# {{ }} 이스케이프 없이 .format()으로 hex 값 주입 → 파싱 오류 원천 차단
_FONT = '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'

_CSS = """
<style>
html, body, [class*="css"], .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stSidebar"],
.block-container {
    font-family: 'JetBrains Mono', monospace !important;
}
.stApp, [data-testid="stAppViewContainer"] { background-color: BG !important; }
.block-container { background-color: BG !important; padding-top: 20px !important; padding-bottom: 48px !important; max-width: 1100px !important; }
section[data-testid="stSidebar"] > div:first-child { background-color: SURFACE !important; border-right: 1px solid BORDER !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stRadio label, .stCheckbox label, p, span, div, li { color: TEXT !important; }
label[data-testid="stWidgetLabel"] { color: TEXT2 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.06em; }
div.stButton > button {
    font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
    font-weight: 600 !important; letter-spacing: 0.04em; text-transform: uppercase;
    border-radius: 2px !important; padding: 6px 14px !important;
    border: 1px solid BORDER2 !important; background-color: transparent !important;
    color: TEXT2 !important; transition: all 0.12s ease !important; box-shadow: none !important;
}
div.stButton > button:hover { border-color: ACCENT !important; color: ACCENT !important; background-color: ACCENT_SOFT !important; }
div.stButton > button[kind="primary"] { background-color: ACCENT !important; color: BG !important; border-color: ACCENT !important; font-weight: 700 !important; }
div.stButton > button[kind="primary"]:hover { opacity: 0.85 !important; }
.stTextInput input, .stTextArea textarea {
    font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important;
    background-color: SURFACE2 !important; color: TEXT !important;
    border: 1px solid BORDER2 !important; border-radius: 2px !important; caret-color: ACCENT;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: ACCENT !important; box-shadow: 0 0 0 1px ACCENT !important; }
[data-testid="stExpander"] { background-color: SURFACE !important; border: 1px solid BORDER !important; border-radius: 2px !important; overflow: hidden; }
[data-testid="stExpander"] summary { font-size: 12px !important; font-weight: 500 !important; color: TEXT2 !important; background-color: SURFACE !important; }
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] { background-color: SURFACE !important; border: 1px solid BORDER !important; border-radius: 2px !important; }
[data-testid="stAlert"] { background-color: SURFACE2 !important; border: 1px solid BORDER2 !important; border-left: 3px solid ACCENT !important; border-radius: 2px !important; font-size: 13px !important; color: TEXT !important; }
[data-testid="stToggle"] label div[data-checked="true"] { background-color: ACCENT !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: BORDER2; border-radius: 0; }
/* ── 로고 / 프롬프트 ─────────────────────────────────── */
.si-logo { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid BORDER; }
.si-logo-mark {
    width: 30px; height: 30px; background: ACCENT; color: BG; border-radius: 2px;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 700; flex-shrink: 0;
}
.si-logo-text { font-size: 13px; font-weight: 700; letter-spacing: 0.02em; color: TEXT !important; text-transform: uppercase; }
.si-logo-sub  { font-size: 9px; color: MUTED !important; letter-spacing: 0.1em; text-transform: uppercase; }
.si-cursor { color: ACCENT; animation: si-blink 1.1s step-start infinite; }
@keyframes si-blink { 50% { opacity: 0; } }
/* ── 상태 배지 ───────────────────────────────────────── */
.si-badge {
    display: inline-flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase; padding: 3px 8px 3px 6px;
    border-radius: 2px; border: 1px solid BORDER2; background: BADGE_BG; color: BADGE_FG !important;
}
.si-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; animation: si-pulse 1.6s ease-in-out infinite; }
@keyframes si-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
/* ── 시스템 배너 ─────────────────────────────────────── */
.si-banner {
    display: flex; align-items: baseline; gap: 10px; background: SURFACE2; border: 1px solid BORDER;
    border-left: 3px solid ACCENT; border-radius: 2px; padding: 10px 15px; font-size: 12px;
    color: TEXT2 !important; margin-bottom: 18px;
}
.si-banner-tag { color: ACCENT !important; font-weight: 700; letter-spacing: 0.08em; flex-shrink: 0; }
/* ── 페이지 타이틀 (프롬프트 라인) ───────────────────── */
.si-page-title {
    font-size: 18px; font-weight: 700; letter-spacing: 0.02em; text-transform: uppercase;
    color: TEXT; margin: 0 0 18px 0; padding-bottom: 14px; border-bottom: 2px solid ACCENT;
}
.si-prompt { color: ACCENT !important; margin-right: 8px; }
/* ── 라벨 / 섹션 태그 ─────────────────────────────────── */
.si-label {
    font-size: 11px; font-weight: 700; color: TEXT2 !important; letter-spacing: 0.1em;
    text-transform: uppercase; padding-left: 10px; border-left: 3px solid ACCENT;
    margin: 22px 0 12px 0;
}
/* ── 리포트 카드 ─────────────────────────────────────── */
.si-report-card {
    background: SURFACE; border: 1px solid BORDER; border-radius: 3px;
    padding: 28px 30px; line-height: 1.8; font-size: 14.5px; font-family: 'IBM Plex Sans', sans-serif;
    color: TEXT; box-shadow: SHADOW; margin-bottom: 16px;
}
.si-report-card h2 {
    font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: ACCENT;
    letter-spacing: 0.03em; margin: 26px 0 10px; padding: 6px 0 6px 10px; border-left: 3px solid ACCENT;
    background: ACCENT_SOFT;
}
.si-report-card h2:first-child { margin-top: 0; }
.si-report-card h3 { font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: TEXT2; margin: 16px 0 6px; }
.si-report-card p  { margin: 0 0 12px; }
.si-report-card a  { color: ACCENT !important; font-weight: 700; text-decoration: none; border-bottom: 1px dotted ACCENT; }
/* ── 아카이브 참고 기사 ───────────────────────────────── */
.si-archive-ref {
    display: flex; align-items: baseline; gap: 8px; padding: 6px 0; border-bottom: 1px solid BORDER;
    font-size: 12.5px; color: TEXT2 !important; font-family: 'JetBrains Mono', monospace;
}
.si-archive-ref:hover { color: ACCENT !important; }
.si-archive-ref:hover .si-ref-title { color: ACCENT !important; }
.si-archive-ref:last-child { border-bottom: none; }
.si-ref-chevron { color: ACCENT !important; flex-shrink: 0; }
.si-ref-source { color: MUTED !important; flex-shrink: 0; }
.si-ref-title { color: TEXT !important; font-family: 'IBM Plex Sans', sans-serif; }
a  { text-decoration: none; }
hr { border-color: BORDER !important; margin: 12px 0 !important; }
</style>
"""

def _inject_css(t):
    css = _CSS
    # [수정] BADGE_BG/BADGE_FG는 "BG" 치환보다 먼저 처리해야 함 - "BG"를 먼저
    # 치환하면 "BADGE_BG"의 접미사가 깨져서 뒤의 BADGE_BG 규칙이 매칭되지 않음
    css = css.replace("BADGE_BG",    t["badge_bg"])
    css = css.replace("BADGE_FG",    t["badge_fg"])
    css = css.replace("BG",          t["bg"])
    css = css.replace("SURFACE2",    t["surface2"])
    css = css.replace("SURFACE",     t["surface"])
    css = css.replace("BORDER2",     t["border2"])
    css = css.replace("BORDER",      t["border"])
    css = css.replace("TEXT2",       t["text2"])
    css = css.replace("TEXT",        t["text"])
    css = css.replace("ACCENT_SOFT", t["accent_soft"])
    css = css.replace("ACCENT",      t["accent"])
    css = css.replace("MUTED",       t["muted"])
    css = css.replace("SHADOW",      t["shadow"])
    st.markdown(_FONT + css, unsafe_allow_html=True)

_inject_css(T)

# ==========================================
# 1. 데이터 관리 (GitHub Auto-Sync)
# ==========================================
def sync_to_github(filename, content_data):
    if "GITHUB_TOKEN" not in st.secrets or "REPO_NAME" not in st.secrets:
        return False
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(st.secrets["REPO_NAME"])
        content_str = json.dumps(content_data, ensure_ascii=False, indent=4, default=str)
        try:
            contents = repo.get_contents(filename)
            repo.update_file(contents.path, f"Update {filename}", content_str, contents.sha)
        except Exception:
            repo.create_file(filename, f"Create {filename}", content_str)
        return True
    except Exception as e:
        logger.warning(f"GitHub sync error [{filename}]: {e}")
        return False

def load_keywords():
    data = {DAILY_REPORT: []}
    if "GITHUB_TOKEN" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(KEYWORD_FILE)
            loaded = json.loads(contents.decoded_content.decode("utf-8"))
            if DAILY_REPORT in loaded:
                data[DAILY_REPORT] = loaded[DAILY_REPORT]
            return data
        except Exception as e:
            logger.warning(f"GitHub keyword load error: {e}")
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if DAILY_REPORT in loaded:
                data[DAILY_REPORT] = loaded[DAILY_REPORT]
        except Exception as e:
            logger.warning(f"Local keyword load error: {e}")
    if not data.get(DAILY_REPORT):
        data[DAILY_REPORT] = ["반도체", "삼성전자", "SK하이닉스"]
    return data

def save_keywords(data):
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.warning(f"Local keyword save error: {e}")
    sync_to_github(KEYWORD_FILE, data)

def load_daily_history_from_source():
    if "GITHUB_TOKEN" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(HISTORY_FILE)
            if contents.encoding == "none":
                # Contents API는 1MB 초과 파일에 inline content를 주지 않음(encoding="none").
                # 이 경우 decoded_content가 예외를 던지므로 Git Blob API로 원본을 다시 조회한다.
                blob = repo.get_git_blob(contents.sha)
                raw = base64.b64decode(blob.content)
                return json.loads(raw.decode("utf-8"))
            return json.loads(contents.decoded_content.decode("utf-8"))
        except Exception as e:
            logger.warning(f"GitHub history load error: {e}")
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Local history load error: {e}")
    return []

# ==========================================
# Session State 초기화
# ==========================================
if 'keywords' not in st.session_state:
    st.session_state.keywords = load_keywords()
if 'daily_history' not in st.session_state:
    st.session_state.daily_history = load_daily_history_from_source()

def save_daily_history(new_report_data):
    current_history = [h for h in st.session_state.daily_history if h['date'] != new_report_data['date']]
    current_history.insert(0, new_report_data)
    current_history = current_history[:MAX_HISTORY]  # 무제한 증가 방지 (GitHub Contents API 1MB 제한 대비)
    st.session_state.daily_history = current_history
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=4, default=str)
    except Exception as e:
        logger.warning(f"Local history save error: {e}")
    sync_to_github(HISTORY_FILE, current_history)

# ==========================================
# 2. 뉴스 수집
# ==========================================
def _fetch_keyword_news(kw, per_kw_limit, days, strict_time, start_dt, end_dt):
    """단일 키워드 RSS를 1회만 조회하여 (시간필터 통과 목록, 원본 전체 목록)을 함께 반환.
    시간필터 결과가 부족할 때 재크롤링 없이 원본 목록을 그대로 폴백에 사용한다."""
    url = (
        f"https://news.google.com/rss/search?"
        f"q={quote(kw)}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
    )
    filtered, raw = [], []
    try:
        res = requests.get(url, timeout=5, verify=False)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'xml')
        for item in soup.find_all('item'):
            title = item.title.text if item.title else ""
            if not title:
                continue
            link = item.link.text if item.link else ""
            date_raw = item.pubDate.text if item.pubDate else ""
            src = item.source.text if item.source else "Google News"

            is_valid = True
            pub_date_str_val = None
            if strict_time and start_dt and end_dt:
                try:
                    pub_date = datetime.strptime(date_raw, "%a, %d %b %Y %H:%M:%S %Z")
                    pub_date_kst = pub_date + timedelta(hours=9)
                    pub_date_str_val = pub_date_kst.strftime("%Y-%m-%d %H:%M:%S")
                    if not (start_dt <= pub_date_kst <= end_dt):
                        is_valid = False
                except Exception:
                    is_valid = True  # 날짜 파싱 실패 시 포함

            entry = {'Title': title, 'Link': link, 'Date': date_raw, 'Source': src, 'ParsedDate': pub_date_str_val}
            if len(raw) < per_kw_limit:
                raw.append(entry)
            if is_valid and len(filtered) < per_kw_limit:
                filtered.append(entry)
            if len(filtered) >= per_kw_limit and len(raw) >= per_kw_limit:
                break
    except Exception as e:
        logger.warning(f"News fetch error [kw={kw}]: {e}")
    return filtered, raw


def fetch_news(keywords, days=1, limit=NEWS_LIMIT, strict_time=False, start_dt=None, end_dt=None):
    """
    [수정] strict_time 조건 분리:
    - strict_time=True  → 전달받은 start_dt/end_dt 사용, 결과 부족 시 이미 수집한 뉴스로 자동 폴백(재크롤링 없음)
    - strict_time=False → 현재 시각 기준 기본 window 계산
    키워드별 요청은 병렬로 실행해 수집 시간을 단축한다.
    """
    if not strict_time:
        # strict_time=False 일 때만 기본 window 계산 (전달 인자 무시하지 않음)
        now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
        end_dt = datetime(now_kst.year, now_kst.month, now_kst.day, 6, 0, 0)
        if now_kst.hour < 6:
            end_dt -= timedelta(days=1)
        start_dt = end_dt - timedelta(hours=18)

    # [수정] per_kw_limit: 전체 limit을 키워드 수로 동적 배분
    per_kw_limit = max(3, limit // max(len(keywords), 1))

    filtered_all, raw_all = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(keywords))) as executor:
        futures = [
            executor.submit(_fetch_keyword_news, kw, per_kw_limit, days, strict_time, start_dt, end_dt)
            for kw in keywords
        ]
        for future in concurrent.futures.as_completed(futures):
            filtered, raw = future.result()
            filtered_all.extend(filtered)
            raw_all.extend(raw)

    def _to_df(items, sort_by_date):
        d = pd.DataFrame(items)
        if not d.empty:
            d = d.drop_duplicates(subset=['Title'])
            if sort_by_date:
                d['TempDate'] = pd.to_datetime(d['ParsedDate'], errors='coerce')
                d = d.sort_values(by='TempDate', ascending=False)
                d = d.drop(columns=['TempDate'])
        return d

    df = _to_df(filtered_all, sort_by_date=strict_time)
    if strict_time and len(df) < 5:
        logger.warning(f"시간 필터 결과 {len(df)}건 → 폴백: 이미 수집된 뉴스 재사용")
        df = _to_df(raw_all, sort_by_date=False)

    if df.empty:
        return []
    return df.head(limit).to_dict('records')

# ==========================================
# 3. AI 리포트 생성 (NVIDIA NIM, OpenAI 호환 API)
# ==========================================
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "qwen/qwen2.5-72b-instruct"

def sanitize_url(url_str):
    """[추가] URL scheme 검증 → XSS 방지"""
    try:
        parsed = urlparse(url_str)
        if parsed.scheme in ("http", "https"):
            return url_str
    except Exception:
        pass
    return "#"

def inject_links_to_report(report_text, news_data):
    def replace_match(match):
        try:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(news_data):
                link = sanitize_url(news_data[idx]['Link'])
                accent = T['accent']
                return (
                    f"<a href='{link}' target='_blank' "
                    f"style='color:{accent};font-weight:600;text-decoration:underline;'>[{match.group(1)}]</a>"
                )
        except Exception:
            pass
        return match.group(0)
    return re.sub(r'\[(\d+)\]', replace_match, report_text)

def generate_report_with_citations(api_key, news_data):
    news_context = ""
    for i, item in enumerate(news_data):
        clean_title = re.sub(r'<[^>]+>', '', item['Title'])
        news_context += f"[{i+1}] {clean_title} (Source: {item['Source']})\n"

    prompt = f"""당신은 글로벌 반도체 소재 전략 수석 애널리스트입니다.
아래 뉴스만 근거로, 바쁜 임원이 핵심을 즉시 파악할 [일일 반도체 기술·소재 브리핑]을 작성하세요.

[절대 금지] "오늘날 반도체 산업은" 같은 상투적 도입 문장 금지 - 바로 사실로 시작. 제목 나열/번역 금지. 뉴스에 없는 내용 추측 금지.
[작성 원칙] 1) 두괄식: 각 섹션 첫 문장에 결론 제시 후 근거. 2) 서술형, 군더더기 없이 간결하게. 3) 모든 주장에 뉴스 번호 [1][2] 인용.

[뉴스 데이터]
{news_context}

[보고서 구조 - Markdown]
## 📌 핵심 요약 (Executive Brief)
가장 중요한 판단 3~4개를 각 1문장, 결론부터. 인용 번호 포함.

## 🚨 Key Issues & Deep Dive (핵심 이슈 심층 분석)
이슈 2~3가지, 소제목마다 결론 먼저 제시 후 서술형으로 상세 분석. 인용 번호 필수.

## 🕸️ Supply Chain & Tech Trends (공급망 및 기술 동향)
소재·소부장 기술 변화와 공급망 핵심만 결론 우선 서술.

## 💡 Analyst's View (시사점)
시사점과 향후 관전 포인트를 결론부터 서술.
"""

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    data = {
        "model": NVIDIA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 2048,
    }

    # [수정] 429 응답 시 Exponential Backoff 적용
    last_error = "응답 없음"
    retry_wait = 1
    for attempt in range(4):
        try:
            response = requests.post(NVIDIA_API_URL, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                res_json = response.json()
                choices = res_json.get('choices')
                if choices:
                    raw_text = choices[0]['message']['content']
                    if len(raw_text) < 300 or "##" not in raw_text:
                        # 응답이 비정상적으로 짧거나(조기 절단) 구조가 없으면 폐기하고 재시도
                        logger.warning(f"리포트가 비정상적으로 짧음 ({len(raw_text)} chars) → 재시도")
                        last_error = f"응답이 비정상적으로 짧음 ({len(raw_text)} chars)"
                        continue
                    return True, inject_links_to_report(raw_text, news_data)
                last_error = f"200 응답이지만 choices 없음: {response.text[:300]}"
                break
            elif response.status_code == 429:
                logger.warning(f"Rate limit hit, retrying in {retry_wait}s...")
                last_error = "429 Rate limit"
                time.sleep(retry_wait)
                retry_wait *= 2  # Exponential backoff
                continue
            else:
                last_error = f"{response.status_code} {response.text[:300]}"
                logger.warning(f"NVIDIA API 오류: {last_error}")
                break
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Report generation error: {e}")
            break

    return False, f"AI 분석 실패 (NVIDIA API): {last_error}"

# ==========================================
# 4. 키워드 관리 UI
# ==========================================
def render_keyword_manager():
    c1, c2 = st.columns([3, 1])

    new_kw = c1.text_input(
        "수집 키워드 추가",
        placeholder="예: HBM, 패키징",
        label_visibility="collapsed",
        key="kw_input"
    )
    if c2.button("추가", use_container_width=True, key="kw_add"):
        if new_kw and new_kw not in st.session_state.keywords[DAILY_REPORT]:
            st.session_state.keywords[DAILY_REPORT].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()

    curr_kws = st.session_state.keywords.get(DAILY_REPORT, [])
    if curr_kws:
        st.write("")
        num_cols = min(len(curr_kws), 8)
        cols = st.columns(num_cols)
        for i, kw in enumerate(curr_kws):
            if cols[i % num_cols].button(f"{kw} ×", key=f"kw_del_{i}_{kw}"):
                st.session_state.keywords[DAILY_REPORT].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

# ==========================================
# 5. 메인 앱 UI
# ==========================================
# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    # 로고
    st.markdown(f"""
    <div class="si-logo">
        <div class="si-logo-mark">$</div>
        <div>
            <div class="si-logo-text">Semi-Insight<span class="si-cursor">_</span></div>
            <div class="si-logo-sub">Semiconductor Intel Terminal</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 다크모드 토글 (Streamlit native → session_state 기반)
    dark_toggled = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark_toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggled
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    with st.expander("🔐 API Key"):
        user_key = st.text_input("NVIDIA API Key", type="password",
                                  label_visibility="collapsed",
                                  placeholder="NVIDIA API Key를 입력하세요")
        if user_key:
            api_key = user_key
        elif "NVIDIA_API_KEY" in st.secrets:
            api_key = st.secrets["NVIDIA_API_KEY"]

    if "GITHUB_TOKEN" in st.secrets:
        st.markdown(
            "<div style='margin-top:10px'><span class='si-badge'>"
            "<span class='si-dot'></span>GitHub Sync</span></div>",
            unsafe_allow_html=True
        )

# ── 메인 콘텐츠 (Daily Report) ──────────────────────────────
st.markdown(
    f"<div class='si-page-title'>"
    f"<span class='si-prompt'>$</span>DAILY_REPORT<span class='si-cursor'>_</span></div>",
    unsafe_allow_html=True
)

# ── 날짜 계산 ──────────────────────────────────────────
now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
if now_kst.hour < 6:
    target_date = (now_kst - timedelta(days=1)).date()
else:
    target_date = now_kst.date()
target_date_str = target_date.strftime('%Y-%m-%d')

# ── 배너 ───────────────────────────────────────────────
st.markdown(
    "<div class='si-banner'>"
    "<span class='si-banner-tag'>[SYSTEM]</span>"
    "매일 06:00 KST GitHub Actions가 자동으로 리포트를 생성합니다. "
    "아래 버튼으로 수동 생성도 가능합니다."
    "</div>",
    unsafe_allow_html=True
)

# ── 날짜 표시 + GitHub 최신화 버튼 ────────────────────
col_date, col_refresh = st.columns([4, 1])
with col_date:
    st.markdown(
        f"<div style='font-size:12px; color:{T['muted']}; padding-top:6px; text-transform:uppercase; letter-spacing:0.05em;'>"
        f"DATE &nbsp;·&nbsp; <b style='color:{T['accent']}'>{target_date}</b></div>",
        unsafe_allow_html=True
    )
with col_refresh:
    if st.button("↻ 새로고침", use_container_width=True, key="reload_history"):
        # GitHub에서 최신 히스토리 강제 재로드
        st.session_state.daily_history = load_daily_history_from_source()
        st.rerun()

# ── 키워드 관리 ────────────────────────────────────────
with st.expander("⚙️ 키워드 관리", expanded=False):
    render_keyword_manager()

# ── 오늘 리포트 상태 확인 ──────────────────────────────
history = st.session_state.daily_history
today_report = next((h for h in history if h['date'] == target_date_str), None)

if not today_report:
    # GitHub Actions가 아직 실행 전이거나 실패한 경우
    next_run_dt = target_date if now_kst.hour < 6 else (target_date + timedelta(days=1))
    st.info(
        f"📢 오늘({target_date_str}) 리포트가 아직 없습니다. "
        f"다음 자동 생성: **{next_run_dt} 06:00 KST**"
    )

    # 수동 생성 버튼
    if st.button("🚀 지금 바로 리포트 생성", type="primary", disabled=not bool(api_key)):
        if not api_key:
            st.warning("API Key를 먼저 입력해주세요.")
        else:
            status_box = st.status("🚀 리포트 생성 중...", expanded=True)
            end_dt   = datetime.combine(target_date, dt_time(6, 0))
            start_dt = end_dt - timedelta(hours=18)
            daily_kws = st.session_state.keywords[DAILY_REPORT]

            status_box.write(f"📡 뉴스 수집 중 ({NEWS_LIMIT}건)...")
            # fetch_news 내부에서 시간필터 결과가 부족하면 재크롤링 없이 자동 폴백 처리
            news_items = fetch_news(
                daily_kws, days=2, limit=NEWS_LIMIT,
                strict_time=True, start_dt=start_dt, end_dt=end_dt
            )

            if not news_items:
                status_box.update(label="❌ 수집된 뉴스가 없습니다.", state="error")
            else:
                status_box.write(f"🧠 AI 심층 분석 중... ({len(news_items)}건)")
                success, result = generate_report_with_citations(api_key, news_items)
                if success:
                    save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                    status_box.write("💾 GitHub에 저장 중...")
                    save_daily_history(save_data)
                    status_box.update(label="🎉 완료!", state="complete")
                    st.rerun()
                else:
                    status_box.update(label="⚠️ AI 분석 실패", state="error")
                    st.error(result)
else:
    # 자동 또는 수동으로 생성된 리포트 존재
    auto_tag = ""
    if today_report.get("auto_generated"):
        auto_tag = f" &nbsp;<span class='si-badge'>AUTO</span>"
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:12px;'>"
        f"<span style='color:{T['accent']};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;'>"
        f"● 리포트 생성 완료</span>"
        f"{auto_tag}</div>",
        unsafe_allow_html=True
    )

    # 수동 재생성 버튼
    if st.button("🔄 리포트 다시 만들기", disabled=not bool(api_key)):
        status_box = st.status("🚀 재생성 중...", expanded=True)
        daily_kws  = st.session_state.keywords[DAILY_REPORT]
        news_items = fetch_news(daily_kws, days=2, limit=NEWS_LIMIT, strict_time=False)
        if news_items:
            status_box.write("🧠 AI 분석 중...")
            success, result = generate_report_with_citations(api_key, news_items)
            if success:
                save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
                save_daily_history(save_data)
                status_box.update(label="🎉 완료!", state="complete")
                st.rerun()
            else:
                status_box.update(label="⚠️ 실패", state="error")
                st.error(result)

# ── 아카이브 ───────────────────────────────────────────
if history:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='si-label'>REPORT_ARCHIVE</div>", unsafe_allow_html=True)
    for entry in history:
        is_today = (entry['date'] == target_date_str)
        with st.expander(
            f"{'● ' if is_today else '  '}{entry['date']} · DAILY_REPORT",
            expanded=is_today
        ):
            # [수정] "##" 등 마크다운을 Streamlit 렌더러에 맡기면 div로 감싼 raw HTML
            # 블록 처리 방식과 충돌해 헤더가 스타일 없이 그대로 텍스트로 노출됨.
            # Python에서 먼저 완전한 HTML로 변환한 뒤 삽입한다.
            report_html = md.markdown(entry['report'])
            st.markdown(
                f"<div class='si-report-card'>{report_html}</div>",
                unsafe_allow_html=True
            )
            st.markdown("<div class='si-label' style='margin-top:18px;'>REFERENCES</div>", unsafe_allow_html=True)
            for item in entry.get('articles', []):
                safe_link = sanitize_url(item.get('Link', '#'))
                clean_title = re.sub(r'<[^>]+>', '', item.get('Title', ''))
                source = re.sub(r'<[^>]+>', '', item.get('Source', ''))
                st.markdown(
                    f"<a href='{safe_link}' target='_blank' class='si-archive-ref'>"
                    f"<span class='si-ref-chevron'>&gt;</span>"
                    f"<span class='si-ref-source'>[{source}]</span>"
                    f"<span class='si-ref-title'>{clean_title}</span></a>",
                    unsafe_allow_html=True
                )
