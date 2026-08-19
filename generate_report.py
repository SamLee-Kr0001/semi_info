"""
generate_report.py
──────────────────
GitHub Actions에서 매일 06:00 KST (21:00 UTC)에 실행되는 독립 스크립트.
Streamlit / session_state 완전 미사용.

필요한 GitHub Secrets:
  GEMINI_API_KEY  - Gemini API 키
  GITHUB_TOKEN    - (Actions에서 자동 제공) repo read/write 권한
  REPO_NAME       - "username/repo-name" 형태의 저장소 이름

실행 방법 (로컬 테스트):
  GEMINI_API_KEY=... GITHUB_TOKEN=... REPO_NAME=user/repo python generate_report.py
"""

import base64
import concurrent.futures
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
import urllib3
from bs4 import BeautifulSoup
from github import Github

# ── 로깅 ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── 상수 ────────────────────────────────────────────────────
KEYWORD_FILE  = "keywords.json"
HISTORY_FILE  = "daily_history.json"
DEFAULT_KEYWORDS = ["반도체", "삼성전자", "SK하이닉스", "HBM", "NAND", "파운드리"]
MAX_HISTORY   = 30          # 아카이브 최대 보관 수
NEWS_LIMIT    = 25          # 무료 Gemini API 토큰 한도에 맞춰 수집 기사 수 축소 (기존 40 → 25)
NEWS_DAYS     = 2           # 수집 기간 (일)
NEWS_WINDOW_H = 18          # 수집 시간 윈도우 (시간): 전날 12:00 ~ 당일 06:00

# ── 환경변수 로드 ────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME      = os.environ.get("REPO_NAME", "")

def _require_env():
    missing = [k for k, v in {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GITHUB_TOKEN":   GITHUB_TOKEN,
        "REPO_NAME":      REPO_NAME,
    }.items() if not v]
    if missing:
        logger.error(f"필수 환경변수 누락: {missing}")
        sys.exit(1)


# ════════════════════════════════════════════════════════════
# 1. GitHub I/O
# ════════════════════════════════════════════════════════════
def _get_repo():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)

def _read_json_from_github(filename: str, default):
    try:
        repo = _get_repo()
        contents = repo.get_contents(filename)
        if contents.encoding == "none":
            # Contents API는 1MB 초과 파일에 inline content를 주지 않음(encoding="none").
            # 이 경우 decoded_content가 예외를 던지므로 Git Blob API로 원본을 다시 조회한다.
            blob = repo.get_git_blob(contents.sha)
            raw = base64.b64decode(blob.content)
            return json.loads(raw.decode("utf-8"))
        return json.loads(contents.decoded_content.decode("utf-8"))
    except Exception as e:
        logger.warning(f"GitHub 읽기 실패 [{filename}]: {e}")
        return default

def _write_json_to_github(filename: str, data):
    try:
        repo = _get_repo()
        content_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        try:
            existing = repo.get_contents(filename)
            repo.update_file(
                existing.path,
                f"[Auto] Update {filename} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                content_str,
                existing.sha,
            )
        except Exception:
            repo.create_file(
                filename,
                f"[Auto] Create {filename}",
                content_str,
            )
        logger.info(f"GitHub 저장 완료: {filename}")
        return True
    except Exception as e:
        logger.error(f"GitHub 저장 실패 [{filename}]: {e}")
        return False


# ════════════════════════════════════════════════════════════
# 2. 키워드 로드
# ════════════════════════════════════════════════════════════
def load_keywords() -> list[str]:
    data = _read_json_from_github(KEYWORD_FILE, {})
    keywords = data.get("Daily Report", [])
    if not keywords:
        logger.warning("키워드 없음 → 기본 키워드 사용")
        keywords = DEFAULT_KEYWORDS
    logger.info(f"키워드 ({len(keywords)}개): {keywords}")
    return keywords


# ════════════════════════════════════════════════════════════
# 3. 뉴스 수집
# ════════════════════════════════════════════════════════════
def _fetch_keyword_news(kw: str, per_kw: int, start_dt: datetime, end_dt: datetime) -> tuple[list[dict], list[dict]]:
    """단일 키워드 RSS를 1회만 조회하여 (시간필터 통과 목록, 원본 전체 목록)을 함께 반환.
    폴백 시 재크롤링 없이 이 원본 목록을 그대로 재사용한다."""
    url = (
        f"https://news.google.com/rss/search?"
        f"q={quote(kw)}+when:{NEWS_DAYS}d&hl=ko&gl=KR&ceid=KR:ko"
    )
    filtered: list[dict] = []
    raw: list[dict] = []
    try:
        res = requests.get(url, timeout=8, verify=False)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "xml")
        for item in soup.find_all("item"):
            title = item.title.text.strip() if item.title else ""
            if not title:
                continue
            link  = item.link.text.strip()  if item.link  else ""
            src   = item.source.text.strip() if item.source else "Google News"
            date_raw = item.pubDate.text if item.pubDate else ""
            parsed_date_str = None

            # 시간 필터
            is_valid = True
            try:
                pub_dt = datetime.strptime(date_raw, "%a, %d %b %Y %H:%M:%S %Z")
                pub_dt_kst = pub_dt + timedelta(hours=9)
                parsed_date_str = pub_dt_kst.strftime("%Y-%m-%d %H:%M:%S")
                if not (start_dt <= pub_dt_kst <= end_dt):
                    is_valid = False
            except Exception:
                pass  # 파싱 실패 시 포함

            entry = {
                "Title": title, "Link": link, "Date": date_raw,
                "Source": src, "ParsedDate": parsed_date_str,
            }
            if len(raw) < per_kw:
                raw.append(entry)
            if is_valid and len(filtered) < per_kw:
                filtered.append(entry)
            if len(filtered) >= per_kw and len(raw) >= per_kw:
                break
    except Exception as e:
        logger.warning(f"뉴스 수집 오류 [kw={kw}]: {e}")
    return filtered, raw


def _dedupe(items: list[dict]) -> list[dict]:
    seen, unique = set(), []
    for item in items:
        if item["Title"] not in seen:
            seen.add(item["Title"])
            unique.append(item)
    return unique


def fetch_news(keywords: list[str], target_date_str: str) -> list[dict]:
    """
    target_date 전날 12:00 KST ~ target_date 06:00 KST 범위 뉴스 수집.
    범위 내 뉴스가 없으면 이미 수집해 둔 전체 뉴스로 폴백(재크롤링 없음).
    키워드별 요청은 병렬로 실행해 크롤링 시간을 단축한다.
    """
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    end_dt   = target_date.replace(hour=6, minute=0, second=0)
    start_dt = end_dt - timedelta(hours=NEWS_WINDOW_H)

    logger.info(f"뉴스 수집 범위: {start_dt} ~ {end_dt} KST")

    per_kw = max(3, NEWS_LIMIT // max(len(keywords), 1))
    filtered_all: list[dict] = []
    raw_all: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(keywords))) as executor:
        futures = [executor.submit(_fetch_keyword_news, kw, per_kw, start_dt, end_dt) for kw in keywords]
        for future in concurrent.futures.as_completed(futures):
            filtered, raw = future.result()
            filtered_all.extend(filtered)
            raw_all.extend(raw)

    unique_filtered = _dedupe(filtered_all)
    if len(unique_filtered) < 5:
        logger.warning(f"시간 필터 결과 {len(unique_filtered)}건 → 폴백: 이미 수집된 전체 뉴스 재사용")
        result_pool = _dedupe(raw_all)
    else:
        result_pool = unique_filtered

    result = result_pool[:NEWS_LIMIT]
    logger.info(f"뉴스 수집 완료: {len(result)}건")
    return result


# ════════════════════════════════════════════════════════════
# 4. AI 리포트 생성
# ════════════════════════════════════════════════════════════
DEFAULT_MODEL = "gemini-2.0-flash"  # 매번 모델 목록을 조회하지 않고 바로 사용 (지연 시간 단축)


def _get_best_model() -> str:
    """사용 가능한 Gemini 모델 중 최선 선택 (DEFAULT_MODEL 실패 시에만 조회)"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            models = [
                m["name"].replace("models/", "")
                for m in res.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "vision" not in m["name"]
            ]
            # 2.0-flash 우선, 그 다음 1.5-pro, 나머지 순
            for prefix in ("gemini-2.0-flash", "gemini-2.5", "gemini-1.5-pro", "gemini-1.5-flash"):
                found = next((m for m in models if m.startswith(prefix)), None)
                if found:
                    logger.info(f"선택된 모델: {found}")
                    return found
    except Exception as e:
        logger.warning(f"모델 목록 조회 실패: {e}")
    return DEFAULT_MODEL


def generate_report(news_data: list[dict]) -> str:
    """뉴스 데이터로 AI 리포트 생성 (링크 주입 없이 순수 Markdown 반환)"""
    news_context = "\n".join(
        f"[{i+1}] {re.sub(r'<[^>]+>', '', item['Title'])} (출처: {item['Source']})"
        for i, item in enumerate(news_data)
    )

    prompt = f"""당신은 글로벌 반도체 소재 전략 수석 애널리스트입니다.
아래 뉴스만 근거로, 바쁜 임원이 핵심을 즉시 파악할 [일일 반도체 기술·소재 브리핑]을 작성하세요.

[절대 금지] "오늘날 반도체 산업은" 같은 상투적 도입 문장 금지 - 바로 사실로 시작. 제목 나열/번역 금지. 뉴스에 없는 내용 추측 금지.
[작성 원칙] 1) 두괄식: 각 섹션 첫 문장에 결론 제시 후 근거. 2) 서술형, 군더더기 없이 간결하게. 3) 모든 주장에 뉴스 번호 [1][2] 인용.

[뉴스 데이터]
{news_context}

[보고서 구조 - Markdown]
## 📌 핵심 요약 (Executive Brief)
가장 중요한 판단 3~4개를 각 1문장, 결론부터. 인용 번호 포함.

## 🚨 핵심 이슈 심층 분석
이슈 2~3가지, 소제목마다 결론 먼저 제시 후 서술형으로 상세 분석. 인용 번호 필수.

## 🕸️ 공급망 및 기술 동향
소재·소부장 기술 변화와 공급망 핵심만 결론 우선 서술.

## 💡 Analyst's View (시사점)
시사점과 향후 관전 포인트를 결론부터 서술.
"""

    headers = {"Content-Type": "application/json"}
    body    = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048,  # 무료 Gemini API 토큰 한도에 맞춘 보수적인 출력 예산
            # gemini-2.5 계열은 기본적으로 "thinking" 토큰이 maxOutputTokens를 잠식해
            # 실제 응답이 조기 절단될 수 있으므로 명시적으로 비활성화
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    def _call(model: str):
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )
        return requests.post(url, headers=headers, json=body, timeout=120)

    model = DEFAULT_MODEL
    retry_wait = 2
    for attempt in range(4):
        try:
            resp = _call(model)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    text = candidates[0]["content"]["parts"][0]["text"]
                    if len(text) < 300 or "##" not in text:
                        # 응답이 비정상적으로 짧거나(조기 절단) 구조가 없으면 폐기하고 재시도
                        logger.warning(f"리포트가 비정상적으로 짧음 ({len(text)} chars) → 재시도")
                        continue
                    logger.info(f"리포트 생성 완료 ({len(text)} chars)")
                    return text
                logger.warning("candidates 없음 → 재시도")
            elif resp.status_code == 404 and model == DEFAULT_MODEL:
                # 기본 모델 사용 불가 → 사용 가능한 모델로 교체 후 재시도
                model = _get_best_model()
                logger.warning(f"기본 모델 사용 불가 → {model}(으)로 전환")
                continue
            elif resp.status_code == 429:
                logger.warning(f"Rate limit → {retry_wait}s 대기 후 재시도 (attempt {attempt+1})")
                time.sleep(retry_wait)
                retry_wait *= 2
                continue
            else:
                logger.error(f"API 오류: {resp.status_code} {resp.text[:200]}")
                break
        except Exception as e:
            logger.error(f"리포트 생성 예외: {e}")
            break

    raise RuntimeError("AI 리포트 생성 실패 (모든 재시도 소진)")


# ════════════════════════════════════════════════════════════
# 5. 히스토리 저장
# ════════════════════════════════════════════════════════════
def save_report(date_str: str, report_text: str, articles: list[dict]):
    history = _read_json_from_github(HISTORY_FILE, [])

    # 같은 날짜 항목 제거 후 맨 앞에 추가
    history = [h for h in history if h.get("date") != date_str]
    history.insert(0, {
        "date":           date_str,
        "report":         report_text,
        "articles":       articles,
        "auto_generated": True,
        "generated_at":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    })

    # 오래된 항목 정리
    history = history[:MAX_HISTORY]

    _write_json_to_github(HISTORY_FILE, history)
    logger.info(f"히스토리 저장 완료 (총 {len(history)}건)")


# ════════════════════════════════════════════════════════════
# 6. 메인
# ════════════════════════════════════════════════════════════
def main():
    logger.info("=" * 60)
    logger.info("Semi-Insight Hub - Daily Report Generator")
    logger.info("=" * 60)

    _require_env()

    # 실행 시각 기준 KST 날짜 (06:00 이후이면 당일, 이전이면 전날)
    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
    if now_kst.hour < 6:
        target_date = (now_kst - timedelta(days=1)).date()
    else:
        target_date = now_kst.date()
    target_date_str = target_date.strftime("%Y-%m-%d")

    logger.info(f"대상 날짜: {target_date_str}")

    # 이미 오늘 리포트가 있으면 스킵 (중복 실행 방지)
    history = _read_json_from_github(HISTORY_FILE, [])
    if any(h.get("date") == target_date_str for h in history):
        logger.info(f"{target_date_str} 리포트 이미 존재 → 스킵")
        return

    # 키워드 로드
    keywords = load_keywords()

    # 뉴스 수집
    articles = fetch_news(keywords, target_date_str)
    if not articles:
        logger.error("수집된 뉴스 없음 → 종료")
        sys.exit(1)

    # AI 리포트 생성
    report_text = generate_report(articles)

    # 저장
    save_report(target_date_str, report_text, articles)

    logger.info("✅ Daily Report 생성 완료!")


if __name__ == "__main__":
    main()

