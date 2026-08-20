"""
core/theme.py
───────────────
"MatChain Insight" 디자인 시스템.
분석 리포트 매체 느낌을 내기 위해 본문은 세리프(Source Serif 4), UI는 산세리프(Inter)를 사용한다.
"""

FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&'
    'family=Inter:wght@400;500;600;700&'
    'family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
)

LIGHT = {
    "bg": "#FAF9F6",
    "surface": "#FFFFFF",
    "surface2": "#F3F1EC",
    "border": "#E7E3DA",
    "border2": "#D8D2C4",
    "text": "#1C1B18",
    "text2": "#6B6558",
    "muted": "#9A9385",
    "accent": "#B4530A",
    "accent_soft": "#FBEEE0",
    "up": "#C0392B",
    "down": "#1D6FA5",
    "flat": "#8A8578",
    "badge_bg": "#E6F0EA",
    "badge_fg": "#1F6B4C",
    "shadow": "0 6px 24px rgba(28,27,24,0.06)",
}

DARK = {
    "bg": "#14130F",
    "surface": "#1D1B16",
    "surface2": "#242219",
    "border": "#332F24",
    "border2": "#433D2D",
    "text": "#F5F2EA",
    "text2": "#B6AF9E",
    "muted": "#78725F",
    "accent": "#E08A34",
    "accent_soft": "#2B2013",
    "up": "#E5776A",
    "down": "#5FA8D3",
    "flat": "#8A8578",
    "badge_bg": "#1E3226",
    "badge_fg": "#7FCBA4",
    "shadow": "0 6px 24px rgba(0,0,0,0.45)",
}


def get_theme(dark_mode):
    return DARK if dark_mode else LIGHT


_CSS_TEMPLATE = """
<style>
html, body, [class*="css"], .stApp,
[data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"],
.block-container {
    font-family: 'Inter', sans-serif !important;
}
.stApp, [data-testid="stAppViewContainer"] { background-color: {bg} !important; }
.block-container { background-color: {bg} !important; padding-top: 24px !important; padding-bottom: 48px !important; max-width: 1180px; }
section[data-testid="stSidebar"] > div:first-child { background-color: {surface} !important; border-right: 1px solid {border} !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stRadio label, .stCheckbox label, p, span, div, li { color: {text} !important; }
label[data-testid="stWidgetLabel"] { color: {text2} !important; font-size: 12.5px !important; }

div.stButton > button {
    font-family: 'Inter', sans-serif !important; font-size: 13px !important; font-weight: 600 !important;
    border-radius: 8px !important; padding: 6px 16px !important;
    border: 1px solid {border2} !important; background-color: {surface2} !important;
    color: {text} !important; transition: all 0.15s ease !important; box-shadow: none !important;
}
div.stButton > button:hover { border-color: {accent} !important; color: {accent} !important; background-color: {accent_soft} !important; }
div.stButton > button[kind="primary"] { background-color: {accent} !important; color: #ffffff !important; border-color: {accent} !important; }
div.stButton > button[kind="primary"]:hover { opacity: 0.9 !important; }

.stTextInput input, .stTextArea textarea {
    font-family: 'Inter', sans-serif !important; font-size: 13px !important;
    background-color: {surface} !important; color: {text} !important;
    border: 1px solid {border2} !important; border-radius: 8px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: {accent} !important; }
[data-testid="stExpander"] { background-color: {surface} !important; border: 1px solid {border} !important; border-radius: 10px !important; overflow: hidden; }
[data-testid="stExpander"] summary { font-size: 13px !important; font-weight: 600 !important; color: {text2} !important; background-color: {surface} !important; }
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] { background-color: {surface} !important; border: 1px solid {border} !important; border-radius: 12px !important; }
[data-testid="stAlert"] { background-color: {surface2} !important; border: 1px solid {border} !important; border-radius: 9px !important; font-size: 13px !important; color: {text} !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid {border}; }
.stTabs [data-baseweb="tab"] { font-size: 13px; font-weight: 600; color: {text2}; }
.stTabs [aria-selected="true"] { color: {accent} !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: {border2}; border-radius: 999px; }

/* ── 브랜드 ── */
.mc-logo { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; padding-bottom: 16px; border-bottom: 1px solid {border}; }
.mc-logo-mark { width: 32px; height: 32px; background: {accent}; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; color: #fff; }
.mc-logo-text { font-size: 14.5px; font-weight: 700; letter-spacing: -0.02em; color: {text} !important; }
.mc-logo-sub  { font-size: 10px; color: {muted} !important; letter-spacing: 0.07em; text-transform: uppercase; }

/* ── 카테고리 헤더 ── */
.mc-cat-header { display: flex; align-items: baseline; gap: 10px; margin: 0 0 4px 0; }
.mc-cat-icon { font-size: 22px; }
.mc-cat-title { font-family: 'Source Serif 4', serif; font-size: 25px; font-weight: 700; letter-spacing: -0.01em; color: {text}; }
.mc-cat-desc { font-size: 13px; color: {text2} !important; margin: 0 0 18px 0; padding-bottom: 16px; border-bottom: 1px solid {border}; }

/* ── 배지 / 칩 ── */
.mc-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 3px 9px; border-radius: 999px; background: {badge_bg}; color: {badge_fg} !important; }
.mc-flag-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: {surface2}; border: 1px solid {border}; color: {text2} !important; margin: 0 6px 6px 0; }
.mc-banner { display: flex; align-items: center; gap: 10px; background: {accent_soft}; border: 1px solid {border}; border-radius: 9px; padding: 11px 15px; font-size: 13px; color: {accent} !important; margin-bottom: 18px; font-weight: 600; }

/* ── 리포트 본문 ── */
.mc-report-card { background: {surface}; border: 1px solid {border}; border-radius: 14px; padding: 38px 42px; box-shadow: {shadow}; margin-bottom: 20px; }
.mc-report-card h2 { font-family: 'Source Serif 4', serif; font-size: 18px; font-weight: 700; color: {text}; margin: 26px 0 10px; padding-bottom: 9px; border-bottom: 1px solid {border}; }
.mc-report-card h2:first-child { margin-top: 0; }
.mc-report-card h3 { font-size: 13.5px; font-weight: 700; color: {accent}; margin: 18px 0 6px; }
.mc-report-card p  { font-size: 15px; line-height: 1.9; margin: 0 0 14px; color: {text}; }
.mc-report-card a  { color: {accent} !important; font-weight: 700; text-decoration: none; border-bottom: 1px solid {accent}; }
.mc-report-card strong { color: {text}; }

/* ── 소스 카드 (정확한 출처) ── */
.mc-source-group-label { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: {muted} !important; margin: 18px 0 8px; }
.mc-source-card { display: flex; gap: 10px; align-items: flex-start; background: {surface}; border: 1px solid {border}; border-radius: 9px; padding: 11px 13px; margin-bottom: 6px; }
.mc-source-card:hover { border-color: {accent}; }
.mc-source-num { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; color: {muted}; flex-shrink: 0; padding-top: 1px; }
.mc-source-title { font-size: 13px; font-weight: 500; color: {text} !important; line-height: 1.5; text-decoration: none; display: block; }
.mc-source-title:hover { color: {accent} !important; }
.mc-source-meta { font-size: 11px; color: {muted} !important; margin-top: 3px; }

/* ── 요약 카드 ── */
.mc-summary-card { background: {accent_soft}; border: 1px solid {border}; border-radius: 12px; padding: 18px 22px; margin-bottom: 18px; font-size: 14px; line-height: 1.75; color: {text} !important; }
.mc-summary-label { font-size: 10.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: {accent} !important; margin-bottom: 6px; }

/* ── 주가 위젯 ── */
.mc-stock-label { font-size: 9.5px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: {muted} !important; padding: 9px 0 4px; border-bottom: 1px solid {border}; margin-bottom: 2px; }
.mc-stock-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid {border}; }
.mc-stock-row:last-child { border-bottom: none; }
.mc-stock-name  { font-size: 11px; font-weight: 500; color: {text2} !important; }
.mc-stock-price { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; text-align: right; }
.mc-stock-chg   { font-size: 10px; margin-left: 4px; }
.up-color   { color: {up}   !important; }
.down-color { color: {down} !important; }
.flat-color { color: {flat} !important; }

/* ── 아카이브 ── */
.mc-archive-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 2px; border-bottom: 1px solid {border}; font-size: 13px; color: {text2} !important; }
.mc-archive-row:last-child { border-bottom: none; }

a { text-decoration: none; }
hr { border-color: {border} !important; margin: 12px 0 !important; }
</style>
"""


def inject_css(st_module, theme):
    # 순수 .format()은 CSS 블록의 리터럴 중괄호와 충돌하므로 토큰 치환 방식 사용.
    css = _CSS_TEMPLATE
    for key, value in theme.items():
        css = css.replace("{" + key + "}", value)
    # <link>와 <style>을 한 번에 넘기면 CommonMark가 <link>를 시작 태그로 보고
    # 블록 타입을 결정해 버려, CSS 안의 빈 줄에서 HTML 블록이 끊겨 원문이 그대로 노출된다.
    # <style>이 각자 블록의 첫 줄이 되도록 반드시 분리 호출한다.
    st_module.markdown(FONT_LINK, unsafe_allow_html=True)
    st_module.markdown(css.strip(), unsafe_allow_html=True)
