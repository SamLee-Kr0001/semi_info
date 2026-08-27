"""
과제관리 대시보드 (Streamlit + GitHub)
────────────────────────────────────────────────────────────
회의록 텍스트를 과제/정보로 자동 분류하고 진척을 이력 관리한다.
데이터는 GitHub 저장소의 tasks_data.json에 동기화된다.

필요한 Streamlit Secrets:
  GITHUB_TOKEN : repo read/write 권한 토큰
  REPO_NAME    : "username/repo-name"

AI API 키가 필요 없다 — 분류·매칭은 모두 규칙 기반으로 동작한다.
"""

import base64
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import streamlit as st
from github import Github

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="과제관리 대시보드", page_icon="📋")

# ════════════════════════════════════════════════════════════
# 0. 상수
# ════════════════════════════════════════════════════════════
DATA_FILE = "tasks_data.json"
STATUS = ["접수", "진행중", "완료", "보류"]
STATUS_HEX = {"접수": "#9CA3AF", "진행중": "#2563EB", "완료": "#059669", "보류": "#D97706"}
TASK_CATS = ["소재개발", "품질", "R&D기술", "설비/인프라", "조직/인력",
             "수급/SCM", "AI/DX", "환경", "경영현안", "미분류"]
INFO_CATS = ["소재", "System", "운영", "인물", "기술"]


def today_kst() -> date:
    return (datetime.now(timezone.utc) + timedelta(hours=9)).date()


def today_str() -> str:
    return today_kst().strftime("%Y-%m-%d")


# ════════════════════════════════════════════════════════════
# 1. GitHub I/O
# ════════════════════════════════════════════════════════════
def _secret(key, default=None):
    """secrets.toml이 없는 로컬 실행에서도 크래시하지 않도록 방어."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def github_enabled() -> bool:
    return bool(_secret("GITHUB_TOKEN") and _secret("REPO_NAME"))


def _repo():
    return Github(_secret("GITHUB_TOKEN")).get_repo(_secret("REPO_NAME"))


def load_data() -> dict:
    """GitHub → 로컬 파일 → 빈 데이터 순으로 로드."""
    if github_enabled():
        try:
            contents = _repo().get_contents(DATA_FILE)
            if contents.encoding == "none":
                # 1MB 초과 시 Contents API가 inline content를 주지 않으므로 Blob API 사용
                blob = _repo().get_git_blob(contents.sha)
                raw = base64.b64decode(blob.content).decode("utf-8")
            else:
                raw = contents.decoded_content.decode("utf-8")
            return _normalize(json.loads(raw))
        except Exception as e:
            logger.warning(f"GitHub 로드 실패: {e}")
            st.session_state.td_load_error = str(e)

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return _normalize(json.load(f))
        except Exception as e:
            logger.warning(f"로컬 로드 실패: {e}")

    return {"tasks": [], "info": []}


def _normalize(d) -> dict:
    if isinstance(d, list):          # 구 스키마 방어
        d = {"tasks": d, "info": []}
    d.setdefault("tasks", [])
    d.setdefault("info", [])
    for t in d["tasks"]:
        t.setdefault("history", [])
        t.setdefault("progress", 0)
        t.setdefault("status", "접수")
        for k in ("owner", "deadline", "goal", "category"):
            t.setdefault(k, "")
    return d


def save_data(data: dict, message: str = "") -> tuple[bool, str]:
    """로컬에 쓰고 GitHub에 커밋한다."""
    payload = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(payload)
    except Exception as e:
        logger.warning(f"로컬 저장 실패: {e}")

    if not github_enabled():
        return False, "GitHub Secrets(GITHUB_TOKEN, REPO_NAME)가 설정되지 않아 로컬에만 저장했습니다."

    msg = message or f"[과제관리] Update {DATA_FILE} - {today_str()}"
    try:
        repo = _repo()
        try:
            existing = repo.get_contents(DATA_FILE)
            repo.update_file(existing.path, msg, payload, existing.sha)
        except Exception:
            repo.create_file(DATA_FILE, msg, payload)
        return True, "GitHub에 저장했습니다."
    except Exception as e:
        logger.error(f"GitHub 저장 실패: {e}")
        return False, f"GitHub 저장 실패: {e}"


# ════════════════════════════════════════════════════════════
# 2. 회의록 파서 — 규칙 기반 (외부 API 불필요)
# ════════════════════════════════════════════════════════════
DATE_RE = re.compile(r"^\s*(20\d{2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*\.?\s*(?:[(（]([^)）]*)[)）])?\s*$")

# 실행/조치를 요구하는 표현 (과제 신호)
ACT_RE = re.compile(
    r"(할\s*것|하기로|하자|해라|해야|필요|추진|검토|구축|확보|반영|개선|수립|정의|요청|통보|점검|"
    r"만들|찾자|제안|도출|대응|준비|신설|생성|변경|전환|적용|산정|조사|연동|명확히|의사결정|"
    r"예정|진행할|운용\s*방안|방안|TF|과제|지시|착수|시작|완료|ASAP|미팅\s*Call)")
# 사실 서술 표현 (정보 신호)
FACT_RE = re.compile(
    r"(수준|달성|불만|현황|분포|명단|참석|이다|입니다|임\.?$|함\.?$|있다|없다|이며|상황|특성|담당[:：])")

# 카테고리 키워드 (가중치가 클수록 우선)
CAT_TASK = [
    (re.compile(r"(Dashboard|대시보드|Portal|library|라이브러리|해커톤|DX|디지털|AI)", re.I), "AI/DX", 3),
    (re.compile(r"(환경|냉매|Recycle|탄소|탄관위|Plastic)", re.I), "환경", 3),
    (re.compile(r"(요소기술|HTRS|P-1|P-2|TD\b|integration|CDP|MTS|Platform|Vehicle|DtS|N\+\d|DRAM|NAND|단위공정|협의체|Tech)", re.I), "R&D기술", 2),
    (re.compile(r"(장비|창고|FAB|설비|SoW|도급|입주|Epi|Etch|CLN|온도|인프라|비용\s*처리)", re.I), "설비/인프라", 2),
    (re.compile(r"(품질|Q-?day|VOC|Audit|하자|불량|검증|유효기간|Bottle)", re.I), "품질", 2),
    (re.compile(r"(수급|공급|구매|다변화|재고|SCM|BP\s*가격)", re.I), "수급/SCM", 2),
    (re.compile(r"(인력|교육|출향|조직|파견|융합\s*Eng|채용|동기부여|인사)", re.I), "조직/인력", 2),
    (re.compile(r"(KPI|OI\b|보상|부회장|경영|NDA|1on1|리뷰|포상)", re.I), "경영현안", 2),
    (re.compile(r"(소재|PR\b|Slurry|Precursor|TEOS|MLR|MLA|HF\b|CuMn|Moly|Filter|SP7000|SC2M0|etchant|wt%|화학|separation)", re.I), "소재개발", 1),
]
CAT_INFO = [
    # 인물: "이름+직급" 또는 "이름, 이름" 나열만 인정 (직급 단독어는 제외)
    (re.compile(r"([가-힣]{2,3}\s*(TL\b|팀장|담당자|부문장|책임|수석|위원))|([가-힣]{3}\s*[,、+]\s*[가-힣]{3})|(담당[:：]\s*[가-힣]{2,3})"), "인물"),
    (re.compile(r"(소재|PR\b|Slurry|Precursor|TEOS|MLR|HF\b|CuMn|Moly|SP7000|Abrasive|wt%|nm|해상도|peeling|PGMEA|separation)", re.I), "소재"),
    (re.compile(r"(Portal|Dashboard|System|Platform|HTRS|PLM|DB|Tech\s*scheme|Logic|AI\b|장비|scheme|구조)", re.I), "System"),
    (re.compile(r"(KPI|R&R|조직|일정|Open|입주|보고|회의|협의체|참여|분포|총평|목표|예산|비용)", re.I), "운영"),
]


def guess_task_cat(s: str) -> str:
    best, score = "미분류", 0
    for rx, cat, w in CAT_TASK:
        hits = len(rx.findall(s))
        if hits and hits * w > score:
            best, score = cat, hits * w
    return best


def guess_info_cat(s: str) -> str:
    for rx, cat in CAT_INFO:
        if rx.search(s):
            return cat
    return "기술"


def guess_status(s: str) -> str:
    done = re.search(r"완료(?![가-힣])", s) is not None
    wip = re.search(r"(진행\s*중|추진\s*중|검토\s*중|개발\s*중|착수|시작|예정|중이)", s) is not None
    if re.search(r"(보류|홀드|중단|재논의)", s):
        return "보류"
    if done and wip:      # "PCN 완료. P&T 확장 검토 중" → 아직 진행중
        return "진행중"
    if done:
        return "완료"
    if wip:
        return "진행중"
    return "접수"


def extract_owner(s: str) -> str:
    m = re.search(r"([가-힣]{2,3})\s*(TL|팀장|담당|부문장)", s)
    if m:
        return m.group(0).strip()
    names = re.findall(r"[가-힣]{3}(?=\s*[,、]|\s*\+)", s)
    if len(names) >= 2:
        return ", ".join(names)
    return ""


def extract_deadline(s: str) -> str:
    Y = today_kst().year
    m = re.search(r"'?(\d{2})[.\-](\d{1,2})\s*월", s)
    if m:
        return f"20{m.group(1)}-{int(m.group(2)):02d}-28"
    m = re.search(r"\((\d{1,2})/(\d{1,2})\)", s)
    if m:
        return f"{Y}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"(?:^|[^0-9])(\d{1,2})/(\d{1,2})(?![0-9])", s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        return f"{Y}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"'(\d{2})\.(\d{1,2})", s)
    if m:
        return f"20{m.group(1)}-{int(m.group(2)):02d}-01"
    m = re.search(r"(?:^|[^0-9a-zA-Z])(\d{1,2})\s*월(?!\s*[Rr])", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{Y}-{int(m.group(1)):02d}-28"
    return ""


def make_title(s: str) -> str:
    t = re.sub(r"^[\s\-–—•*+>]+", "", s)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.split(r"\s*(?:-->|→)\s*", t)[0]
    t = re.sub(r"[.。]\s*$", "", t)
    return t[:44] + "…" if len(t) > 44 else t


def _norm(s: str) -> str:
    return re.sub(r"[^가-힣a-z0-9]", "", str(s).lower())


def dice(a: str, b: str) -> float:
    """문자 bigram Dice 계수."""
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    A = [a[i:i + 2] for i in range(len(a) - 1)]
    B = [b[i:i + 2] for i in range(len(b) - 1)]
    if not A or not B:
        return 0.0
    pool = {}
    for g in A:
        pool[g] = pool.get(g, 0) + 1
    hit = 0
    for g in B:
        if pool.get(g, 0) > 0:
            pool[g] -= 1
            hit += 1
    return 2 * hit / (len(A) + len(B))


def key_tokens(s: str) -> set:
    """TEOS, SP7000, Q-day 같은 고유 식별자성 토큰."""
    return {x.lower().rstrip(".-") for x in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{2,}", str(s))}


def best_match(text: str, tasks: list) -> tuple:
    """(과제, 유사도) 또는 (None, 0)."""
    best, score = None, 0.0
    kt = key_tokens(text)
    for t in tasks:
        sc = max(dice(text, t["title"]), dice(text, t["title"] + " " + t.get("goal", "")) * 0.92)
        shared = kt & key_tokens(t["title"] + " " + t.get("goal", ""))
        if shared and sc >= 0.18:
            sc = max(sc, 0.45 + 0.05 * min(len(shared), 3))
        if sc > score:
            best, score = t, sc
    return (best, min(score, 1.0)) if score >= 0.34 else (None, 0.0)


def parse_meeting_text(raw: str) -> list:
    """날짜 헤더를 인식하고 항목 단위로 쪼갠다. '-->', '+', 들여쓰기는 앞 항목에 병합."""
    items, buf = [], None
    cur_date, cur_meet = today_str(), ""

    def flush():
        nonlocal buf
        if buf and len(buf["text"].strip()) >= 4:
            items.append(buf)
        buf = None

    for ln in raw.split("\n"):
        t = ln.strip()
        if not t:
            continue
        dm = DATE_RE.match(t)
        if dm:
            flush()
            cur_date = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
            cur_meet = (dm.group(4) or "").strip()
            continue
        is_cont = bool(re.match(r"^(-->|→|\+)", t)) or (re.match(r"^\s{2,}", ln) and buf)
        if is_cont and buf:
            buf["text"] += " " + re.sub(r"^(-->|→|\+)\s*", "", t)
            continue
        flush()
        buf = {"date": cur_date, "meeting": cur_meet, "text": re.sub(r"^[\-–—•*]\s*", "", t)}
    flush()
    return items


def classify(items: list, tasks: list) -> list:
    """항목을 과제/정보로 분류하고 기존 과제와 매칭한다.

    · 담당·납기·진척율은 자동 입력하지 않는다 (수동 입력 원칙).
      텍스트에서 찾은 값은 sug_* 필드에 '제안'으로만 담는다.
    · 정보로 분류됐어도 기존 과제와 동일 주제면 별도 정보가 아니라
      해당 과제의 진척 이력으로 등록한다 (중복 통합).
    """
    out = []
    for it in items:
        s = it["text"]
        act = len(ACT_RE.findall(s))
        fact = len(FACT_RE.findall(s))
        is_q = bool(re.search(r"[?？]\s*$", s))
        name_only = bool(re.match(r"^[^:：]{0,14}[:：]?\s*[가-힣]{3}(\s*[,+、]\s*[가-힣]{3})+\s*$", s))

        if name_only:
            kind = "info"
        elif is_q and act == 0:
            kind = "info"
        elif act > fact:
            kind = "task"
        else:
            kind = "info"          # 동점·사실 우세 → 정보 (안전한 기본값)

        matched, score = best_match(s, tasks)
        if kind == "info" and matched:      # 중복 통합
            kind = "task"

        row = {
            "포함": True,
            "유형": "과제" if kind == "task" else "정보",
            "제목": make_title(s),
            "원문": s,
            "날짜": it["date"],
            "회의": it["meeting"] or "-",
        }
        if kind == "task":
            row.update({
                "저장방식": f"🔗 {matched['title']} [{matched['id']}]" if matched else "🆕 신규 과제",
                "분류": guess_task_cat(s),
                "상태": guess_status(s),
                "담당": "", "납기": None, "진척율": 0,
                "제안담당": extract_owner(s),
                "제안납기": extract_deadline(s),
                "매칭": f"{score*100:.0f}%" if matched else "",
            })
        else:
            # 정보 항목은 상태·담당·납기·진척율을 쓰지 않지만,
            # 표의 열 dtype을 과제 행과 맞추기 위해 기본값을 채워 둔다.
            row.update({
                "저장방식": "🆕 신규 정보", "분류": guess_info_cat(s), "상태": "접수",
                "담당": "", "납기": None, "진척율": 0,
                "제안담당": "", "제안납기": "", "매칭": "",
            })
        out.append(row)
    return out


# ════════════════════════════════════════════════════════════
# 3. 날짜 유틸
# ════════════════════════════════════════════════════════════
def dday(deadline: str):
    """(라벨, 남은일수) 또는 (None, None)."""
    if not deadline:
        return None, None
    try:
        d = datetime.strptime(str(deadline)[:10], "%Y-%m-%d").date()
    except Exception:
        return None, None
    n = (d - today_kst()).days
    if n < 0:
        return f"D+{abs(n)}", n
    if n == 0:
        return "D-Day", 0
    return f"D-{n}", n


def to_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date() if s else None
    except Exception:
        return None


def fmt_date(v) -> str:
    """data_editor가 돌려준 날짜 값을 'YYYY-MM-DD' 문자열로. 미입력은 빈 문자열.

    pd.NaT는 datetime의 서브클래스라 isinstance 검사를 통과하므로
    pd.isna()로 먼저 걸러야 'NaT' 문자열이 저장되는 것을 막을 수 있다.
    """
    if v is None or pd.isna(v):
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    return str(v)[:10]


# ════════════════════════════════════════════════════════════
# 4. 세션 상태
# ════════════════════════════════════════════════════════════
if "td_data" not in st.session_state:
    st.session_state.td_data = load_data()
if "td_dirty" not in st.session_state:
    st.session_state.td_dirty = False
if "td_review" not in st.session_state:
    st.session_state.td_review = None

DATA = st.session_state.td_data
TASKS, INFO = DATA["tasks"], DATA["info"]


def mark_dirty():
    st.session_state.td_dirty = True


def next_id(prefix: str, items: list) -> str:
    nums = [int(x["id"][1:]) for x in items if re.fullmatch(rf"{prefix}\d+", str(x.get("id", "")))]
    return f"{prefix}{(max(nums) + 1) if nums else 1:03d}"


# ════════════════════════════════════════════════════════════
# 5. 사이드바
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📋 과제관리")
    st.caption("회의 Text → 과제 분류 · 진척 이력 · 정보 저장소")

    if github_enabled():
        st.success(f"GitHub 연결됨\n\n`{_secret('REPO_NAME')}`", icon="✅")
    else:
        st.warning(
            "GitHub 미연결 — 변경사항이 저장소에 반영되지 않습니다.\n\n"
            "Streamlit Secrets에 `GITHUB_TOKEN`, `REPO_NAME`을 설정하세요.",
            icon="⚠️",
        )

    st.divider()
    if st.session_state.td_dirty:
        st.warning("저장되지 않은 변경이 있습니다.", icon="✏️")
    else:
        st.caption("모든 변경이 저장되었습니다.")

    if st.button("💾 GitHub에 저장", type="primary", use_container_width=True,
                 disabled=not st.session_state.td_dirty):
        ok, msg = save_data(DATA)
        if ok:
            st.session_state.td_dirty = False
            st.success(msg, icon="✅")
        else:
            st.error(msg, icon="⚠️")
        st.rerun()

    if st.button("↻ GitHub에서 다시 불러오기", use_container_width=True):
        if st.session_state.td_dirty and not st.session_state.get("td_confirm_reload"):
            st.session_state.td_confirm_reload = True
            st.warning("저장되지 않은 변경이 사라집니다. 한 번 더 누르면 진행합니다.")
        else:
            st.session_state.td_data = load_data()
            st.session_state.td_dirty = False
            st.session_state.td_confirm_reload = False
            st.rerun()

    st.divider()
    st.download_button(
        "⬇ 백업 (JSON)",
        json.dumps(DATA, ensure_ascii=False, indent=2, default=str),
        file_name=f"과제관리_{today_str()}.json",
        mime="application/json",
        use_container_width=True,
    )

# ════════════════════════════════════════════════════════════
# 6. 메인
# ════════════════════════════════════════════════════════════
st.title("과제관리 대시보드")
st.caption("회의록 텍스트를 붙여넣으면 과제/정보로 자동 분류하고, 기존 과제는 진척 이력으로 갱신합니다. "
           "담당·납기·진척율은 직접 입력합니다.")

tab_dash, tab_ingest, tab_tasks, tab_info, tab_hist = st.tabs(
    ["📊 대시보드", "📥 회의록 입력", "📁 과제 목록", "🗃️ 정보 저장소", "🕒 전체 이력"]
)

# ── 대시보드 ────────────────────────────────────────────────
with tab_dash:
    if not TASKS:
        st.info("등록된 과제가 없습니다. '📥 회의록 입력' 탭에서 시작하세요.")
    else:
        cnt = {s: sum(1 for t in TASKS if t["status"] == s) for s in STATUS}
        open_tasks = [t for t in TASKS if t["status"] != "완료"]
        overdue = sum(1 for t in open_tasks if (dday(t["deadline"])[1] or 1) < 0)
        soon = sum(1 for t in open_tasks
                   if dday(t["deadline"])[1] is not None and 0 <= dday(t["deadline"])[1] <= 14)
        avg = round(sum(int(t.get("progress") or 0) for t in TASKS) / len(TASKS))

        c = st.columns(6)
        c[0].metric("전체 과제", len(TASKS), help=f"정보 {len(INFO)}건 별도 보관")
        c[1].metric("진행중", cnt["진행중"], help=f"접수 {cnt['접수']} · 보류 {cnt['보류']}")
        c[2].metric("완료", cnt["완료"], f"{round(cnt['완료']/len(TASKS)*100)}%")
        c[3].metric("마감 임박", soon, help="14일 이내")
        c[4].metric("납기 초과", overdue, help="즉시 조치 필요")
        c[5].metric("평균 진척율", f"{avg}%")

        no_owner = sum(1 for t in TASKS if not t.get("owner"))
        no_due = sum(1 for t in TASKS if not t.get("deadline"))
        if no_owner or no_due:
            st.warning(f"담당 미입력 **{no_owner}건** · 납기 미입력 **{no_due}건** — "
                       "'📁 과제 목록' 탭에서 직접 입력하세요.", icon="✏️")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("##### 상태 분포")
            df_s = pd.DataFrame({"상태": STATUS, "건수": [cnt[s] for s in STATUS]})
            fig = px.pie(df_s, names="상태", values="건수", hole=0.55, color="상태",
                         color_discrete_map=STATUS_HEX)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=290,
                              paper_bgcolor="rgba(0,0,0,0)", legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
        with d2:
            st.markdown("##### 카테고리별 과제")
            cm = {}
            for t in TASKS:
                cm[t.get("category") or "미분류"] = cm.get(t.get("category") or "미분류", 0) + 1
            df_c = pd.DataFrame({"카테고리": list(cm), "건수": list(cm.values())}).sort_values("건수")
            fig2 = px.bar(df_c, x="건수", y="카테고리", orientation="h")
            fig2.update_traces(marker_color="#2563EB")
            fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=290,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### ⏰ 마감 임박 / 초과")
        due = [t for t in open_tasks if dday(t["deadline"])[1] is not None]
        due.sort(key=lambda t: dday(t["deadline"])[1])
        if due:
            st.dataframe(
                pd.DataFrame([{
                    "상태": t["status"], "과제명": t["title"], "담당": t.get("owner") or "–",
                    "납기": t["deadline"], "D-day": dday(t["deadline"])[0], "진척율": t.get("progress", 0),
                } for t in due[:10]]),
                hide_index=True, use_container_width=True,
                column_config={"진척율": st.column_config.ProgressColumn(
                    "진척율", min_value=0, max_value=100, format="%d%%")},
            )
        else:
            st.info("납기가 입력된 미완료 과제가 없습니다.")

        st.markdown("##### 🕒 최근 업데이트")
        rec = [{"날짜": h.get("date", ""), "회의": h.get("meeting", "-"),
                "과제": t["title"], "내용": h.get("note", "")}
               for t in TASKS for h in t.get("history", [])]
        rec.sort(key=lambda r: r["날짜"], reverse=True)
        st.dataframe(pd.DataFrame(rec[:12]), hide_index=True, use_container_width=True)

# ── 회의록 입력 ─────────────────────────────────────────────
with tab_ingest:
    st.info(
        "날짜 헤더(예: `2026. 08. 27 (팀장 현안회의)`)를 인식해 항목별로 나눈 뒤, "
        "**실행이 필요한 항목은 과제**로, **단순 사실·수치·인물 정보는 정보 저장소**로 분류합니다. "
        "기존 과제와 같은 주제면 신규 등록 대신 **해당 과제의 진척 이력으로 갱신**합니다. "
        "**담당·납기·진척율은 자동 입력하지 않으며**, 텍스트에서 찾은 값은 '제안' 열로만 보여줍니다.",
        icon="ℹ️",
    )
    raw = st.text_area(
        "회의록 텍스트", height=260, key="td_raw",
        placeholder="2026. 08. 27 (팀장 현안회의)\n - 도전보상제 - 미래tech 에 대한 과제가 있나?\n"
                    " - AI 관련 소재 구조 기반으로 library 구축\n   + Special NDA (BP IP로 막힘 - 우회방법을 찾자)",
    )

    b1, b2, _ = st.columns([1, 1, 4])
    if b1.button("🔍 분석하기", type="primary"):
        if not raw.strip():
            st.warning("회의록 텍스트를 입력하세요.")
        else:
            items = parse_meeting_text(raw)
            if not items:
                st.warning("추출된 항목이 없습니다.")
            else:
                st.session_state.td_review = classify(items, TASKS)
                st.session_state.td_review_ver = st.session_state.get("td_review_ver", 0) + 1
                st.rerun()
    if b2.button("지우기"):
        st.session_state.td_review = None
        st.rerun()

    review = st.session_state.td_review
    if review:
        n_task = sum(1 for r in review if r["유형"] == "과제")
        n_match = sum(1 for r in review if r["매칭"])
        st.success(f"{len(review)}개 추출 — 과제 {n_task} (기존 매칭 {n_match}) · 정보 {len(review)-n_task}")

        target_opts = ["🆕 신규 과제", "🆕 신규 정보"] + [f"🔗 {t['title']} [{t['id']}]" for t in TASKS]
        all_cats = TASK_CATS + INFO_CATS

        rdf = pd.DataFrame(review)
        # 빈 값이 'None' 문자열로 표시되지 않도록 dtype 정리
        rdf["납기"] = pd.to_datetime(rdf["납기"], errors="coerce")
        for col in ("담당", "제안담당", "제안납기", "매칭", "제목", "회의", "원문"):
            rdf[col] = rdf[col].fillna("").astype(str)
        rdf["상태"] = rdf["상태"].replace("", "접수")

        # st.data_editor는 key로 위젯 편집 상태를 유지하므로, 배경 데이터를 바꿀 때
        # (예: 제안값 일괄 적용) key도 함께 바꿔야 화면에 반영된다.
        edited = st.data_editor(
            rdf,
            hide_index=True, use_container_width=True, height=420,
            key=f"td_review_editor_{st.session_state.get('td_review_ver', 0)}",
            column_order=["포함", "유형", "저장방식", "제목", "분류", "상태",
                          "담당", "납기", "진척율", "제안담당", "제안납기", "매칭", "날짜", "회의", "원문"],
            column_config={
                "포함": st.column_config.CheckboxColumn("포함", width="small"),
                "유형": st.column_config.SelectboxColumn("유형", options=["과제", "정보"], width="small"),
                "저장방식": st.column_config.SelectboxColumn("저장 방식", options=target_opts, width="medium"),
                "제목": st.column_config.TextColumn("제목", width="medium"),
                "분류": st.column_config.SelectboxColumn("분류", options=all_cats, width="small"),
                "상태": st.column_config.SelectboxColumn("상태", options=STATUS, width="small"),
                "담당": st.column_config.TextColumn("담당 (직접 입력)", width="small"),
                "납기": st.column_config.DateColumn("납기 (직접 입력)", format="YYYY-MM-DD", width="small"),
                "진척율": st.column_config.NumberColumn("진척율", min_value=0, max_value=100, step=5, width="small"),
                "제안담당": st.column_config.TextColumn("제안 담당", disabled=True, width="small"),
                "제안납기": st.column_config.TextColumn("제안 납기", disabled=True, width="small"),
                "매칭": st.column_config.TextColumn("매칭", disabled=True, width="small"),
                "날짜": st.column_config.TextColumn("날짜", disabled=True, width="small"),
                "회의": st.column_config.TextColumn("회의", disabled=True, width="small"),
                "원문": st.column_config.TextColumn("원문", disabled=True, width="large"),
            },
        )

        a1, a2, _ = st.columns([1.4, 1.4, 3])
        if a1.button("↪ 제안값 일괄 적용 (담당·납기)"):
            rows = edited.to_dict("records")
            for r in rows:
                if not str(r["담당"] or "").strip() and r["제안담당"]:
                    r["담당"] = r["제안담당"]
                # bool(pd.NaT)는 True라서 `not r["납기"]`로는 미입력을 판별할 수 없다.
                if (r["납기"] is None or pd.isna(r["납기"])) and r["제안납기"]:
                    r["납기"] = to_date(r["제안납기"])
            st.session_state.td_review = rows
            st.session_state.td_review_ver = st.session_state.get("td_review_ver", 0) + 1
            st.rerun()

        if a2.button("✅ 확정 저장", type="primary"):
            n_new = n_upd = n_info = 0
            for r in edited.to_dict("records"):
                if not r["포함"]:
                    continue
                dstr = fmt_date(r["납기"])
                if r["유형"] == "과제":
                    entry = {
                        "date": r["날짜"], "meeting": r["회의"], "note": r["원문"],
                        "status": r["상태"] or "접수", "progress": int(r["진척율"] or 0),
                    }
                    tid = None
                    m = re.search(r"\[([TI]\d+)\]$", str(r["저장방식"]))
                    if m:
                        tid = m.group(1)
                    tgt = next((t for t in TASKS if t["id"] == tid), None) if tid else None
                    if tgt:
                        tgt["status"] = r["상태"] or tgt["status"]
                        tgt["progress"] = int(r["진척율"] or 0)
                        if r["담당"]:
                            tgt["owner"] = r["담당"]
                        if dstr:
                            tgt["deadline"] = dstr
                        tgt["history"].append(entry)
                        tgt["updated"] = today_str()
                        n_upd += 1
                    else:
                        TASKS.append({
                            "id": next_id("T", TASKS), "title": r["제목"], "goal": r["원문"],
                            "category": r["분류"] if r["분류"] in TASK_CATS else "미분류",
                            "owner": r["담당"], "deadline": dstr,
                            "status": r["상태"] or "접수", "progress": int(r["진척율"] or 0),
                            "created": r["날짜"], "updated": r["날짜"], "history": [entry],
                        })
                        n_new += 1
                else:
                    INFO.append({
                        "id": next_id("I", INFO),
                        "category": r["분류"] if r["분류"] in INFO_CATS else "기술",
                        "title": r["제목"], "content": r["원문"],
                        "date": r["날짜"], "meeting": r["회의"], "tags": [],
                    })
                    n_info += 1

            ok, msg = save_data(DATA, f"[과제관리] 회의록 반영 - 신규 {n_new} / 갱신 {n_upd} / 정보 {n_info}")
            st.session_state.td_dirty = not ok
            st.session_state.td_review = None
            (st.success if ok else st.warning)(
                f"저장 완료 — 신규 과제 {n_new} · 진척 갱신 {n_upd} · 정보 {n_info}. {msg}")
            st.rerun()

# ── 과제 목록 (목록형) ──────────────────────────────────────
with tab_tasks:
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    q = f1.text_input("검색", placeholder="제목·목표·담당", label_visibility="collapsed")
    fs = f2.multiselect("상태", STATUS, default=[], label_visibility="collapsed",
                        placeholder="상태 (전체)")
    cats_present = sorted({t.get("category") or "미분류" for t in TASKS})
    fc = f3.multiselect("카테고리", cats_present, default=[],
                        label_visibility="collapsed", placeholder="카테고리 (전체)")
    only_missing = f4.checkbox("미입력만 보기", help="담당 또는 납기가 비어 있는 과제")

    view = [t for t in TASKS
            if t["status"] in (fs or STATUS)
            and (t.get("category") or "미분류") in (fc or cats_present)
            and (not q or q.lower() in (t["title"] + t.get("goal", "") + t.get("owner", "")).lower())
            and (not only_missing or not t.get("owner") or not t.get("deadline"))]

    st.caption(f"{len(view)} / {len(TASKS)}건 표시 · "
               f"담당 미입력 {sum(1 for t in TASKS if not t.get('owner'))} · "
               f"납기 미입력 {sum(1 for t in TASKS if not t.get('deadline'))}  "
               f"— 표의 칸을 클릭해 담당·납기·진척율을 직접 입력하세요.")

    if not view:
        st.info("조건에 맞는 과제가 없습니다.")
    else:
        df = pd.DataFrame([{
            "id": t["id"], "상태": t["status"], "과제명": t["title"],
            "카테고리": t.get("category") or "미분류", "담당": t.get("owner", ""),
            "D-day": dday(t.get("deadline"))[0] or "–",
            "진척율": int(t.get("progress") or 0), "이력": len(t.get("history", [])),
        } for t in view])
        # 빈 납기가 'None' 문자열로 표시되지 않도록 datetime 컬럼으로 만든다 (미입력 → NaT → 빈칸)
        df.insert(5, "납기", pd.to_datetime(
            pd.Series([t.get("deadline") or None for t in view]), errors="coerce"))

        edited = st.data_editor(
            df, hide_index=True, use_container_width=True, height=560, key="td_task_editor",
            column_config={
                "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
                "상태": st.column_config.SelectboxColumn("상태", options=STATUS, width="small"),
                "과제명": st.column_config.TextColumn("과제명", width="large"),
                "카테고리": st.column_config.SelectboxColumn("카테고리", options=TASK_CATS, width="small"),
                "담당": st.column_config.TextColumn("담당", width="small"),
                "납기": st.column_config.DateColumn("납기", format="YYYY-MM-DD", width="small"),
                "D-day": st.column_config.TextColumn("D-day", disabled=True, width="small"),
                "진척율": st.column_config.NumberColumn("진척율 %", min_value=0, max_value=100, step=5, width="small"),
                "이력": st.column_config.NumberColumn("이력", disabled=True, width="small"),
            },
        )

        # 편집 내용을 세션 데이터에 반영
        changed = 0
        by_id = {t["id"]: t for t in TASKS}
        for r in edited.to_dict("records"):
            t = by_id.get(r["id"])
            if not t:
                continue
            new_due = fmt_date(r["납기"])
            pairs = [("status", r["상태"]), ("title", r["과제명"]), ("category", r["카테고리"]),
                     ("owner", r["담당"] or ""), ("deadline", new_due), ("progress", int(r["진척율"] or 0))]
            for k, v in pairs:
                if t.get(k) != v:
                    t[k] = v
                    t["updated"] = today_str()
                    changed += 1
        if changed:
            mark_dirty()
            st.toast(f"{changed}개 항목 수정됨 — 사이드바에서 GitHub에 저장하세요.", icon="✏️")

        st.divider()
        st.markdown("##### 과제 상세 · 진척 이력")
        sel = st.selectbox("과제 선택", [f"{t['title']} [{t['id']}]" for t in view],
                           label_visibility="collapsed")
        tid = re.search(r"\[(T\d+)\]$", sel).group(1)
        t = by_id[tid]
        st.markdown(f"**목표** — {t.get('goal') or '–'}")
        cc = st.columns(4)
        cc[0].metric("상태", t["status"])
        cc[1].metric("진척율", f"{t.get('progress', 0)}%")
        cc[2].metric("담당", t.get("owner") or "미입력")
        cc[3].metric("납기", t.get("deadline") or "미입력")

        hist = sorted(t.get("history", []), key=lambda h: h.get("date", ""), reverse=True)
        st.dataframe(
            pd.DataFrame([{"날짜": h.get("date", ""), "회의": h.get("meeting", "-"),
                           "내용": h.get("note", "")} for h in hist]),
            hide_index=True, use_container_width=True,
        )

        with st.form("td_add_hist", clear_on_submit=True):
            h1, h2 = st.columns([1, 3])
            h_meet = h1.text_input("회의/출처", value="수동 입력")
            h_note = h2.text_input("진척 내용")
            if st.form_submit_button("➕ 진척 이력 추가") and h_note.strip():
                t["history"].append({"date": today_str(), "meeting": h_meet,
                                     "note": h_note.strip(), "status": t["status"],
                                     "progress": t.get("progress", 0)})
                t["updated"] = today_str()
                mark_dirty()
                st.rerun()

        if st.button("🗑 이 과제 삭제", type="secondary"):
            if st.session_state.get("td_del") == tid:
                TASKS.remove(t)
                mark_dirty()
                st.session_state.td_del = None
                st.rerun()
            else:
                st.session_state.td_del = tid
                st.warning("한 번 더 누르면 삭제됩니다 (이력도 함께 삭제).")

# ── 정보 저장소 ─────────────────────────────────────────────
with tab_info:
    st.info("과제로 분류할 수 없는 **단순 정보**가 쌓이는 저장소입니다. "
            "**소재 · System · 운영 · 인물 · 기술**로 분류되며, 회의록을 넣을 때마다 누적됩니다.", icon="🗃️")
    if not INFO:
        st.info("저장된 정보가 없습니다.")
    else:
        g1, g2 = st.columns([1, 2])
        fic = g1.multiselect("분류", INFO_CATS, default=INFO_CATS,
                             label_visibility="collapsed", placeholder="분류 전체")
        fiq = g2.text_input("검색", placeholder="내용·회의명 검색", label_visibility="collapsed")

        iv = [i for i in INFO
              if i["category"] in (fic or INFO_CATS)
              and (not fiq or fiq.lower() in (i["title"] + i["content"] + i.get("meeting", "")).lower())]
        iv.sort(key=lambda i: i.get("date", ""), reverse=True)

        st.caption(f"{len(iv)} / {len(INFO)}건 표시")
        st.dataframe(
            pd.DataFrame([{"분류": i["category"], "제목": i["title"], "내용": i["content"],
                           "날짜": i.get("date", ""), "회의": i.get("meeting", "-")} for i in iv]),
            hide_index=True, use_container_width=True, height=520,
            column_config={"내용": st.column_config.TextColumn("내용", width="large")},
        )

        with st.expander("➕ 정보 직접 추가 / 삭제"):
            with st.form("td_add_info", clear_on_submit=True):
                n1, n2 = st.columns([1, 3])
                ni_cat = n1.selectbox("분류", INFO_CATS)
                ni_title = n2.text_input("제목")
                ni_content = st.text_area("내용", height=80)
                if st.form_submit_button("추가") and ni_title.strip():
                    INFO.append({"id": next_id("I", INFO), "category": ni_cat,
                                 "title": ni_title.strip(), "content": ni_content,
                                 "date": today_str(), "meeting": "수동 등록", "tags": []})
                    mark_dirty()
                    st.rerun()

            if iv:
                del_sel = st.selectbox("삭제할 정보", [f"{i['title']} [{i['id']}]" for i in iv])
                if st.button("🗑 정보 삭제"):
                    iid = re.search(r"\[(I\d+)\]$", del_sel).group(1)
                    DATA["info"] = [x for x in INFO if x["id"] != iid]
                    st.session_state.td_data = DATA
                    mark_dirty()
                    st.rerun()

# ── 전체 이력 ───────────────────────────────────────────────
with tab_hist:
    rows = [{"날짜": h.get("date", ""), "회의": h.get("meeting", "-"), "과제": t["title"],
             "카테고리": t.get("category", ""), "내용": h.get("note", ""),
             "상태": h.get("status", ""), "진척율": h.get("progress", 0)}
            for t in TASKS for h in t.get("history", [])]
    if not rows:
        st.info("이력이 없습니다.")
    else:
        hq = st.text_input("이력 검색", placeholder="과제·회의·내용", label_visibility="collapsed")
        rows = [r for r in rows if not hq or hq.lower() in (r["과제"] + r["회의"] + r["내용"]).lower()]
        rows.sort(key=lambda r: r["날짜"], reverse=True)
        st.caption(f"{len(rows)}건")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=600,
                     column_config={"내용": st.column_config.TextColumn("내용", width="large")})
        st.download_button("⬇ 이력 CSV", pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"과제이력_{today_str()}.csv", mime="text/csv")
