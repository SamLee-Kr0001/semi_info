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
NEWS_LIMIT = 160   # 기사 제목 160건도 입력 토큰 2만 개 안팎 수준 → Gemini 컨텍스트 윈도우에 여유 있음.
                    # 과거 응답 절단 문제의 실제 원인은 기사 수가 아니라 gemini-2.5의
                    # "thinking" 토큰이 출력 예산을 잠식한 것이었고 thinkingBudget=0으로 해결됨.

# [수정] api_key 전역 기본값 선언 → NameError 방지
api_key = ""

# ==========================================
# 화면 테마 (taste-skill deal: lunar-grey-bronze / Manrope + JetBrains Mono)
# ==========================================
# 근흑(near-black) 바탕에 브론즈 포인트: 웨이퍼·구리 배선 같은 반도체 소재의
# 금속성을 한 가지 색으로만 받는다. 인터페이스는 90% 이상 무채색으로 둔다.
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

def get_theme():
    if st.session_state.dark_mode:
        return {
            "bg":          "#111111",
            "surface":     "#1A1A1A",
            "surface2":    "#232323",
            "line":        "rgba(242,242,242,0.12)",
            "line2":       "rgba(242,242,242,0.22)",
            "text":        "#F2F2F2",
            "text2":       "#D4D4D4",
            "muted":       "#8F8F8F",
            "accent":      "#A08672",
            "accent_ink":  "#111111",
            "accent_soft": "rgba(160,134,114,0.16)",
            "shadow":      "0 18px 40px rgba(0,0,0,0.45)",
        }
    return {
        "bg":          "#F3F1EE",
        "surface":     "#FFFFFF",
        "surface2":    "#E9E6E2",
        "line":        "rgba(22,21,20,0.12)",
        "line2":       "rgba(22,21,20,0.24)",
        "text":        "#161514",
        "text2":       "#2E2B28",
        "muted":       "#6B6560",
        "accent":      "#7A5F4B",
        "accent_ink":  "#FFFFFF",
        "accent_soft": "rgba(122,95,75,0.12)",
        "shadow":      "0 18px 40px rgba(22,21,20,0.10)",
    }

T = get_theme()

# Manrope(라틴·숫자) + Pretendard(한글) + JetBrains Mono(날짜·수치)
_FONT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400..700'
    '&family=JetBrains+Mono:wght@400..500&display=swap" rel="stylesheet">'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/'
    'dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
)

_CSS = """
<style>
:root {
  --bg: {bg}; --surface: {surface}; --surface2: {surface2};
  --line: {line}; --line2: {line2};
  --ink: {text}; --ink2: {text2}; --muted: {muted};
  --accent: {accent}; --accent-ink: {accent_ink}; --accent-soft: {accent_soft};
  --shadow: {shadow};
  --f-text: "Manrope", "Pretendard Variable", Pretendard, system-ui, sans-serif;
  --f-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  --r-lg: 20px; --r-md: 12px; --r-sm: 8px;
  --ease: cubic-bezier(.2,.7,.2,1);
}
html, body, .stApp, [data-testid="stAppViewContainer"], .block-container,
.stMarkdown, .stMarkdown p, button, input, textarea {
  font-family: var(--f-text) !important;
}
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; font-size: 18px !important; }
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--ink); }
[data-testid="stHeader"] { background: transparent !important; }
.stAppDeployButton, [data-testid="stDecoration"] { display: none !important; }
.block-container { max-width: 1360px !important; padding: 24px 40px 96px !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li { color: var(--ink2); }
label[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] { color: var(--muted) !important; font-size: 13px !important; }
* { box-sizing: border-box; }
::selection { background: var(--accent); color: var(--accent-ink); }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 999px; }
a { color: var(--accent); text-decoration: none; }
:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }

/* ── 버튼: 한 가지 모양, 채움은 주 동작 하나만 ─────────────── */
div.stButton > button, button[data-testid="stPopoverButton"], [data-testid="stPopover"] > div > button {
  font-size: 14px !important; font-weight: 500 !important; letter-spacing: -0.005em;
  min-height: 40px; border-radius: 999px !important; padding: 8px 18px !important;
  background: transparent !important; color: var(--ink) !important;
  border: 1px solid var(--line2) !important; box-shadow: none !important;
  transition: transform .18s var(--ease), background-color .18s var(--ease), border-color .18s var(--ease) !important;
}
div.stButton > button:hover, button[data-testid="stPopoverButton"]:hover {
  background: var(--surface2) !important; border-color: var(--ink) !important; transform: translateY(-1px);
}
div.stButton > button:active, button[data-testid="stPopoverButton"]:active { transform: translateY(0) scale(.97) !important; }
div.stButton > button[kind="primary"] {
  background: var(--accent) !important; color: var(--accent-ink) !important; border-color: var(--accent) !important;
  font-weight: 600 !important; padding: 10px 22px !important;
}
div.stButton > button[kind="primary"] p { color: var(--accent-ink) !important; }
div.stButton > button[kind="primary"]:hover { filter: brightness(1.08); }
div.stButton > button:disabled { opacity: .35 !important; transform: none !important; }
div.stButton > button p, button[data-testid="stPopoverButton"] p { color: inherit !important; font-size: 14px !important; }
[data-testid="stPopoverBody"] { background: var(--surface) !important; border: 1px solid var(--line2) !important; border-radius: var(--r-md) !important; }
.stTextInput input {
  font-size: 15px !important; background: var(--surface2) !important; color: var(--ink) !important;
  border: 1px solid var(--line2) !important; border-radius: var(--r-sm) !important; min-height: 40px;
}
.stTextInput input:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-soft) !important; }
[data-testid="stToggle"] label p, .stCheckbox label p { color: var(--muted) !important; font-size: 13px !important; }
[data-testid="stAlert"] { background: var(--surface) !important; border: 1px solid var(--line) !important; border-radius: var(--r-md) !important; }
[data-testid="stAlert"] p { color: var(--ink2) !important; }
[data-testid="stStatusWidget"], [data-testid="stExpander"] { background: var(--surface) !important; border-color: var(--line) !important; }

/* ── 상단 바 ───────────────────────────────────────────── */
.si-brand { display: flex; align-items: center; gap: 10px; height: 40px; }
.si-mark { width: 22px; height: 22px; position: relative; flex-shrink: 0; }
.si-mark i { position: absolute; width: 9px; height: 9px; border-radius: 2px; background: var(--ink); }
.si-mark i:nth-child(1) { left: 0; top: 0; } .si-mark i:nth-child(2) { right: 0; top: 0; opacity: .45; }
.si-mark i:nth-child(3) { left: 0; bottom: 0; opacity: .45; } .si-mark i:nth-child(4) { right: 0; bottom: 0; background: var(--accent); }
.si-name { font-size: 18px; font-weight: 600; letter-spacing: -0.02em; color: var(--ink); }
.si-name span { color: var(--muted); font-weight: 500; }
.si-rule { height: 1px; background: var(--line); margin: 14px 0 0; }

/* ── 히어로: 오늘 브리핑 자체가 주인공 ───────────────────────── */
@keyframes si-enter { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes si-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes si-pulse { 0%,100% { opacity: 1; } 50% { opacity: .3; } }
.si-hero { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); column-gap: 24px; row-gap: 40px; padding: 72px 0 80px; border-bottom: 1px solid var(--line); }
.si-hero > :first-child { grid-column: 1 / 8; padding-right: 40px; }
.si-hero > :last-child { grid-column: 8 / 13; }
.si-hero > * { animation: si-enter .7s var(--ease) both; }
.si-hero > *:nth-child(2) { animation-delay: .12s; }
.si-kicker { display: flex; align-items: center; gap: 10px; font: 500 13px/1 var(--f-mono); color: var(--muted); letter-spacing: 0; margin-bottom: 28px; }
.si-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: si-pulse 2.4s ease-in-out infinite; }
.si-dot.is-idle { background: var(--muted); animation: none; }
.stMarkdown .si-h1 { font-family: var(--f-text) !important; font-size: clamp(34px, 4.2vw, 60px) !important; line-height: 1.1 !important; font-weight: 600 !important; letter-spacing: -0.04em; color: var(--ink) !important; margin: 0 0 32px !important; padding: 0 !important; word-break: keep-all; }
.stMarkdown .si-q { color: var(--muted) !important; }
.si-lead { font-size: 19px; line-height: 1.75; color: var(--ink2); max-width: 62ch; margin: 0; word-break: keep-all; }
.si-lead-empty { font-size: 19px; line-height: 1.7; color: var(--muted); margin: 0; }

/* 히어로 오른쪽: 오늘 판의 수치 패널 */
.si-panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 28px; align-self: start; }
.si-panel-head { display: flex; justify-content: space-between; align-items: baseline; font: 500 13px/1 var(--f-mono); color: var(--muted); padding-bottom: 20px; border-bottom: 1px solid var(--line); }
.si-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 24px 0; border-bottom: 1px solid var(--line); }
.si-stat b { display: block; font: 500 clamp(26px, 2.4vw, 34px)/1 var(--f-mono); letter-spacing: -0.04em; color: var(--ink); margin-bottom: 8px; }
.si-stat span { font-size: 13px; color: var(--muted); }
.si-src-title { font-size: 13px; font-weight: 500; color: var(--muted); margin: 22px 0 14px; }
.si-src { display: grid; grid-template-columns: 112px 1fr 28px; align-items: center; gap: 12px; font-size: 14px; color: var(--ink2); margin-bottom: 10px; }
.si-src em { font-style: normal; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.si-src i { display: block; height: 6px; border-radius: 3px; background: var(--accent); transform-origin: left; animation: si-grow .9s var(--ease) .35s both; }
.si-src s { text-decoration: none; font: 500 13px/1 var(--f-mono); color: var(--muted); text-align: right; }

/* ── 본문 장(章) ───────────────────────────────────────── */
.si-h2row { display: flex; justify-content: space-between; align-items: baseline; gap: 24px; padding: 96px 0 40px; }
.stMarkdown .si-h2 { font-family: var(--f-text) !important; font-size: clamp(26px, 2.6vw, 38px) !important; font-weight: 600 !important; letter-spacing: -0.035em; color: var(--ink) !important; margin: 0 !important; padding: 0 !important; line-height: 1.2 !important; word-break: keep-all; }
.si-meta { font: 500 13px/1 var(--f-mono); color: var(--muted); white-space: nowrap; }
.si-chapter { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); column-gap: 24px; row-gap: 16px; padding: 40px 0 48px; border-top: 1px solid var(--line); }
.si-chapter > :first-child { grid-column: 1 / 6; padding-right: 40px; }
.si-chapter > :last-child { grid-column: 6 / 13; }
.si-chapter-num { font: 500 13px/1 var(--f-mono); color: var(--accent); margin-bottom: 14px; }
.stMarkdown .si-chapter-title { font-family: var(--f-text) !important; font-size: 24px !important; line-height: 1.3 !important; font-weight: 600 !important; letter-spacing: -0.025em; color: var(--ink) !important; margin: 0 !important; padding: 0 !important; word-break: keep-all; }
.stMarkdown .si-body h4 { font-family: var(--f-text) !important; padding: 0 !important; }
.stMarkdown [data-testid="stHeaderActionElements"] { display: none !important; }
.si-cites { white-space: nowrap; }
.si-body { font-size: 17px; line-height: 1.8; color: var(--ink2); max-width: 68ch; word-break: keep-all; }
.si-body h4 { font-size: 18px; line-height: 1.45; font-weight: 600; letter-spacing: -0.015em; color: var(--ink); margin: 32px 0 10px; }
.si-body h4:first-child { margin-top: 0; }
.si-body p { margin: 0 0 18px; color: var(--ink2); }
.si-body ul, .si-body ol { padding-left: 20px; margin: 0 0 18px; }
.si-body li { color: var(--ink2); margin-bottom: 6px; }
.si-body strong { color: var(--ink); font-weight: 600; }

/* 인용 번호: 기사로 바로 가는 작은 칩 */
.si-cite {
  display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 20px;
  padding: 0 5px; margin: 0 1px; border-radius: 6px; vertical-align: 2px;
  font: 500 11.5px/1 var(--f-mono); color: var(--muted) !important; background: var(--surface2); text-decoration: none !important;
  transition: background-color .15s var(--ease), color .15s var(--ease), transform .15s var(--ease);
}
.si-cite:hover { background: var(--accent); color: var(--accent-ink) !important; transform: translateY(-1px); }

/* ── 참고 기사 ─────────────────────────────────────────── */
.si-refs { border-top: 1px solid var(--line); padding-top: 8px; }
.si-refs summary { cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center; padding: 20px 0; font-size: 17px; font-weight: 600; color: var(--ink); }
.si-refs summary::-webkit-details-marker { display: none; }
.si-refs summary::after { content: '+'; font: 400 22px/1 var(--f-mono); color: var(--muted); transition: transform .25s var(--ease); }
.si-refs[open] summary::after { transform: rotate(45deg); }
.si-ref-grid { display: grid; grid-template-columns: 1fr 1fr; column-gap: 48px; }
.si-ref { display: grid; grid-template-columns: 36px 1fr; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--line); color: var(--ink2) !important; font-size: 15px; line-height: 1.5; }
.si-ref b { font: 500 13px/1.6 var(--f-mono); color: var(--muted); }
.si-ref em { font-style: normal; display: block; font-size: 13px; color: var(--muted); margin-top: 4px; }
.si-ref span { background: linear-gradient(currentColor, currentColor) 0 100% / 0 1px no-repeat; transition: background-size .3s var(--ease), color .15s; }
.si-ref:hover span { background-size: 100% 1px; color: var(--ink); }

/* ── 아카이브: 날짜 타일 ───────────────────────────────── */
.si-month { font: 500 13px/1 var(--f-mono); color: var(--muted); margin: 8px 0 14px; }
[class*="st-key-day-"] div.stButton > button, [class*="st-key-dayon-"] div.stButton > button {
  width: 100%; min-height: 56px; border-radius: var(--r-md) !important; padding: 8px 8px !important;
  background: var(--surface) !important; border: 1px solid var(--line) !important;
}
[class*="st-key-day-"] div.stButton > button p, [class*="st-key-dayon-"] div.stButton > button p {
  font: 500 13px/1.3 var(--f-mono) !important; color: var(--ink2) !important; white-space: nowrap;
}
[class*="st-key-day-"] div.stButton > button:hover { border-color: var(--line2) !important; transform: translateY(-2px); box-shadow: var(--shadow) !important; }
[class*="st-key-dayon-"] div.stButton > button { border-color: var(--accent) !important; background: var(--accent-soft) !important; }
[class*="st-key-dayon-"] div.stButton > button p { color: var(--ink) !important; }

.si-foot { margin-top: 96px; padding-top: 24px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; gap: 24px; font-size: 13px; color: var(--muted); }
.si-foot span { font-family: var(--f-mono); }

@media (max-width: 900px) {
  .block-container { padding: 16px 20px 64px !important; }
  .si-hero { padding: 48px 0 56px; }
  .si-hero > :first-child, .si-hero > :last-child, .si-chapter > :first-child, .si-chapter > :last-child { grid-column: 1 / -1; padding-right: 0; }
  .si-ref-grid { grid-template-columns: 1fr; }
  .si-h2row { flex-direction: column; align-items: flex-start; gap: 12px; padding-top: 72px; }
  .si-lead { font-size: 17px; }
}
@media (max-width: 640px) {
  .st-key-archive [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; }
  .st-key-archive [data-testid="stColumn"] { width: calc(25% - 6px) !important; flex: 0 0 calc(25% - 6px) !important; min-width: 0 !important; }
  .st-key-archive [data-testid="stColumn"]:empty { display: none; }
  [class*="st-key-day-"] div.stButton > button p, [class*="st-key-dayon-"] div.stButton > button p { font-size: 12px !important; white-space: normal; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
"""

def _inject_css(t):
    css = _CSS
    for k, v in t.items():
        css = css.replace("{" + k + "}", v)
    # 빈 줄이 있으면 Streamlit 마크다운이 <style> 블록을 중간에서 끊는다
    css = "\n".join(line for line in css.split("\n") if line.strip())
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
# [수정] 국내(ko/KR) 에디션만 조회하면 해외 소식이 거의 잡히지 않아 글로벌 에디션(en-US/US)을
# 함께 조회해 기사 소스 범위를 넓힌다. 두 에디션은 동시에 요청해 지연 시간을 늘리지 않는다.
_NEWS_EDITIONS = [
    ("hl=ko&gl=KR&ceid=KR:ko", "domestic"),
    ("hl=en-US&gl=US&ceid=US:en", "global"),
]

def _fetch_one_edition(kw, edition_params, per_kw_limit, days, strict_time, start_dt, end_dt):
    url = (
        f"https://news.google.com/rss/search?"
        f"q={quote(kw)}+when:{days}d&{edition_params}"
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

def _fetch_keyword_news(kw, per_kw_limit, days, strict_time, start_dt, end_dt):
    """단일 키워드를 국내/글로벌 두 에디션에서 조회하여 (시간필터 통과 목록, 원본 전체 목록)을 함께 반환.
    시간필터 결과가 부족할 때 재크롤링 없이 원본 목록을 그대로 폴백에 사용한다."""
    filtered, raw = [], []
    for edition_params, _ in _NEWS_EDITIONS:
        f, r = _fetch_one_edition(kw, edition_params, per_kw_limit, days, strict_time, start_dt, end_dt)
        filtered.extend(f)
        raw.extend(r)
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

    # [수정] per_kw_limit: 전체 limit을 키워드 수로 동적 배분.
    # 키워드가 많을 때(예: 20개 이상) limit // 키워드수가 바닥값(3)에 걸려 NEWS_LIMIT을
    # 올려도 실제 수집량이 늘지 않는 문제가 있어 바닥값을 8로 상향.
    per_kw_limit = max(8, limit // max(len(keywords), 1))

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
# 3. AI 리포트 생성 (Google Gemini REST API)
# ==========================================
@st.cache_data(ttl=3600)
def get_available_models(api_key):
    """[수정] @st.cache_data(ttl=3600) 추가 → 매번 API 호출 방지"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [
                m['name'].replace("models/", "")
                for m in data.get('models', [])
                if 'generateContent' in m.get('supportedGenerationMethods', [])
            ]
    except Exception as e:
        logger.warning(f"Model list fetch error: {e}")
    return []

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
    models = get_available_models(api_key)
    if not models:
        models = ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-1.5-flash"]
    else:
        # gemini-2.0-flash 우선 정렬
        preferred = [m for m in models if "2.0-flash" in m]
        others = [m for m in models if "2.0-flash" not in m]
        models = preferred + others

    news_context = ""
    for i, item in enumerate(news_data):
        clean_title = re.sub(r'<[^>]+>', '', item['Title'])
        news_context += f"[{i+1}] {clean_title} (Source: {item['Source']})\n"

    prompt = f"""당신은 글로벌 반도체 소재 전략 수석 애널리스트입니다.
아래 뉴스만 근거로, 바쁜 임원이 핵심을 즉시 파악할 [일일 반도체 기술·소재 브리핑]을 작성하세요.

[절대 금지] "오늘날 반도체 산업은", "오늘 반도체 시장은", "최근 반도체 업계는", "글로벌 반도체 산업은", "전 세계 반도체 시장은", "반도체 시장이 급변하는 가운데" 등 산업 전체를 막연히 요약하는 상투적 도입 문장을 단 한 곳에도 쓰지 말 것 - 이 규칙은 핵심 요약뿐 아니라 Key Issues, Supply Chain, Analyst's View 등 모든 섹션의 첫 문장에 동일하게 적용됨. 모든 문장은 구체적 기업명·기술명·숫자·사건으로 바로 시작. 제목 나열/번역 금지. 뉴스에 없는 내용 추측 금지.
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

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048,  # 무료 Gemini API 토큰 한도에 맞춘 보수적인 출력 예산
            # gemini-2.5 계열은 기본적으로 "thinking" 토큰이 maxOutputTokens를 잠식해
            # 실제 응답이 조기 절단될 수 있으므로 명시적으로 비활성화
            "thinkingConfig": {"thinkingBudget": 0},
        }
    }

    # [수정] 429 응답 시 Exponential Backoff 적용, 모델별로 순차 재시도
    last_error = "응답 없음"
    for model in models:
        if "vision" in model:
            continue
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        retry_wait = 1
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)
                if response.status_code == 200:
                    res_json = response.json()
                    candidates = res_json.get('candidates')
                    if candidates:
                        raw_text = candidates[0]['content']['parts'][0]['text']
                        if len(raw_text) < 300 or "##" not in raw_text:
                            # 응답이 비정상적으로 짧거나(조기 절단) 구조가 없으면 폐기하고 재시도
                            logger.warning(f"리포트가 비정상적으로 짧음 [{model}] ({len(raw_text)} chars) → 재시도")
                            last_error = f"응답이 비정상적으로 짧음 [{model}] ({len(raw_text)} chars)"
                            continue
                        return True, inject_links_to_report(raw_text, news_data)
                    last_error = f"200 응답이지만 candidates 없음 [{model}]: {response.text[:300]}"
                    break  # candidates 없으면 다음 모델로
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit [{model}], retrying in {retry_wait}s...")
                    last_error = f"429 Rate limit [{model}]"
                    time.sleep(retry_wait)
                    retry_wait *= 2  # Exponential backoff
                    continue
                else:
                    last_error = f"{response.status_code} [{model}] {response.text[:300]}"
                    logger.warning(f"Gemini API 오류: {last_error}")
                    break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Report generation error [{model}]: {e}")
                break

    return False, f"AI 분석 실패 (Gemini API): {last_error}"

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
# [수정] 구버전 Streamlit 호환 폴리필: st.popover가 없으면 st.expander로 대체
if not hasattr(st, "popover"):
    st.popover = st.expander

from collections import Counter
from html import escape as _esc

_WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

def _ko_date(d):
    return f"{d.month}월 {d.day}일 {_WEEKDAYS[d.weekday()]}요일"

def _clean_title(title_html):
    """'📌 핵심 요약 (Executive Brief)' → '핵심 요약' : 앞쪽 이모지와 영문 괄호 병기를 걷어낸다."""
    t = re.sub(r'<[^>]+>', '', title_html)
    t = re.sub(r'^[^\w가-힣]+', '', t).strip()
    t = re.sub(r'\s*\((Executive Brief)\)\s*$', '', t)
    return t

def _with_citations(html, articles):
    """본문의 [n] 인용을 해당 기사로 가는 작은 칩 링크로 바꾼다."""
    def chip(n):
        idx = int(n) - 1
        if 0 <= idx < len(articles):
            a = articles[idx]
            link = sanitize_url(a.get('Link', '#'))
            title = _esc(re.sub(r'<[^>]+>', '', a.get('Source', '') + ' · ' + a.get('Title', '')), quote=True)
            return f"<a class='si-cite' href='{link}' target='_blank' rel='noopener' title='{title}'>{n}</a>"
        return f"[{n}]"
    def repl(m):
        # 연속된 인용과 바로 뒤 문장부호를 한 덩어리로 묶어 줄바꿈으로 떨어지지 않게 한다
        chips = ''.join(chip(n) for n in re.findall(r'\d+', m.group(1)))
        return f"<span class='si-cites'>{chips}{m.group(2)}</span>"
    return re.sub(r'\s?((?:\[\d+\])+)([.,]?)', repl, html)

def _sections_of(entry):
    report_html = md.markdown(entry['report'])
    return split_report_sections(report_html), report_html

# ── 날짜 계산 ──────────────────────────────────────────
now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
if now_kst.hour < 6:
    target_date = (now_kst - timedelta(days=1)).date()
else:
    target_date = now_kst.date()
target_date_str = target_date.strftime('%Y-%m-%d')

history = st.session_state.daily_history
today_report = next((h for h in history if h['date'] == target_date_str), None)

if "view_date" not in st.session_state:
    st.session_state.view_date = target_date_str
view_entry = next((h for h in history if h['date'] == st.session_state.view_date), None)
if view_entry is None:
    view_entry = today_report
    st.session_state.view_date = target_date_str
is_today_view = st.session_state.view_date == target_date_str

# ── 상단 바: 로고 · 키워드 · API Key · 화면 밝기 ──────────────
top_l, top_kw, top_key, top_mode = st.columns([6, 1.5, 1.5, 1.3], vertical_alignment="center")
with top_l:
    st.markdown(
        "<div class='si-brand'><span class='si-mark' aria-hidden='true'><i></i><i></i><i></i><i></i></span>"
        "<span class='si-name'>Semi Insight <span>· 반도체 소재 브리핑</span></span></div>",
        unsafe_allow_html=True
    )
with top_kw:
    with st.popover("수집 키워드", use_container_width=True):
        render_keyword_manager()
with top_key:
    with st.popover("API Key", use_container_width=True):
        user_key = st.text_input("Gemini API Key", type="password",
                                  label_visibility="collapsed",
                                  placeholder="Gemini API Key를 입력하세요")
        if user_key:
            api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
        if "GITHUB_TOKEN" in st.secrets:
            st.caption("GitHub 동기화 연결됨")
with top_mode:
    light = st.toggle("밝은 화면", value=not st.session_state.dark_mode)
    if light == st.session_state.dark_mode:
        st.session_state.dark_mode = not light
        st.rerun()
st.markdown("<div class='si-rule'></div>", unsafe_allow_html=True)

# ── 히어로: 오늘(또는 고른 날) 브리핑의 핵심 요약이 곧 첫 화면 ────────
n_keywords = len(st.session_state.keywords.get(DAILY_REPORT, []))
if view_entry:
    v_date = datetime.strptime(view_entry['date'], '%Y-%m-%d').date()
    articles = view_entry.get('articles', [])
    sections, report_html = _sections_of(view_entry)
    lead_html, rest = "", sections
    if sections:
        lead_html = re.sub(r'</?p>', '', ''.join(sections[0]['body']).strip())
        rest = sections[1:]
    sources = Counter(re.sub(r'<[^>]+>', '', a.get('Source', '')).strip() or '기타' for a in articles)
    top = sources.most_common(5)
    top_max = top[0][1] if top else 1
    src_rows = "".join(
        f"<div class='si-src'><em>{_esc(name)}</em>"
        f"<i style='width:{max(6, round(cnt / top_max * 100))}%'></i><s>{cnt}</s></div>"
        for name, cnt in top
    )
    when = "오늘 아침" if is_today_view else _ko_date(v_date)
    issued = view_entry.get('generated_at', '')
    kicker_state = "" if is_today_view else " is-idle"
    kicker_text = (f"{v_date.isoformat()} · 06:00 KST 발행" + (" · 자동" if view_entry.get('auto_generated') else "")
                   if is_today_view else f"{v_date.isoformat()} · 지난 브리핑")
    st.markdown(
        "<section class='si-hero'>"
        "<div>"
        f"<div class='si-kicker'><span class='si-dot{kicker_state}'></span>{kicker_text}</div>"
        f"<h1 class='si-h1'>{when}의 반도체 소재 브리핑. <span class='si-q'>기사 {len(articles)}건을 읽고 정리했습니다.</span></h1>"
        f"<p class='si-lead'>{_with_citations(lead_html, articles)}</p>"
        "</div>"
        "<aside class='si-panel' aria-label='이번 브리핑 수치'>"
        f"<div class='si-panel-head'><span>{_ko_date(v_date)}</span><span>{len(rest)}개 장</span></div>"
        "<div class='si-stats'>"
        f"<div class='si-stat'><b>{len(articles)}</b><span>읽은 기사</span></div>"
        f"<div class='si-stat'><b>{len(sources)}</b><span>언론사</span></div>"
        f"<div class='si-stat'><b>{n_keywords}</b><span>수집 키워드</span></div>"
        "</div>"
        "<div class='si-src-title'>많이 인용된 언론사</div>"
        f"{src_rows}"
        "</aside>"
        "</section>",
        unsafe_allow_html=True
    )
else:
    next_run_dt = target_date if now_kst.hour < 6 else (target_date + timedelta(days=1))
    st.markdown(
        "<section class='si-hero'>"
        "<div>"
        f"<div class='si-kicker'><span class='si-dot is-idle'></span>{target_date_str} · 아직 발행 전</div>"
        "<h1 class='si-h1'>오늘의 반도체 소재 브리핑. <span class='si-q'>아직 만들어지지 않았습니다.</span></h1>"
        f"<p class='si-lead-empty'>매일 06:00 KST에 자동으로 발행됩니다. 다음 자동 발행은 {next_run_dt} 06:00 KST입니다. "
        "지금 바로 만들려면 Gemini API Key를 넣고 아래 버튼을 누르세요.</p>"
        "</div><div></div></section>",
        unsafe_allow_html=True
    )

# ── 리포트 생성 액션 ───────────────────────────────────
def _run_generation(strict):
    status_box = st.status("브리핑을 만드는 중...", expanded=True)
    daily_kws = st.session_state.keywords[DAILY_REPORT]
    status_box.write(f"뉴스 수집 중 (최대 {NEWS_LIMIT}건)...")
    if strict:
        end_dt   = datetime.combine(target_date, dt_time(6, 0))
        start_dt = end_dt - timedelta(hours=18)
        # fetch_news 내부에서 시간필터 결과가 부족하면 재크롤링 없이 자동 폴백 처리
        news_items = fetch_news(daily_kws, days=2, limit=NEWS_LIMIT,
                                strict_time=True, start_dt=start_dt, end_dt=end_dt)
    else:
        news_items = fetch_news(daily_kws, days=2, limit=NEWS_LIMIT, strict_time=False)
    if not news_items:
        status_box.update(label="수집된 뉴스가 없습니다.", state="error")
        return
    status_box.write(f"AI 분석 중... ({len(news_items)}건)")
    success, result = generate_report_with_citations(api_key, news_items)
    if success:
        save_data = {'date': target_date_str, 'report': result, 'articles': news_items}
        status_box.write("GitHub에 저장 중...")
        save_daily_history(save_data)
        status_box.update(label="완료", state="complete")
        st.session_state.view_date = target_date_str
        st.rerun()
    else:
        status_box.update(label="AI 분석 실패", state="error")
        st.error(result)

if not today_report:
    if not api_key:
        st.info("브리핑을 만들려면 오른쪽 위 API Key에 Gemini API Key를 먼저 넣어주세요.")
    if st.button("오늘 브리핑 만들기", type="primary", disabled=not bool(api_key)):
        _run_generation(strict=True)

# ── 본문: 나머지 장(章) ─────────────────────────────────
if view_entry:
    articles = view_entry.get('articles', [])
    h_l, h_r1, h_r2 = st.columns([7, 1.4, 1.6], vertical_alignment="bottom")
    with h_l:
        st.markdown(
            "<div class='si-h2row'><h2 class='si-h2'>핵심 이슈와 공급망 분석</h2></div>",
            unsafe_allow_html=True
        )
    with h_r1:
        if st.button("새로 불러오기", use_container_width=True, key="reload_history"):
            # GitHub에서 최신 히스토리 강제 재로드
            st.session_state.daily_history = load_daily_history_from_source()
            st.rerun()
    with h_r2:
        if today_report and is_today_view:
            if st.button("브리핑 다시 만들기", use_container_width=True, disabled=not bool(api_key)):
                _run_generation(strict=False)
        elif not is_today_view:
            if st.button("오늘 브리핑으로", use_container_width=True, key="back_today"):
                st.session_state.view_date = target_date_str
                st.session_state.scroll_top = True
                st.rerun()

    if rest:
        chapters = ""
        for i, sec in enumerate(rest, start=2):
            body_html = _with_citations(''.join(sec['body']).strip(), articles)
            # 장 제목이 h3이므로 본문 소제목은 한 단계 아래(h4)로 내린다
            body_html = re.sub(r'<(/?)h3>', r'<\1h4>', body_html)
            chapters += (
                "<article class='si-chapter'>"
                f"<div><div class='si-chapter-num'>{i:02d}</div><h3 class='si-chapter-title'>{_esc(_clean_title(sec['title']))}</h3></div>"
                f"<div class='si-body'>{body_html}</div>"
                "</article>"
            )
        st.markdown(chapters, unsafe_allow_html=True)
    elif not sections:
        st.markdown(f"<div class='si-body'>{_with_citations(report_html, articles)}</div>", unsafe_allow_html=True)

    refs_html = "".join(
        f"<a class='si-ref' href='{sanitize_url(a.get('Link', '#'))}' target='_blank' rel='noopener'>"
        f"<b>{n:02d}</b><div><span>{_esc(re.sub(r'<[^>]+>', '', a.get('Title', '')))}</span>"
        f"<em>{_esc(re.sub(r'<[^>]+>', '', a.get('Source', '')))}</em></div></a>"
        for n, a in enumerate(articles, start=1)
    )
    st.markdown(
        f"<details class='si-refs'><summary>참고 기사 {len(articles)}건</summary>"
        f"<div class='si-ref-grid'>{refs_html}</div></details>",
        unsafe_allow_html=True
    )

# ── 아카이브: 날짜 타일을 누르면 그날 브리핑이 위에 열린다 ─────────
if history:
    st.markdown(
        f"<div class='si-h2row'><h2 class='si-h2'>지난 {len(history)}일의 브리핑</h2></div>",
        unsafe_allow_html=True
    )
    with st.container(key="archive"):
        months = {}
        for entry in history:
            months.setdefault(entry['date'][:7], []).append(entry)
        for month_key, entries in months.items():
            y, m = month_key.split('-')
            st.markdown(f"<div class='si-month'>{y}년 {int(m)}월 · {len(entries)}건</div>", unsafe_allow_html=True)
            per_row = 8  # 모바일에서는 CSS로 4칸씩 접혀 줄이 고르게 떨어진다
            for row_start in range(0, len(entries), per_row):
                cols = st.columns(per_row)
                for col, entry in zip(cols, entries[row_start:row_start + per_row]):
                    d = datetime.strptime(entry['date'], '%Y-%m-%d').date()
                    selected = entry['date'] == st.session_state.view_date
                    label = f"{d.month}.{d.day:02d} {_WEEKDAYS[d.weekday()]}" + (" · 오늘" if entry['date'] == target_date_str else "")
                    key = ("dayon-" if selected else "day-") + entry['date']
                    if col.button(label, key=key, use_container_width=True):
                        st.session_state.view_date = entry['date']
                        st.session_state.scroll_top = True
                        st.rerun()

st.markdown(
    "<footer class='si-foot'><div>Semi Insight · Google News 기사를 Gemini로 요약한 사내용 브리핑입니다. 원문은 각 언론사에 있습니다.</div>"
    f"<span>{now_kst.strftime('%Y-%m-%d %H:%M')} KST</span></footer>",
    unsafe_allow_html=True
)

# 날짜를 바꾸면 화면 맨 위(히어로)로 올려 고른 날의 브리핑이 바로 보이게 한다.
if st.session_state.pop("scroll_top", False):
    import streamlit.components.v1 as components
    components.html(
        "<script>const d=window.parent.document;"
        "(d.querySelector('[data-testid=\"stMain\"]')||d.querySelector('[data-testid=\"stAppViewContainer\"]')||d.documentElement)"
        ".scrollTo({top:0,behavior:'instant'});window.parent.scrollTo(0,0);</script>",
        height=0,
    )
