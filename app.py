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
st.set_page_config(layout="wide", page_title="Semi Insight", page_icon="◆")

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

# ── 테마별 토큰 (apple.md 색상 스펙 기반, hex 고정값) ──────────
def get_theme():
    if st.session_state.dark_mode:
        return {
            "bg":           "#000000",
            "surface":      "#1D1D1F",
            "surface2":     "#2A2A2C",
            "border":       "#2C2C2E",
            "border2":      "#3A3A3C",
            "text":         "#FFFFFF",
            "text2":        "#CCCCCC",
            "muted":        "#8E8E93",
            "accent":       "#2997FF",
            "accent_soft":  "#12283B",
            "badge_bg":     "#12283B",
            "badge_fg":     "#2997FF",
            "shadow":       "0 12px 32px rgba(0,0,0,0.6)",
        }
    else:
        return {
            "bg":           "#F5F5F7",
            "surface":      "#FFFFFF",
            "surface2":     "#FAFAFC",
            "border":       "#F0F0F0",
            "border2":      "#E0E0E0",
            "text":         "#1D1D1F",
            "text2":        "#333333",
            "muted":        "#7A7A7A",
            "accent":       "#0066CC",
            "accent_soft":  "#EAF3FC",
            "badge_bg":     "#EAF3FC",
            "badge_fg":     "#0066CC",
            "shadow":       "0 12px 32px rgba(0,0,0,0.10)",
        }

T = get_theme()

# ── CSS 주입 ─────────────────────────────────────────────────
# {{ }} 이스케이프 없이 .format()으로 hex 값 주입 → 파싱 오류 원천 차단
# 폰트: apple.md가 명시한 SF Pro 대체 서체(Inter)를 그대로 사용
_FONT = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">'

_CSS = """
<style>
html, body, [class*="css"], .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.block-container {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}
/* [수정] 위 전역 규칙이 Streamlit 내장 아이콘(Material Symbols 리거처 폰트)의
   font-family까지 덮어써서 "expand_more"/"keyboard_arrow_down" 같은 리터럴
   텍스트가 아이콘 대신 노출되고 라벨과 겹치는 문제 → 아이콘 요소만 원래 폰트로 복원 */
[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded' !important;
    font-size: 18px !important;
}
.stApp, [data-testid="stAppViewContainer"] { background-color: BG !important; }
.block-container { background-color: BG !important; padding-top: 24px !important; padding-bottom: 64px !important; max-width: 900px !important; }
[data-testid="stHeader"] { background-color: transparent !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stRadio label, .stCheckbox label, p, span, div, li { color: TEXT !important; }
label[data-testid="stWidgetLabel"] { color: MUTED !important; font-size: 12px !important; font-weight: 400; }
* { box-sizing: border-box; }
div.stButton > button {
    font-family: 'Inter', sans-serif !important; font-size: 14px !important;
    font-weight: 600 !important; letter-spacing: -0.01em;
    border-radius: 999px !important; padding: 9px 20px !important;
    border: 1px solid BORDER2 !important; background-color: transparent !important;
    color: ACCENT !important; transition: transform 0.15s ease, background-color 0.15s ease, opacity 0.15s ease !important;
    box-shadow: none !important;
}
div.stButton > button:hover { background-color: ACCENT_SOFT !important; border-color: ACCENT !important; }
div.stButton > button:active { transform: scale(0.96) !important; }
div.stButton > button[kind="primary"] {
    background-color: ACCENT !important; color: #FFFFFF !important; border-color: ACCENT !important;
    font-weight: 600 !important; padding: 11px 26px !important;
}
div.stButton > button[kind="primary"]:hover { opacity: 0.88 !important; }
div.stButton > button[kind="primary"]:active { transform: scale(0.96) !important; }
div.stButton > button:disabled { opacity: 0.35 !important; transform: none !important; }
button[data-testid="stPopoverButton"] {
    font-family: 'Inter', sans-serif !important; font-size: 14px !important; font-weight: 600 !important;
    border-radius: 999px !important; padding: 9px 20px !important;
    border: 1px solid BORDER2 !important; background-color: SURFACE !important;
    color: TEXT !important; transition: transform 0.15s ease, background-color 0.15s ease !important;
    box-shadow: none !important; white-space: nowrap !important;
}
button[data-testid="stPopoverButton"]:hover { background-color: SURFACE2 !important; border-color: ACCENT !important; }
button[data-testid="stPopoverButton"]:active { transform: scale(0.97) !important; }
.stTextInput input, .stTextArea textarea {
    font-family: 'Inter', sans-serif !important; font-size: 15px !important;
    background-color: SURFACE2 !important; color: TEXT !important;
    border: 1px solid BORDER2 !important; border-radius: 999px !important; padding: 10px 18px !important;
    caret-color: ACCENT; transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.stTextArea textarea { border-radius: 16px !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: ACCENT !important; box-shadow: 0 0 0 3px ACCENT_SOFT !important; }
[data-testid="stExpander"] {
    background-color: SURFACE !important; border: 1px solid BORDER2 !important; border-radius: 18px !important;
    overflow: hidden; transition: box-shadow 0.25s ease, transform 0.25s ease; margin-bottom: 10px;
}
[data-testid="stExpander"]:hover { box-shadow: SHADOW; transform: translateY(-2px); }
[data-testid="stExpander"] summary {
    font-size: 15px !important; font-weight: 600 !important; color: TEXT !important;
    background-color: transparent !important; padding: 4px 2px !important;
}
[data-testid="stPopoverBody"], div[data-testid="stPopover"] > div {
    border-radius: 18px !important; border: 1px solid BORDER2 !important; background-color: SURFACE !important;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: SURFACE !important; border: 1px solid BORDER2 !important; border-radius: 18px !important;
}
[data-testid="stAlert"] {
    background-color: SURFACE2 !important; border: none !important; border-radius: 14px !important;
    font-size: 14px !important; color: TEXT2 !important; padding: 12px 16px !important;
}
[data-testid="stCheckbox"] label:has(input:checked) > div:first-of-type { background-color: ACCENT !important; border-color: ACCENT !important; }
[data-testid="stCheckbox"] label > div:first-of-type { transition: background-color 0.2s ease, border-color 0.2s ease; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: BORDER2; border-radius: 999px; }
@keyframes si-fade-up { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
/* ── 상단 바 ─────────────────────────────────────────── */
.si-topbar { display: flex; align-items: center; justify-content: space-between; padding: 4px 0 28px 0; }
.si-brand { display: flex; align-items: center; gap: 9px; }
.si-brand-mark {
    width: 26px; height: 26px; border-radius: 8px; background: ACCENT; color: #FFFFFF;
    display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0;
}
.si-brand-text { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; color: TEXT !important; }
/* ── 상태 배지 ───────────────────────────────────────── */
.si-badge {
    display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600;
    letter-spacing: 0; padding: 5px 10px; border-radius: 999px; background: BADGE_BG; color: BADGE_FG !important;
}
.si-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; animation: si-pulse 1.8s ease-in-out infinite; }
@keyframes si-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
/* ── 히어로 ──────────────────────────────────────────── */
.si-hero {
    background: SURFACE; border: 1px solid BORDER2; border-radius: 24px;
    padding: 56px 40px; text-align: center; margin-bottom: 20px;
    animation: si-fade-up 0.5s ease both;
}
.si-eyebrow { font-size: 12px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: ACCENT !important; margin-bottom: 14px; }
.si-hero-title { font-size: 40px; font-weight: 600; letter-spacing: -0.02em; color: TEXT !important; margin: 0 0 12px 0; line-height: 1.1; }
.si-hero-tag { font-size: 17px; font-weight: 400; color: MUTED !important; margin: 0 0 28px 0; line-height: 1.5; }
.si-hero-meta { font-size: 13px; color: MUTED !important; margin-top: 18px; }
.si-hero-meta b { color: ACCENT !important; font-weight: 600; }
/* ── 섹션 라벨 ───────────────────────────────────────── */
.si-label { font-size: 13px; font-weight: 600; color: TEXT !important; letter-spacing: -0.01em; margin: 32px 0 14px 2px; }
/* ── 일별 토글 버튼 (월 expander 내부, 중첩 expander 대체) ──── */
[class*="st-key-daybtn-"] div.stButton > button {
    background-color: SURFACE !important; border: 1px solid BORDER2 !important; color: TEXT !important;
    font-weight: 600 !important; font-size: 14.5px !important; letter-spacing: 0;
    border-radius: 14px !important; padding: 12px 16px !important;
}
[class*="st-key-daybtn-"] div.stButton > button:hover { background-color: SURFACE2 !important; border-color: ACCENT !important; opacity: 1 !important; }
[class*="st-key-daybtn-"] div.stButton > button:active { transform: scale(0.99) !important; }
/* ── 리포트 카드 (구조 파싱 실패 시 폴백) ──────────────── */
.si-report-card {
    line-height: 1.75; font-size: 16px; font-family: 'Inter', sans-serif;
    color: TEXT; padding: 4px 2px 8px;
}
.si-report-card h2 {
    font-size: 21px; font-weight: 600; color: TEXT; letter-spacing: -0.015em;
    margin: 30px 0 12px; padding-bottom: 10px; border-bottom: 1px solid BORDER2;
}
.si-report-card h2:first-child { margin-top: 0; }
.si-report-card h3 { font-size: 16px; font-weight: 600; color: TEXT; margin: 18px 0 6px; }
.si-report-card p  { margin: 0 0 14px; color: TEXT2; }
.si-report-card a  {
    color: ACCENT !important; font-weight: 600; text-decoration: none;
    transition: opacity 0.15s ease;
}
.si-report-card a:hover { text-decoration: underline; opacity: 0.85; }
/* ── 리포트 4단 섹션 카드 ──────────────────────────────── */
.si-section { margin-bottom: 14px; }
.si-section:last-child { margin-bottom: 0; }
.si-section-head {
    display: flex; align-items: center; gap: 12px; padding: 16px 2px 12px;
    border-bottom: 1px solid BORDER2;
}
.si-section-num {
    flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%;
    background: ACCENT_SOFT; color: ACCENT !important; font-size: 12px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
}
.si-section-title { font-size: 17px; font-weight: 600; color: TEXT !important; letter-spacing: -0.015em; }
.si-section-body {
    line-height: 1.75; font-size: 15.5px; font-family: 'Inter', sans-serif;
    color: TEXT2; padding: 16px 2px 4px 38px;
}
.si-section-body h3 { font-size: 15.5px; font-weight: 600; color: TEXT !important; margin: 16px 0 6px; }
.si-section-body h3:first-child { margin-top: 0; }
.si-section-body p { margin: 0 0 14px; color: TEXT2; }
.si-section-body a {
    color: ACCENT !important; font-weight: 600; text-decoration: none;
    transition: opacity 0.15s ease;
}
.si-section-body a:hover { text-decoration: underline; opacity: 0.85; }
/* ── 참고 기사 리스트 ────────────────────────────────── */
.si-archive-ref {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin: 0 -12px;
    border-radius: 12px; font-size: 14px; color: TEXT !important;
    transition: background-color 0.15s ease, transform 0.15s ease;
}
.si-archive-ref:hover { background-color: SURFACE2; transform: translateX(2px); }
.si-archive-ref:hover .si-ref-title { color: ACCENT !important; }
.si-ref-source {
    flex-shrink: 0; font-size: 11px; font-weight: 600; color: MUTED !important;
    background: SURFACE2; border-radius: 999px; padding: 3px 9px; white-space: nowrap;
}
.si-ref-title { color: TEXT !important; transition: color 0.15s ease; }
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

def split_report_sections(report_html):
    """[추가] 리포트 HTML을 h2(##) 기준 4단으로 분리 → 단별 카드 렌더링에 사용.
    h2가 하나도 없으면 빈 리스트를 반환해 호출부가 폴백 렌더링으로 전환하게 한다."""
    soup = BeautifulSoup(report_html, 'html.parser')
    sections = []
    current = None
    for el in list(soup.contents):
        if getattr(el, 'name', None) == 'h2':
            if current is not None:
                sections.append(current)
            current = {'title': el.decode_contents(), 'body': []}
        elif current is not None:
            current['body'].append(str(el))
    if current is not None:
        sections.append(current)
    return sections

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
# 5. 메인 앱 UI (사이드바 없이 단일 컬럼)
# ==========================================
# [수정] 구버전 Streamlit 호환 폴리필: st.popover가 없으면 st.expander로 대체
if not hasattr(st, "popover"):
    st.popover = st.expander

# ── 상단 바: 로고 + 다크모드 + API Key 팝오버 + GitHub 상태 ──
top_l, top_r1, top_r2, top_r3 = st.columns([4.4, 1, 1.9, 1.6])
with top_l:
    st.markdown(
        "<div class='si-topbar'><div class='si-brand'>"
        "<div class='si-brand-mark'>◆</div>"
        "<div class='si-brand-text'>Semi Insight</div>"
        "</div></div>",
        unsafe_allow_html=True
    )
with top_r1:
    dark_toggled = st.toggle("🌙", value=st.session_state.dark_mode)
    if dark_toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggled
        st.rerun()
with top_r2:
    with st.popover("🔑 API Key", use_container_width=True):
        user_key = st.text_input("NVIDIA API Key", type="password",
                                  label_visibility="collapsed",
                                  placeholder="NVIDIA API Key를 입력하세요")
        if user_key:
            api_key = user_key
        elif "NVIDIA_API_KEY" in st.secrets:
            api_key = st.secrets["NVIDIA_API_KEY"]
with top_r3:
    if "GITHUB_TOKEN" in st.secrets:
        st.markdown(
            "<div style='text-align:right; padding-top:6px;'><span class='si-badge'>"
            "<span class='si-dot'></span>Synced</span></div>",
            unsafe_allow_html=True
        )

# ── 날짜 계산 ──────────────────────────────────────────
now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
if now_kst.hour < 6:
    target_date = (now_kst - timedelta(days=1)).date()
else:
    target_date = now_kst.date()
target_date_str = target_date.strftime('%Y-%m-%d')

history = st.session_state.daily_history
today_report = next((h for h in history if h['date'] == target_date_str), None)

# ── 히어로 ─────────────────────────────────────────────
hero_meta = f"Report Date · <b>{target_date}</b>"
if today_report:
    hero_meta += "  ·  <b>✓ 생성 완료</b>" + (" · AUTO" if today_report.get("auto_generated") else "")
else:
    next_run_dt = target_date if now_kst.hour < 6 else (target_date + timedelta(days=1))
    hero_meta += f"  ·  다음 자동 생성 <b>{next_run_dt} 06:00 KST</b>"

st.markdown(
    "<div class='si-hero'>"
    "<div class='si-eyebrow'>Semiconductor Intelligence</div>"
    "<div class='si-hero-title'>Daily Report</div>"
    "<p class='si-hero-tag'>매일 아침, 반도체 소재 산업의 핵심을 가장 먼저 확인하세요.</p>"
    f"<div class='si-hero-meta'>{hero_meta}</div>"
    "</div>",
    unsafe_allow_html=True
)

# ── 키워드 관리 + 새로고침 ─────────────────────────────
col_kw, col_refresh = st.columns([5, 1])
with col_kw:
    with st.popover("⚙️ 키워드 관리"):
        render_keyword_manager()
with col_refresh:
    if st.button("🔄", use_container_width=True, key="reload_history"):
        # GitHub에서 최신 히스토리 강제 재로드
        st.session_state.daily_history = load_daily_history_from_source()
        st.rerun()

# ── 리포트 생성 액션 ───────────────────────────────────
if not today_report:
    if not api_key:
        st.info("리포트를 생성하려면 우측 상단에서 NVIDIA API Key를 먼저 입력해주세요.")

    if st.button("리포트 생성하기", type="primary", disabled=not bool(api_key)):
        status_box = st.status("리포트 생성 중...", expanded=True)
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
    if st.button("리포트 다시 만들기", disabled=not bool(api_key)):
        status_box = st.status("재생성 중...", expanded=True)
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

def render_day_report(entry):
    # [수정] "##" 등 마크다운을 Streamlit 렌더러에 맡기면 div로 감싼 raw HTML
    # 블록 처리 방식과 충돌해 헤더가 스타일 없이 그대로 텍스트로 노출됨.
    # Python에서 먼저 완전한 HTML로 변환한 뒤 삽입한다.
    report_html = md.markdown(entry['report'])
    sections = split_report_sections(report_html)
    if sections:
        for i, sec in enumerate(sections, start=1):
            body_html = ''.join(sec['body']).strip()
            st.markdown(
                f"<div class='si-section'>"
                f"<div class='si-section-head'>"
                f"<span class='si-section-num'>{i:02d}</span>"
                f"<span class='si-section-title'>{sec['title']}</span>"
                f"</div>"
                f"<div class='si-section-body'>{body_html}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            f"<div class='si-report-card'>{report_html}</div>",
            unsafe_allow_html=True
        )
    st.markdown("<div class='si-label' style='font-size:12px; margin-top:8px;'>참고 기사</div>", unsafe_allow_html=True)
    for item in entry.get('articles', []):
        safe_link = sanitize_url(item.get('Link', '#'))
        clean_title = re.sub(r'<[^>]+>', '', item.get('Title', ''))
        source = re.sub(r'<[^>]+>', '', item.get('Source', ''))
        st.markdown(
            f"<a href='{safe_link}' target='_blank' class='si-archive-ref'>"
            f"<span class='si-ref-source'>{source}</span>"
            f"<span class='si-ref-title'>{clean_title}</span></a>",
            unsafe_allow_html=True
        )

# ── 아카이브 (월별 그룹핑, 기본 접힘 + 일별 클릭 펼침) ──────
# [수정] Streamlit은 expander를 expander 안에 중첩할 수 없어 월 단위는
# expander로, 일 단위는 session_state로 여닫는 토글 버튼으로 구현한다.
if history:
    st.markdown("<div class='si-label'>지난 리포트</div>", unsafe_allow_html=True)
    months = {}
    for entry in history:
        months.setdefault(entry['date'][:7], []).append(entry)

    for month_key, entries in months.items():
        y, m = month_key.split('-')
        month_has_today = any(e['date'] == target_date_str for e in entries)
        with st.expander(f"{y}년 {int(m)}월 · {len(entries)}건", expanded=month_has_today):
            for entry in entries:
                is_today = (entry['date'] == target_date_str)
                state_key = f"day_open_{entry['date']}"
                if state_key not in st.session_state:
                    st.session_state[state_key] = is_today
                opened = st.session_state[state_key]
                badge = " 🟢 오늘" if is_today else ""
                arrow = "▾" if opened else "▸"
                if st.button(f"{arrow}  {entry['date']}{badge}",
                             key=f"daybtn-{entry['date']}", use_container_width=True):
                    st.session_state[state_key] = not opened
                    st.rerun()
                if opened:
                    render_day_report(entry)
