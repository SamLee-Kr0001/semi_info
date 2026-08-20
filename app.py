"""
app.py
────────
MatChain Insight — 반도체 소재 기술 동향 · 기업 변화 · SCM · 공급망 리포트 웹사이트.
한국·미국·일본·대만·중국 5개국 뉴스를 출처 그대로 수집해 Gemini로 인용 기반 심층 리포트를 생성한다.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

import streamlit as st

from core import gemini
from core import history as hist_store
from core import keywords as kw_store
from core import news as news_store
from core import render as rmod
from core import stocks as stock_store
from core import theme as theme_mod

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="MatChain Insight", page_icon="🧬")


# ══════════════════════════════════════════════════════════════
# Secrets / 환경
# ══════════════════════════════════════════════════════════════
def _secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return None


GITHUB_TOKEN = _secret("GITHUB_TOKEN")
REPO_NAME = _secret("REPO_NAME")

api_key = ""

# ══════════════════════════════════════════════════════════════
# 세션 상태 / 테마
# ══════════════════════════════════════════════════════════════
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "keywords" not in st.session_state:
    st.session_state.keywords = kw_store.load_keywords(GITHUB_TOKEN, REPO_NAME)
if "history" not in st.session_state:
    st.session_state.history = hist_store.load_history(GITHUB_TOKEN, REPO_NAME)

T = theme_mod.get_theme(st.session_state.dark_mode)
theme_mod.inject_css(st, T)


# ══════════════════════════════════════════════════════════════
# 공통 헬퍼
# ══════════════════════════════════════════════════════════════
def clean_text(text):
    return re.sub(r"<[^>]+>", "", text or "")


def today_kst_str():
    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
    target_date = (now_kst - timedelta(days=1)).date() if now_kst.hour < 6 else now_kst.date()
    return target_date.strftime("%Y-%m-%d"), now_kst


def render_keyword_manager(category):
    c1, c2 = st.columns([3, 1])
    new_kw = c1.text_input(
        "키워드 추가", placeholder="예: HBM, CMP 슬러리, 하이브리드 본딩",
        label_visibility="collapsed", key=f"kw_input_{category}",
    )
    if c2.button("추가", use_container_width=True, key=f"kw_add_{category}"):
        if new_kw and new_kw not in st.session_state.keywords[category]:
            st.session_state.keywords[category].append(new_kw)
            kw_store.save_keywords(st.session_state.keywords, GITHUB_TOKEN, REPO_NAME)
            st.rerun()

    curr = st.session_state.keywords.get(category, [])
    if curr:
        st.write("")
        num_cols = min(len(curr), 6)
        cols = st.columns(num_cols)
        for i, kwd in enumerate(curr):
            if cols[i % num_cols].button(f"{kwd} ×", key=f"kw_del_{category}_{i}_{kwd}"):
                st.session_state.keywords[category].remove(kwd)
                kw_store.save_keywords(st.session_state.keywords, GITHUB_TOKEN, REPO_NAME)
                st.rerun()


def render_sources(articles):
    # 레거시 기사(국가 태그 없음)는 한국 소스로 간주한다.
    country_order = [c for c in ["KR", "US", "JP", "TW", "CN"] if any((a.get("Country") or "KR") == c for a in articles)]
    for c in country_order:
        conf = news_store.COUNTRIES[c]
        group = [(i, a) for i, a in enumerate(articles) if (a.get("Country") or "KR") == c]
        st.markdown(
            f"<div class='mc-source-group-label'>{conf['flag']} {conf['label']} · {len(group)}건</div>",
            unsafe_allow_html=True,
        )
        for i, item in group:
            link = rmod.sanitize_url(item.get("Link", "#"))
            title = clean_text(item.get("TitleKo") or item.get("Title", ""))
            date = item.get("ParsedDate") or item.get("Date", "")
            source = clean_text(item.get("Source", ""))
            st.markdown(
                f"<a href='{link}' target='_blank' style='text-decoration:none;'>"
                f"<div class='mc-source-card'>"
                f"<div class='mc-source-num'>[{i+1}]</div>"
                f"<div style='flex:1;min-width:0;'>"
                f"<div class='mc-source-title'>{title}</div>"
                f"<div class='mc-source-meta'>{source} · {date}</div>"
                f"</div></div></a>",
                unsafe_allow_html=True,
            )


def render_report(entry):
    summary = clean_text(rmod.extract_executive_summary(entry["report"]))
    st.markdown(
        f"<div class='mc-summary-card'><div class='mc-summary-label'>Executive Summary</div>{summary}</div>",
        unsafe_allow_html=True,
    )

    articles = entry.get("articles", [])
    linked = rmod.inject_citation_links(entry["report"], articles)
    body_html = rmod.markdown_to_html(linked)
    st.markdown(f"<div class='mc-report-card'>{body_html}</div>", unsafe_allow_html=True)

    if articles:
        counts = {}
        for a in articles:
            counts[a.get("Country", "KR")] = counts.get(a.get("Country", "KR"), 0) + 1
        chips = "".join(
            f"<span class='mc-flag-chip'>{news_store.COUNTRIES[c]['flag']} {news_store.COUNTRIES[c]['label']} {n}</span>"
            for c, n in counts.items() if c in news_store.COUNTRIES
        )
        st.markdown(chips, unsafe_allow_html=True)
        with st.expander(f"📎 참고 기사 전체 보기 ({len(articles)}건)", expanded=False):
            render_sources(articles)

    gen_at = entry.get("generated_at")
    if gen_at:
        st.markdown(
            f"<div style='font-size:11px;color:{T['muted']};margin-top:6px;'>생성 시각 · {gen_at}</div>",
            unsafe_allow_html=True,
        )


def run_generation(category, target_date_str, search_days, countries, per_country_limit, auto_generated=False):
    status = st.status("🚀 리포트 생성 중...", expanded=True)
    kws = st.session_state.keywords.get(category, [])
    if not kws:
        status.update(label="⚠️ 키워드가 없습니다. 먼저 키워드를 추가하세요.", state="error")
        return

    status.write(f"📡 {len(countries)}개국 뉴스 수집 중 (키워드 {len(kws)}개)...")
    articles = news_store.collect_news(
        api_key, kws, days=search_days, per_country_limit=per_country_limit,
        countries=countries, limit=40,
    )
    if not articles:
        status.update(label="❌ 수집된 뉴스가 없습니다. 키워드나 기간을 조정해보세요.", state="error")
        return

    status.write(f"🧠 AI 심층 분석 중... ({len(articles)}건 근거)")
    success, result = gemini.generate_report(api_key, articles, category_label=category)
    if not success:
        status.update(label="⚠️ AI 분석 실패", state="error")
        st.error(result)
        return

    status.write("💾 저장 중...")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.session_state.history = hist_store.save_report(
        st.session_state.history, category, target_date_str, result, articles,
        auto_generated=auto_generated, generated_at=generated_at,
    )
    hist_store.persist(st.session_state.history, GITHUB_TOKEN, REPO_NAME)
    status.update(label="🎉 완료!", state="complete")
    st.rerun()


# ══════════════════════════════════════════════════════════════
# 주가 위젯
# ══════════════════════════════════════════════════════════════
if not hasattr(st, "fragment"):
    def _dummy_fragment(**kwargs):
        return lambda f: f
    st.fragment = _dummy_fragment


@st.cache_data(ttl=300)
def _cached_stock_prices():
    return stock_store.fetch_all()


@st.fragment(run_every=300)
def render_stock_widget():
    if st.button("↻ 새로고침", use_container_width=True, key="stock_refresh"):
        _cached_stock_prices.clear()
    prices = _cached_stock_prices()
    for group_name, tickers in stock_store.STOCK_GROUPS.items():
        st.markdown(f"<div class='mc-stock-label'>{group_name}</div>", unsafe_allow_html=True)
        for name in tickers:
            q = prices.get(name)
            if not q:
                continue
            price = q["price"]
            fmt_price = f"{q['currency']}{price:,.0f}" if q["currency"] in ("₩", "¥") else f"{q['currency']}{price:,.2f}"
            if q["change"] > 0:
                cls, arrow, sign = "up-color", "▲", "+"
            elif q["change"] < 0:
                cls, arrow, sign = "down-color", "▼", ""
            else:
                cls, arrow, sign = "flat-color", "-", ""
            st.markdown(
                f"<div class='mc-stock-row'><span class='mc-stock-name'>{name}</span>"
                f"<span class='mc-stock-price {cls}'>{fmt_price}"
                f"<span class='mc-stock-chg'>{arrow}{sign}{q['pct']:.2f}%</span></span></div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        """
        <div class="mc-logo">
            <div class="mc-logo-mark">🧬</div>
            <div>
                <div class="mc-logo-text">MatChain Insight</div>
                <div class="mc-logo-sub">Semiconductor Materials · Supply Chain</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dark_toggled = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark_toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggled
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    selected_category = st.radio(
        "카테고리", kw_store.CATEGORIES, index=0, label_visibility="collapsed",
        format_func=lambda c: f"{kw_store.CATEGORY_META[c]['icon']}  {c}",
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    with st.expander("🔐 API Key"):
        user_key = st.text_input(
            "Gemini API Key", type="password", label_visibility="collapsed",
            placeholder="Gemini API Key를 입력하세요",
        )
        if user_key:
            api_key = user_key
        elif _secret("GEMINI_API_KEY"):
            api_key = _secret("GEMINI_API_KEY")

    if GITHUB_TOKEN:
        st.markdown(
            "<div style='margin-top:10px'><span class='mc-badge'>✓ GitHub Sync On</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    with st.expander("📈 Materials & Chipmakers", expanded=True):
        render_stock_widget()


# ══════════════════════════════════════════════════════════════
# 메인 콘텐츠
# ══════════════════════════════════════════════════════════════
meta = kw_store.CATEGORY_META[selected_category]
st.markdown(
    f"<div class='mc-cat-header'><span class='mc-cat-icon'>{meta['icon']}</span>"
    f"<span class='mc-cat-title'>{selected_category}</span></div>"
    f"<div class='mc-cat-desc'>{meta['desc']}</div>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='mc-banner'>⏱️ 매일 06:00 KST GitHub Actions가 4개 카테고리 리포트를 자동 생성합니다. "
    "아래에서 수동 생성도 가능합니다.</div>",
    unsafe_allow_html=True,
)

target_date_str, now_kst = today_kst_str()

with st.expander("⚙️ 키워드 및 수집 설정", expanded=False):
    render_keyword_manager(selected_category)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    search_days = col1.slider("검색 기간(일)", 1, 14, 3, key=f"days_{selected_category}")
    country_options = {f"{c['flag']} {c['label']}": code for code, c in news_store.COUNTRIES.items()}
    selected_labels = col2.multiselect(
        "수집 국가", options=list(country_options.keys()), default=list(country_options.keys()),
        key=f"countries_{selected_category}",
    )
    selected_countries = [country_options[l] for l in selected_labels] or list(news_store.COUNTRIES.keys())

tab_today, tab_archive = st.tabs(["📰 오늘의 리포트", "🗂️ 아카이브"])

with tab_today:
    col_date, col_refresh = st.columns([4, 1])
    with col_date:
        st.markdown(
            f"<div style='font-size:12px;color:{T['muted']};padding-top:6px;'>"
            f"Report Date &nbsp;·&nbsp; <b style='color:{T['text2']}'>{target_date_str}</b></div>",
            unsafe_allow_html=True,
        )
    with col_refresh:
        if st.button("↻ 최신화", use_container_width=True, key="reload_history"):
            st.session_state.history = hist_store.load_history(GITHUB_TOKEN, REPO_NAME)
            st.rerun()

    entry = hist_store.get_report(st.session_state.history, selected_category, target_date_str)

    if entry:
        auto_tag = " &nbsp;<span class='mc-badge'>AUTO</span>" if entry.get("auto_generated") else ""
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:14px;'>"
            f"<span style='color:#1F6B4C;font-size:13px;font-weight:700;'>✅ 리포트 생성 완료</span>{auto_tag}</div>",
            unsafe_allow_html=True,
        )
        render_report(entry)
        if st.button("🔄 리포트 다시 만들기", disabled=not bool(api_key), key="regen"):
            run_generation(selected_category, target_date_str, search_days, selected_countries, per_country_limit=3)
    else:
        next_run_dt = target_date_str if now_kst.hour < 6 else (now_kst + timedelta(days=1)).strftime("%Y-%m-%d")
        st.info(f"📢 오늘({target_date_str}) '{selected_category}' 리포트가 아직 없습니다. 다음 자동 생성: **{next_run_dt} 06:00 KST**")
        if st.button("🚀 지금 바로 리포트 생성", type="primary", disabled=not bool(api_key), key="gen_now"):
            if not api_key:
                st.warning("API Key를 먼저 입력해주세요.")
            else:
                run_generation(selected_category, target_date_str, search_days, selected_countries, per_country_limit=3)

with tab_archive:
    archive_entries = [
        e for e in hist_store.list_for_category(st.session_state.history, selected_category)
        if e["date"] != target_date_str
    ]
    archive_entries.sort(key=lambda e: e["date"], reverse=True)
    if not archive_entries:
        st.info("아직 아카이브된 리포트가 없습니다.")
    for e in archive_entries:
        with st.expander(f"{e['date']} · {selected_category}", expanded=False):
            render_report(e)
