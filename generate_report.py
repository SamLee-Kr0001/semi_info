"""
generate_report.py
────────────────────
GitHub Actions에서 매일 06:00 KST(21:00 UTC)에 실행되는 독립 스크립트.
4개 카테고리(Daily Report / 기술 동향 / 기업 변화 / SCM·공급망) 각각에 대해
한국·미국·일본·대만·중국 5개국 뉴스를 수집하고 Gemini로 출처 인용 리포트를 생성해
daily_history.json에 저장한다. Streamlit / session_state는 사용하지 않는다.

필요한 GitHub Secrets:
  GEMINI_API_KEY  - Gemini API 키
  GITHUB_TOKEN    - (Actions에서 자동 제공) repo read/write 권한
  REPO_NAME       - "username/repo-name" 형태의 저장소 이름

로컬 테스트:
  GEMINI_API_KEY=... GITHUB_TOKEN=... REPO_NAME=user/repo python generate_report.py
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
import os

from core import gemini, history, keywords, news

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("REPO_NAME", "")

NEWS_DAYS = 2
PER_COUNTRY_LIMIT = 2
NEWS_LIMIT = 35


def _require_env():
    missing = [k for k, v in {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GITHUB_TOKEN": GITHUB_TOKEN,
        "REPO_NAME": REPO_NAME,
    }.items() if not v]
    if missing:
        logger.error(f"필수 환경변수 누락: {missing}")
        sys.exit(1)


def _target_date_str():
    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
    target_date = (now_kst - timedelta(days=1)).date() if now_kst.hour < 6 else now_kst.date()
    return target_date.strftime("%Y-%m-%d")


def run_category(category, target_date_str, hist):
    if history.get_report(hist, category, target_date_str):
        logger.info(f"[{category}] {target_date_str} 리포트 이미 존재 → 스킵")
        return hist

    kw_map = keywords.load_keywords(GITHUB_TOKEN, REPO_NAME)
    kws = kw_map.get(category, [])
    if not kws:
        logger.warning(f"[{category}] 키워드 없음 → 스킵")
        return hist

    logger.info(f"[{category}] 뉴스 수집 시작 (키워드 {len(kws)}개)")
    articles = news.collect_news(
        GEMINI_API_KEY, kws, days=NEWS_DAYS, per_country_limit=PER_COUNTRY_LIMIT, limit=NEWS_LIMIT,
    )
    if not articles:
        logger.error(f"[{category}] 수집된 뉴스 없음 → 스킵")
        return hist
    logger.info(f"[{category}] 뉴스 {len(articles)}건 수집 완료")

    success, result = gemini.generate_report(GEMINI_API_KEY, articles, category_label=category)
    if not success:
        logger.error(f"[{category}] 리포트 생성 실패: {result}")
        return hist

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    hist = history.save_report(
        hist, category, target_date_str, result, articles,
        auto_generated=True, generated_at=generated_at,
    )
    history.persist(hist, GITHUB_TOKEN, REPO_NAME)
    logger.info(f"[{category}] 리포트 저장 완료")
    return hist


def main():
    logger.info("=" * 60)
    logger.info("MatChain Insight - Daily Report Generator")
    logger.info("=" * 60)

    _require_env()

    target_date_str = _target_date_str()
    logger.info(f"대상 날짜: {target_date_str}")

    hist = history.load_history(GITHUB_TOKEN, REPO_NAME)
    for category in keywords.CATEGORIES:
        hist = run_category(category, target_date_str, hist)

    logger.info("✅ Daily Report 생성 완료!")


if __name__ == "__main__":
    main()
