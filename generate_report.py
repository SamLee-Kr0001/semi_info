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
NEWS_LIMIT    = 40
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
def fetch_news(keywords: list[str], target_date_str: str) -> list[dict]:
    """
    target_date 전날 12:00 KST ~ target_date 06:00 KST 범위 뉴스 수집.
    범위 내 뉴스가 없으면 최근 NEWS_DAYS일로 폴백.
    """
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    end_dt   = target_date.replace(hour=6, minute=0, second=0)
    start_dt = end_dt - timedelta(hours=NEWS_WINDOW_H)

    logger.info(f"뉴스 수집 범위: {start_dt} ~ {end_dt} KST")

    all_items: list[dict] = []
    per_kw = max(3, NEWS_LIMIT // max(len(keywords), 1))

    for kw in keywords:
        url = (
            f"https://news.google.com/rss/search?"
            f"q={quote(kw)}+when:{NEWS_DAYS}d&hl=ko&gl=KR&ceid=KR:ko"
        )
        try:
            res = requests.get(url, timeout=8, verify=False)
            res.raise_for_status()
            soup  = BeautifulSoup(res.content, "xml")
            items = soup.find_all("item")
            kw_count = 0
            for item in items:
                title = item.title.text.strip() if item.title else ""
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

                if is_valid and title:
                    if not any(i["Title"] == title for i in all_items):
                        all_items.append({
                            "Title":      title,
                            "Link":       link,
                            "Date":       date_raw,
                            "Source":     src,
                            "ParsedDate": parsed_date_str,
                        })
                        kw_count += 1
                if kw_count >= per_kw:
                    break
        except Exception as e:
            logger.warning(f"뉴스 수집 오류 [kw={kw}]: {e}")
        time.sleep(0.15)

    # 시간 필터 결과가 부족하면 폴백: 최근 NEWS_DAYS일 전체
    if len(all_items) < 5:
        logger.warning(f"시간 필터 결과 {len(all_items)}건 → 폴백: 전체 {NEWS_DAYS}일")
        all_items = []
        for kw in keywords:
            url = (
                f"https://news.google.com/rss/search?"
                f"q={quote(kw)}+when:{NEWS_DAYS}d&hl=ko&gl=KR&ceid=KR:ko"
            )
            try:
                res = requests.get(url, timeout=8, verify=False)
                res.raise_for_status()
                soup  = BeautifulSoup(res.content, "xml")
                items = soup.find_all("item")
                kw_count = 0
                for item in items:
                    title = item.title.text.strip() if item.title else ""
                    link  = item.link.text.strip()  if item.link  else ""
                    src   = item.source.text.strip() if item.source else "Google News"
                    date_raw = item.pubDate.text if item.pubDate else ""
                    if title and not any(i["Title"] == title for i in all_items):
                        all_items.append({
                            "Title":      title,
                            "Link":       link,
                            "Date":       date_raw,
                            "Source":     src,
                            "ParsedDate": None,
                        })
                        kw_count += 1
                    if kw_count >= per_kw:
                        break
            except Exception as e:
                logger.warning(f"폴백 뉴스 수집 오류 [kw={kw}]: {e}")
            time.sleep(0.15)

    # 중복 제거 후 상위 NEWS_LIMIT건
    seen, unique = set(), []
    for item in all_items:
        if item["Title"] not in seen:
            seen.add(item["Title"])
            unique.append(item)
    result = unique[:NEWS_LIMIT]
    logger.info(f"뉴스 수집 완료: {len(result)}건")
    return result


# ════════════════════════════════════════════════════════════
# 4. AI 리포트 생성
# ════════════════════════════════════════════════════════════
def _get_best_model() -> str:
    """사용 가능한 Gemini 모델 중 최선 선택"""
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
    return "gemini-2.0-flash"


def generate_report(news_data: list[dict]) -> str:
    """뉴스 데이터로 AI 리포트 생성 (링크 주입 없이 순수 Markdown 반환)"""
    model = _get_best_model()

    news_context = "\n".join(
        f"[{i+1}] {re.sub(r'<[^>]+>', '', item['Title'])} (출처: {item['Source']})"
        for i, item in enumerate(news_data)
    )

    prompt = f"""당신은 글로벌 반도체 소재의 전략 수석 엔지니어입니다.
제공된 뉴스 데이터를 바탕으로 전문가 수준의 [일일 반도체 기술·소재 심층 분석 보고서]를 작성하세요.

[작성 원칙]
1. 단순 요약 금지 - 뉴스 제목을 나열하지 마세요.
2. 서술형 작성 - bullet point 없이 자연스러운 논리 흐름의 서술형 단락으로 작성하세요.
3. 근거 명시 - 모든 주장에 뉴스 번호 [1], [2] 등을 반드시 인용하세요.

[뉴스 데이터]
{news_context}

[보고서 구조 - Markdown 형식]

## 🚨 Key Issues & Deep Dive (핵심 이슈 심층 분석)
가장 중요한 이슈 2~3가지를 소제목과 함께 서술형 단락으로 분석. 인용 번호 필수.

## 🕸️ Supply Chain & Tech Trends (공급망 및 기술 동향)
반도체 소재·소부장 기술 변화와 공급망 주요 동향 서술.

## 💡 Analyst's View (시사점)
오늘 뉴스가 주는 핵심 시사점과 향후 관전 포인트 서술.

## 📊 Executive Summary (시장 총평)
오늘 반도체 시장 분위기와 소재 중심 이슈 3~4문장 요약.
"""

    headers = {"Content-Type": "application/json"}
    body    = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_API_KEY}"
    )

    retry_wait = 2
    for attempt in range(4):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=120)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    text = candidates[0]["content"]["parts"][0]["text"]
                    logger.info(f"리포트 생성 완료 ({len(text)} chars)")
                    return text
                logger.warning("candidates 없음 → 재시도")
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

