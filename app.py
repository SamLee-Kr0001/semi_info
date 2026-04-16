import streamlit as st
import pandas as pd
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
import yfinance as yf
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
st.set_page_config(layout="wide", page_title="Semi-Insight Hub", page_icon="💠")

CATEGORIES = ["Daily Report", "P&C 소재", "EDTW 소재", "PKG 소재"]
KEYWORD_FILE = 'keywords.json'
HISTORY_FILE = 'daily_history.json'

# [수정] api_key / search_days 전역 기본값 선언 → NameError 방지
api_key = ""
search_days = 3

# ==========================================
# 다크모드 session_state 초기화
# ==========================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ── 테마별 토큰 (hex 고정값, CSS 변수 미사용) ──────────
def get_theme():
    if st.session_state.dark_mode:
        return {
            "bg":           "#0F0F11",
            "surface":      "#1C1C1F",
            "surface2":     "#232327",
            "border":       "#2A2A2F",
            "border2":      "#36363D",
            "text":         "#FAFAFA",
            "text2":        "#A1A1AA",
            "muted":        "#52525B",
            "accent":       "#3B82F6",
            "accent_soft":  "#1e2d3d",
            "up":           "#F87171",
            "down":         "#60A5FA",
            "flat":         "#71717A",
            "badge_bg":     "#064E3B",
            "badge_fg":     "#6EE7B7",
            "shadow":       "0 4px 20px rgba(0,0,0,0.4)",
        }
    else:
        return {
            "bg":           "#F7F7F5",
            "surface":      "#FFFFFF",
            "surface2":     "#F9F9F7",
            "border":       "#E4E4E0",
            "border2":      "#D0D0CA",
            "text":         "#18181B",
            "text2":        "#71717A",
            "muted":        "#A1A1AA",
            "accent":       "#2563EB",
            "accent_soft":  "#EFF6FF",
            "up":           "#DC2626",
            "down":         "#2563EB",
            "flat":         "#71717A",
            "badge_bg":     "#D1FAE5",
            "badge_fg":     "#065F46",
            "shadow":       "0 4px 16px rgba(0,0,0,0.07)",
        }

T = get_theme()

# ── CSS 주입 ─────────────────────────────────────────────────
# {{ }} 이스케이프 없이 .format()으로 hex 값 주입 → 파싱 오류 원천 차단
_FONT = '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">'

_CSS = """
<style>
html, body, [class*="css"], .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stSidebar"],
.block-container {
    font-family: 'DM Sans', sans-serif !important;
}
.stApp, [data-testid="stAppViewContainer"] { background-color: BG !important; }
.block-container { background-color: BG !important; padding-top: 28px !important; padding-bottom: 48px !important; }
section[data-testid="stSidebar"] > div:first-child { background-color: SURFACE !important; border-right: 1px solid BORDER !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stRadio label, .stCheckbox label, p, span, div, li { color: TEXT !important; }
label[data-testid="stWidgetLabel"] { color: TEXT2 !important; font-size: 13px !important; }
div.stButton > button {
    font-family: 'DM Sans', sans-serif !important; font-size: 13px !important;
    font-weight: 500 !important; border-radius: 7px !important; padding: 5px 14px !important;
    border: 1px solid BORDER2 !important; background-color: SURFACE2 !important;
    color: TEXT !important; transition: all 0.15s ease !important; box-shadow: none !important;
}
div.stButton > button:hover { border-color: ACCENT !important; color: ACCENT !important; background-color: ACCENT_SOFT !important; }
div.stButton > button[kind="primary"] { background-color: ACCENT !important; color: #ffffff !important; border-color: ACCENT !important; }
div.stButton > button[kind="primary"]:hover { opacity: 0.88 !important; }
.stTextInput input, .stTextArea textarea {
    font-family: 'DM Sans', sans-serif !important; font-size: 13px !important;
    background-color: SURFACE !important; color: TEXT !important;
    border: 1px solid BORDER2 !important; border-radius: 7px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: ACCENT !important; }
[data-testid="stExpander"] { background-color: SURFACE !important; border: 1px solid BORDER !important; border-radius: 9px !important; overflow: hidden; }
[data-testid="stExpander"] summary { font-size: 13px !important; font-weight: 500 !important; color: TEXT2 !important; background-color: SURFACE !important; }
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] { background-color: SURFACE !important; border: 1px solid BORDER !important; border-radius: 10px !important; }
[data-testid="stAlert"] { background-color: SURFACE2 !important; border: 1px solid BORDER !important; border-radius: 8px !important; font-size: 13px !important; color: TEXT !important; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: BORDER2; border-radius: 999px; }
.si-logo { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid BORDER; }
.si-logo-mark { width: 30px; height: 30px; background: ACCENT; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; }
.si-logo-text { font-size: 14px; font-weight: 600; letter-spacing: -0.02em; color: TEXT !important; }
.si-logo-sub  { font-size: 10px; color: MUTED !important; letter-spacing: 0.06em; text-transform: uppercase; }
.si-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px; background: BADGE_BG; color: BADGE_FG !important; }
.si-banner { display: flex; align-items: center; gap: 10px; background: ACCENT_SOFT; border: 1px solid BORDER; border-radius: 8px; padding: 11px 15px; font-size: 13px; color: ACCENT !important; margin-bottom: 20px; font-weight: 500; }
.si-page-title { font-size: 21px; font-weight: 600; letter-spacing: -0.03em; color: TEXT; margin: 0 0 16px 0; padding-bottom: 16px; border-bottom: 1px solid BORDER; }
.si-news-card { background: SURFACE; border: 1px solid BORDER; border-radius: 9px; padding: 13px 15px; margin-bottom: 7px; }
.si-news-card:hover { border-color: ACCENT; box-shadow: SHADOW; }
.si-news-source { font-size: 10px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: ACCENT !important; margin-bottom: 4px; }
.si-news-title { font-size: 13px; font-weight: 500; color: TEXT !important; line-height: 1.5; display: block; }
.si-news-title:hover { color: ACCENT !important; }
.si-news-date { font-size: 11px; color: MUTED !important; margin-top: 3px; }
.si-report-card { background: SURFACE; border: 1px solid BORDER; border-radius: 12px; padding: 36px 40px; line-height: 1.85; font-size: 15px; color: TEXT; box-shadow: SHADOW; margin-bottom: 20px; }
.si-report-card h2 { font-size: 15px; font-weight: 600; color: TEXT; margin: 24px 0 8px; padding-bottom: 8px; border-bottom: 1px solid BORDER; }
.si-report-card h3 { font-size: 13px; font-weight: 600; color: TEXT2; margin: 16px 0 5px; }
.si-report-card p  { margin: 0 0 12px; }
.si-report-card a  { color: ACCENT !important; font-weight: 600; text-decoration: underline; }
.si-stock-label { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: MUTED !important; padding: 8px 0 3px; border-bottom: 1px solid BORDER; margin-bottom: 2px; }
.si-stock-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid BORDER; }
.si-stock-row:last-child { border-bottom: none; }
.si-stock-name  { font-size: 11px; font-weight: 500; color: TEXT2 !important; }
.si-stock-price { font-family: 'DM Mono', monospace; font-size: 11px; font-weight: 500; text-align: right; }
.si-stock-chg   { font-size: 10px; margin-left: 4px; }
.up-color   { color: UP   !important; }
.down-color { color: DOWN !important; }
.flat-color { color: FLAT !important; }
.si-archive-ref { display: flex; align-items: flex-start; gap: 7px; padding: 5px 0; border-bottom: 1px solid BORDER; font-size: 13px; color: TEXT2 !important; }
.si-archive-ref:hover { color: ACCENT !important; }
.si-archive-ref:last-child { border-bottom: none; }
a  { text-decoration: none; }
hr { border-color: BORDER !important; margin: 12px 0 !important; }
</style>
"""

def _inject_css(t):
    css = _CSS
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
    css = css.replace("BADGE_BG",    t["badge_bg"])
    css = css.replace("BADGE_FG",    t["badge_fg"])
    css = css.replace("SHADOW",      t["shadow"])
    css = css.replace("UP",          t["up"])
    css = css.replace("DOWN",        t["down"])
    css = css.replace("FLAT",        t["flat"])
    st.markdown(_FONT + css, unsafe_allow_html=True)

_inject_css(T)

# ==========================================
# 주식 티커
# [수정] "Qnity": "Q" → "Q"는 IQVIA 티커와 충돌. 실제 DuPont 분사 티커로 교체 필요
# 임시로 제거하고 주석 처리
# ==========================================
STOCK_CATEGORIES = {
    "🏭 Chipmakers": {
        "SK Hynix": "000660.KS", "Samsung": "005930.KS", "Micron": "MU",
        "TSMC": "TSM", "Intel": "INTC", "AMD": "AMD", "SMIC": "0981.HK"
    },
    "🧠 AI": {
        "NVIDIA": "NVDA", "Apple": "AAPL", "Alphabet": "GOOGL", "Microsoft": "MSFT",
        "Meta": "META", "Amazon": "AMZN", "Tesla": "TSLA", "IBM": "IBM",
        "Oracle": "ORCL", "Broadcom": "AVGO"
    },
    "🧪 Materials": {
        "Soulbrain": "357780.KQ", "Dongjin": "005290.KQ", "Hana Mat": "166090.KQ",
        "Wonik Mat": "104830.KQ", "TCK": "064760.KQ", "Foosung": "093370.KS",
        "PI Adv": "178920.KS", "ENF": "102710.KQ", "TEMC": "425040.KQ",
        "YC Chem": "112290.KQ", "Samsung SDI": "006400.KS", "Shin-Etsu": "4063.T",
        "Sumco": "3436.T", "Merck": "MRK.DE", "Entegris": "ENTG", "TOK": "4186.T",
        "Resonac": "4004.T", "Air Prod": "APD", "Linde": "LIN",
        # "Qnity": "Q",  # [수정] "Q"는 IQVIA 티커와 충돌 → 실제 티커 확인 후 재추가 필요
        "Nissan Chem": "4021.T", "Sumitomo": "4005.T"
    },
    "⚙️ Equipment": {
        "ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T",
        "KLA": "KLAC", "Advantest": "6857.T", "Hitachi HT": "8036.T",
        "Hanmi": "042700.KS", "Wonik IPS": "240810.KQ", "Jusung": "036930.KQ",
        "EO Tech": "039030.KQ", "Techwing": "089030.KQ", "Eugene": "084370.KQ",
        "PSK": "319660.KQ", "Zeus": "079370.KQ", "Top Eng": "065130.KQ"
    }
}

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
    data = {cat: [] for cat in CATEGORIES}
    if "GITHUB_TOKEN" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(KEYWORD_FILE)
            loaded = json.loads(contents.decoded_content.decode("utf-8"))
            return loaded
        except Exception as e:
            logger.warning(f"GitHub keyword load error: {e}")
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in data:
                    data[k] = v
        except Exception as e:
            logger.warning(f"Local keyword load error: {e}")
    if not data.get("Daily Report"):
        data["Daily Report"] = ["반도체", "삼성전자", "SK하이닉스"]
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
if 'news_data' not in st.session_state:
    st.session_state.news_data = {cat: [] for cat in CATEGORIES}
if 'keywords' not in st.session_state:
    st.session_state.keywords = load_keywords()
if 'daily_history' not in st.session_state:
    st.session_state.daily_history = load_daily_history_from_source()

def save_daily_history(new_report_data):
    current_history = [h for h in st.session_state.daily_history if h['date'] != new_report_data['date']]
    current_history.insert(0, new_report_data)
    st.session_state.daily_history = current_history
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=4, default=str)
    except Exception as e:
        logger.warning(f"Local history save error: {e}")
    sync_to_github(HISTORY_FILE, current_history)

# ==========================================
# 주식 데이터 수집
# ==========================================
def fetch_single_stock(name, symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist_5d = ticker.history(period="5d")
        if hist_5d.empty:
            return name, None

        prev = hist_5d['Close'].iloc[-2] if len(hist_5d) >= 2 else hist_5d['Close'].iloc[-1]
        current = hist_5d['Close'].iloc[-1]

        # 장중 실시간 시세 덮어쓰기 시도 (2분봉)
        try:
            hist_live = ticker.history(period="1d", interval="2m")
            if not hist_live.empty:
                current = hist_live['Close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Live price fetch failed [{symbol}]: {e}")

        if current is None or pd.isna(current):
            return name, None

        change = current - prev
        pct = (change / prev) * 100 if prev != 0 else 0

        if ".KS" in symbol or ".KQ" in symbol:
            cur_sym = "₩"
        elif ".T" in symbol:
            cur_sym = "¥"
        elif ".HK" in symbol:
            cur_sym = "HK$"
        elif ".DE" in symbol:
            cur_sym = "€"
        else:
            cur_sym = "$"

        fmt_price = f"{cur_sym}{current:,.0f}" if cur_sym in ["₩", "¥"] else f"{cur_sym}{current:,.2f}"

        if change > 0:
            color_class, arrow, sign = "up-color", "▲", "+"
        elif change < 0:
            color_class, arrow, sign = "down-color", "▼", ""
        else:
            color_class, arrow, sign = "flat-color", "-", ""

        html_str = (
            f"<div class='si-stock-row'>"
            f"<span class='si-stock-name'>{name}</span>"
            f"<span class='si-stock-price {color_class}'>{fmt_price}"
            f"<span class='si-stock-chg'>{arrow}{sign}{pct:.2f}%</span></span>"
            f"</div>"
        )
        return name, html_str
    except Exception as e:
        logger.warning(f"Stock fetch error [{symbol}]: {e}")
        return name, None

@st.cache_data(ttl=300)
def get_stock_prices_grouped():
    result_map = {}
    all_tickers = [
        (name, symbol)
        for cat, items in STOCK_CATEGORIES.items()
        for name, symbol in items.items()
    ]
    # [수정] max_workers를 티커 수에 맞게 동적 설정
    max_workers = min(32, len(all_tickers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {
            executor.submit(fetch_single_stock, name, symbol): name
            for name, symbol in all_tickers
        }
        for future in concurrent.futures.as_completed(future_to_stock):
            try:
                name, html = future.result()
                if html:
                    result_map[name] = html
            except Exception as e:
                logger.warning(f"Stock future error: {e}")
    return result_map

# ==========================================
# 2. 뉴스 수집
# ==========================================
def fetch_news(keywords, days=1, limit=40, strict_time=False, start_dt=None, end_dt=None):
    """
    [수정] strict_time 조건 분리:
    - strict_time=True  → 전달받은 start_dt/end_dt 사용
    - strict_time=False → 현재 시각 기준 기본 window 계산
    """
    all_items = []

    if not strict_time:
        # strict_time=False 일 때만 기본 window 계산 (전달 인자 무시하지 않음)
        now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
        end_dt = datetime(now_kst.year, now_kst.month, now_kst.day, 6, 0, 0)
        if now_kst.hour < 6:
            end_dt -= timedelta(days=1)
        start_dt = end_dt - timedelta(hours=18)

    # [수정] per_kw_limit: 전체 limit을 키워드 수로 동적 배분
    per_kw_limit = max(3, limit // max(len(keywords), 1))

    for kw in keywords:
        url = (
            f"https://news.google.com/rss/search?"
            f"q={quote(kw)}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
        )
        try:
            res = requests.get(url, timeout=5, verify=False)
            res.raise_for_status()
            soup = BeautifulSoup(res.content, 'xml')
            items = soup.find_all('item')
            kw_collected = 0
            for item in items:
                is_valid = True
                pub_date_str_val = None

                if strict_time and start_dt and end_dt:
                    try:
                        pub_date_str = item.pubDate.text
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                        pub_date_kst = pub_date + timedelta(hours=9)
                        if not (start_dt <= pub_date_kst <= end_dt):
                            is_valid = False
                        pub_date_str_val = pub_date_kst.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        is_valid = True  # 날짜 파싱 실패 시 포함

                if is_valid:
                    title = item.title.text if item.title else ""
                    link = item.link.text if item.link else ""
                    if title and not any(i['Title'] == title for i in all_items):
                        all_items.append({
                            'Title': title,
                            'Link': link,
                            'Date': item.pubDate.text if item.pubDate else "",
                            'Source': item.source.text if item.source else "Google News",
                            'ParsedDate': pub_date_str_val
                        })
                        kw_collected += 1
                if kw_collected >= per_kw_limit:
                    break
        except Exception as e:
            logger.warning(f"News fetch error [kw={kw}]: {e}")
        time.sleep(0.1)

    df = pd.DataFrame(all_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['Title'])
        if strict_time:
            df['TempDate'] = pd.to_datetime(df['ParsedDate'], errors='coerce')
            df = df.sort_values(by='TempDate', ascending=False)
            df = df.drop(columns=['TempDate'])
        return df.head(limit).to_dict('records')
    return []

# ==========================================
# 2-1. 글로벌 뉴스
# ==========================================
def translate_text_batch(api_key, texts, target_lang="Korean"):
    if not texts:
        return []
    # [수정] 기본 모델을 gemini-2.0-flash로 업데이트
    model = "gemini-2.0-flash"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            models = [
                m['name'].replace("models/", "")
                for m in res.json().get('models', [])
                if 'generateContent' in m.get('supportedGenerationMethods', [])
            ]
            if models:
                # gemini-2.0-flash 우선, 없으면 첫 번째 모델 사용
                model = next((m for m in models if "2.0-flash" in m), models[0])
    except Exception as e:
        logger.warning(f"Model list fetch error: {e}")

    prompt = (
        f"Translate the following list of texts to {target_lang}. "
        f"Return ONLY the translated strings in a JSON array format [\"text1\", \"text2\"...].\n\n"
        f"Texts: {json.dumps(texts)}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"Translation error: {e}")
    return texts

def get_translated_keywords(api_key, keyword):
    prompt = (
        f"Translate '{keyword}' into English, Japanese, Traditional Chinese(TW), Simplified Chinese(CN). "
        f"Return JSON: {{\"EN\":\"..\",\"JP\":\"..\",\"TW\":\"..\",\"CN\":\"..\"}}"
    )
    # [수정] 기본 모델을 gemini-2.0-flash로 업데이트
    model = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            txt = res.json()['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', txt, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"Keyword translation error [{keyword}]: {e}")
    return {"EN": keyword, "JP": keyword, "TW": keyword, "CN": keyword}

def fetch_news_global(api_key, keywords, days=3):
    TARGETS = {
        "KR": {"gl": "KR", "hl": "ko",    "key": "KR"},
        "US": {"gl": "US", "hl": "en",    "key": "EN"},
        "JP": {"gl": "JP", "hl": "ja",    "key": "JP"},
        "TW": {"gl": "TW", "hl": "zh-TW", "key": "TW"},
        "CN": {"gl": "CN", "hl": "zh-CN", "key": "CN"}
    }
    all_raw_items = []
    per_kw_limit = max(3, 5 // max(len(keywords), 1))

    for kw in keywords:
        trans_map = get_translated_keywords(api_key, kw)
        trans_map["KR"] = kw
        for country, conf in TARGETS.items():
            search_term = trans_map.get(conf["key"], kw)
            url = (
                f"https://news.google.com/rss/search?"
                f"q={quote(search_term)}+when:{days}d"
                f"&hl={conf['hl']}&gl={conf['gl']}&ceid={conf['gl']}:{conf['hl']}"
            )
            try:
                res = requests.get(url, timeout=3, verify=False)
                res.raise_for_status()
                soup = BeautifulSoup(res.content, 'xml')
                items = soup.find_all('item')
                kw_added = 0
                for item in items:
                    title = item.title.text if item.title else ""
                    link = item.link.text if item.link else ""
                    if title:
                        all_raw_items.append({
                            'Title': title,
                            'Link': link,
                            'Date': item.pubDate.text if item.pubDate else "",
                            'Source': f"[{country}] {item.source.text if item.source else 'Google News'}",
                            'Lang': conf['key']
                        })
                        kw_added += 1
                        if kw_added >= per_kw_limit:
                            break
            except Exception as e:
                logger.warning(f"Global news fetch error [kw={kw}, country={country}]: {e}")
            time.sleep(0.1)

    if not all_raw_items:
        return []

    df = pd.DataFrame(all_raw_items)
    # [수정] Title + Link 두 기준으로 중복 제거
    df = df.drop_duplicates(subset=['Title'])
    df = df.drop_duplicates(subset=['Link'])
    items_to_process = df.head(40).to_dict('records')

    titles_to_translate = [x['Title'] for x in items_to_process if x['Lang'] != "KR"]
    indices_to_translate = [i for i, x in enumerate(items_to_process) if x['Lang'] != "KR"]

    if titles_to_translate:
        translated_titles = translate_text_batch(api_key, titles_to_translate)
        for idx, new_title in zip(indices_to_translate, translated_titles):
            if idx < len(items_to_process):
                orig = items_to_process[idx]['Title']
                items_to_process[idx]['Title'] = (
                    f"{new_title} "
                    f"<span style='font-size:0.8em; color:#94A3B8;'>({orig})</span>"
                )
    return items_to_process

# ==========================================
# 3. AI 리포트 생성
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
        # [수정] 기본 모델 목록을 최신 버전으로 업데이트
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

    prompt = f"""
    당신은 글로벌 반도체 소재의 중요 전략 수석 엔지니어 입니다. 
    제공된 뉴스 데이터를 바탕으로 전문가 수준의 **[일일 반도체 기술과 반도체 소재 심층 분석 보고서]**를 작성하세요.

    **[작성 원칙 - 매우 중요]**
    1. **단순 요약 금지**: 뉴스 제목을 단순히 나열하거나 번역하지 마세요.
    2. **서술형 작성**: 이슈별로 현상/원인/전망을 개조식(Bullet points)으로 나누지 말고, **하나의 자연스러운 논리적 흐름을 가진 줄글(Narrative Paragraph)**로 서술하세요. 전문적인 문체를 사용하세요.
    3. **근거 명시**: 모든 주장이나 사실 언급 시 반드시 제공된 뉴스 번호 **[1], [2]**를 문장 끝에 인용하세요.

    [뉴스 데이터]
    {news_context}
    
    [보고서 구조 (Markdown)]
    
    ## 🚨 Key Issues & Deep Dive (핵심 이슈 심층 분석)
    - 가장 중요한 이슈 2~3가지를 선정하여 소제목을 달고 분석하세요.
    - **중요**: 현상, 원인, 전망을 구분하여 나열하지 말고, **깊이 있는 서술형 문단**으로 작성하세요.
    - 반드시 인용 번호[n]를 포함할 것.

    ## 🕸️ Supply Chain & Tech Trends (공급망 및 기술 동향)
    - 반도체 소재 그리고 소부장 기술의 변화와 공급망관련 주요 단신을 종합하여 서술.

    ## 💡 Analyst's View (시사점)
    - 중요한 반도체 기술과 소재 특이점 관련 오늘의 뉴스가 주는 시사점과 향후 관전 포인트 한 줄 정리.

    ## 📊 Executive Summary (시장 총평)
    - 오늘 반도체 시장과 기술적 변화의 핵심 분위기와 소재 중심의 이슈를 3~4문장으로 요약.
    """

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
    }

    # [수정] 429 응답 시 Exponential Backoff 적용
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
                    if 'candidates' in res_json and res_json['candidates']:
                        raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                        return True, inject_links_to_report(raw_text, news_data)
                    break  # candidates 없으면 다음 모델로
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit [{model}], retrying in {retry_wait}s...")
                    time.sleep(retry_wait)
                    retry_wait *= 2  # Exponential backoff
                    continue
                else:
                    logger.warning(f"Model {model} returned status {response.status_code}")
                    break
            except Exception as e:
                logger.warning(f"Report generation error [{model}]: {e}")
                break

    return False, "AI 분석 실패 (모든 모델 응답 없음)"

# ==========================================
# 4. 공통 키워드 관리 UI (중복 코드 제거)
# ==========================================
def render_keyword_manager(category, show_search_days=False):
    """
    [수정] Daily Report / 일반 카테고리 공통 키워드 관리 UI 함수화
    show_search_days=True 이면 검색 기간 슬라이더도 함께 렌더링
    반환값: (추가된 키워드 없음), search_days (int)
    """
    returned_search_days = 3
    c1, c2, c3 = st.columns([2, 1, 1]) if show_search_days else (st.columns([3, 1]) + [None])

    new_kw = c1.text_input(
        "수집 키워드 추가" if not show_search_days else "키워드",
        placeholder="예: HBM, 패키징",
        label_visibility="collapsed",
        key=f"kw_input_{category}"
    )
    if c2.button("추가", use_container_width=True, key=f"kw_add_{category}"):
        if new_kw and new_kw not in st.session_state.keywords[category]:
            st.session_state.keywords[category].append(new_kw)
            save_keywords(st.session_state.keywords)
            st.rerun()

    if show_search_days and c3 is not None:
        returned_search_days = c3.slider("검색 기간", 1, 30, 3, key=f"days_{category}")

    curr_kws = st.session_state.keywords.get(category, [])
    if curr_kws:
        st.write("")
        num_cols = min(len(curr_kws), 8)
        cols = st.columns(num_cols)
        for i, kw in enumerate(curr_kws):
            if cols[i % num_cols].button(f"{kw} ×", key=f"kw_del_{category}_{i}_{kw}"):
                st.session_state.keywords[category].remove(kw)
                save_keywords(st.session_state.keywords)
                st.rerun()

    return returned_search_days

# ==========================================
# 5. 메인 앱 UI
# ==========================================
# [수정] st.fragment 폴리필 (구버전 Streamlit 호환)
if not hasattr(st, "fragment"):
    def dummy_fragment(**kwargs):
        return lambda f: f
    st.fragment = dummy_fragment

@st.fragment(run_every=300)
def render_stock_widget():
    if st.button("↻ 새로고침", use_container_width=True):
        get_stock_prices_grouped.clear()
    stock_data = get_stock_prices_grouped()
    if stock_data:
        for cat, items in STOCK_CATEGORIES.items():
            st.markdown(f"<div class='si-stock-label'>{cat}</div>", unsafe_allow_html=True)
            for name in items:
                html_info = stock_data.get(name)
                if html_info:
                    st.markdown(html_info, unsafe_allow_html=True)

# ==========================================
# 사이드바
# ==========================================
with st.sidebar:
    # 로고
    st.markdown(f"""
    <div class="si-logo">
        <div class="si-logo-mark">💠</div>
        <div>
            <div class="si-logo-text">Semi-Insight Hub</div>
            <div class="si-logo-sub">Semiconductor Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 다크모드 토글 (Streamlit native → session_state 기반)
    dark_toggled = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark_toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggled
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    selected_category = st.radio("카테고리", CATEGORIES, index=0, label_visibility="collapsed")
    st.markdown("<hr>", unsafe_allow_html=True)

    with st.expander("🔐 API Key"):
        user_key = st.text_input("Gemini API Key", type="password",
                                  label_visibility="collapsed",
                                  placeholder="Gemini API Key를 입력하세요")
        if user_key:
            api_key = user_key
        elif "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]

    if "GITHUB_TOKEN" in st.secrets:
        st.markdown(
            "<div style='margin-top:10px'><span class='si-badge'>✓ GitHub Sync On</span></div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    with st.expander("📈 Global Stocks", expanded=True):
        render_stock_widget()

# ==========================================
# 메인 콘텐츠
# ==========================================
c_head, c_info = st.columns([3, 1])
with c_head:
    st.markdown(
        f"<div class='si-page-title'>{selected_category}</div>",
        unsafe_allow_html=True
    )

# ----------------------------------
# [Mode 1] Daily Report
# ----------------------------------
if selected_category == "Daily Report":

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
        "⏱️ 매일 06:00 KST GitHub Actions가 자동으로 리포트를 생성합니다. "
        "아래 버튼으로 수동 생성도 가능합니다."
        "</div>",
        unsafe_allow_html=True
    )

    # ── 날짜 표시 + GitHub 최신화 버튼 ────────────────────
    col_date, col_refresh = st.columns([4, 1])
    with col_date:
        st.markdown(
            f"<div style='font-size:12px; color:{T['muted']}; padding-top:6px;'>"
            f"Report Date &nbsp;·&nbsp; <b style='color:{T['text2']}'>{target_date}</b></div>",
            unsafe_allow_html=True
        )
    with col_refresh:
        if st.button("↻ 새로고침", use_container_width=True, key="reload_history"):
            # GitHub에서 최신 히스토리 강제 재로드
            st.session_state.daily_history = load_daily_history_from_source()
            st.rerun()

    # ── 키워드 관리 ────────────────────────────────────────
    with st.expander("⚙️ 키워드 관리", expanded=False):
        render_keyword_manager("Daily Report", show_search_days=False)

    # ── 오늘 리포트 상태 확인 ──────────────────────────────
    history = st.session_state.daily_history
    today_report = next((h for h in history if h['date'] == target_date_str), None)

    if not today_report:
        # GitHub Actions가 아직 실행 전이거나 실패한 경우
        next_run_h  = 6 if now_kst.hour >= 6 else 6
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
                daily_kws = st.session_state.keywords["Daily Report"]

                status_box.write("📡 뉴스 수집 중 (40건)...")
                news_items = fetch_news(
                    daily_kws, days=2, limit=40,
                    strict_time=True, start_dt=start_dt, end_dt=end_dt
                )
                if not news_items:
                    status_box.update(label="⚠️ 시간 범위 내 뉴스 없음 → 최근 2일로 확장", state="running")
                    time.sleep(0.5)
                    news_items = fetch_news(daily_kws, days=2, limit=40, strict_time=False)

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
            auto_tag = " &nbsp;<span style='font-size:10px;background:#D1FAE5;color:#065F46;padding:2px 7px;border-radius:999px;font-weight:600;'>AUTO</span>"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:12px;'>"
            f"<span style='color:#16a34a;font-size:13px;font-weight:600;'>✅ 리포트 생성 완료</span>"
            f"{auto_tag}</div>",
            unsafe_allow_html=True
        )

        # 수동 재생성 버튼
        if st.button("🔄 리포트 다시 만들기", disabled=not bool(api_key)):
            status_box = st.status("🚀 재생성 중...", expanded=True)
            daily_kws  = st.session_state.keywords["Daily Report"]
            news_items = fetch_news(daily_kws, days=2, limit=40, strict_time=False)
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
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:14px; font-weight:600; color:{T['text2']}; "
            f"margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid {T['border']};'>"
            "🗂️ 리포트 아카이브</div>",
            unsafe_allow_html=True
        )
        for entry in history:
            is_today = (entry['date'] == target_date_str)
            with st.expander(
                f"{'🔥 ' if is_today else ''}{entry['date']} Daily Report",
                expanded=is_today
            ):
                st.markdown(
                    f"<div class='si-report-card'>{entry['report']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div style='font-size:12px; font-weight:600; color:{T['muted']}; "
                    f"letter-spacing:0.05em; text-transform:uppercase; margin:16px 0 8px;'>"
                    "참고 기사</div>",
                    unsafe_allow_html=True
                )
                for item in entry.get('articles', []):
                    safe_link = sanitize_url(item.get('Link', '#'))
                    clean_title = re.sub(r'<[^>]+>', '', item.get('Title', ''))
                    accent = T['accent']
                    st.markdown(
                        f"<a href='{safe_link}' target='_blank' class='si-archive-ref'>"
                        f"<span style='color:{accent};flex-shrink:0'>↗</span>"
                        f"<span>{clean_title}</span></a>",
                        unsafe_allow_html=True
                    )

# ----------------------------------
# [Mode 2] 일반 카테고리
# ----------------------------------
else:
    with st.container(border=True):
        # [수정] 공통 함수 사용, search_days 반환 받음
        search_days = render_keyword_manager(selected_category, show_search_days=True)

        if st.button(
            "실행 (5개국 검색 + 번역)", type="primary",
            use_container_width=True,
            disabled=not bool(api_key)
        ):
            kws = st.session_state.keywords[selected_category]
            if kws:
                with st.spinner("🌍 5개국 뉴스 수집 중..."):
                    news = fetch_news_global(api_key, kws, days=search_days)
                    st.session_state.news_data[selected_category] = news
                    st.rerun()

    data = st.session_state.news_data.get(selected_category, [])
    if data:
        st.markdown(
            f"<div style='font-size:12px; color:{T['muted']}; margin-bottom:16px;'>"
            f"총 <b style='color:{T['text2']}'>{len(data)}</b>건 수집 · 최근 {search_days}일</div>",
            unsafe_allow_html=True
        )
        for item in data:
            safe_link = sanitize_url(item.get('Link', '#'))
            clean_title = re.sub(r'<[^>]+>', '', item.get('Title', ''))
            st.markdown(
                f"<div class='si-news-card'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;'>"
                f"<span class='si-news-source'>{item['Source']}</span>"
                f"<span class='si-news-date'>{item['Date']}</span>"
                f"</div>"
                f"<a href='{safe_link}' target='_blank' class='si-news-title'>{clean_title}</a>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.info("상단의 '실행' 버튼을 눌러 뉴스를 수집하세요. (API Key 필요)")
