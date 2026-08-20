"""
core/history.py
─────────────────
카테고리별 일일 리포트 아카이브(daily_history.json)를 관리한다.
과거(레거시) 항목은 category가 없으므로 "Daily Report"로 간주한다.
"""
from core.store import read_json, write_json

HISTORY_FILE = "daily_history.json"
MAX_ENTRIES_PER_CATEGORY = 30


def load_history(github_token=None, repo_name=None):
    raw = read_json(HISTORY_FILE, [], github_token, repo_name)
    for entry in raw:
        entry.setdefault("category", "Daily Report")
    return raw


def get_report(history, category, date_str):
    return next((h for h in history if h["category"] == category and h["date"] == date_str), None)


def list_for_category(history, category):
    return [h for h in history if h["category"] == category]


def save_report(history, category, date_str, report_text, articles, auto_generated=False, generated_at=None):
    """같은 카테고리+날짜 항목을 교체하고 카테고리별 최신순으로 정리한 새 히스토리 리스트를 반환한다."""
    updated = [h for h in history if not (h["category"] == category and h["date"] == date_str)]
    updated.insert(0, {
        "date": date_str,
        "category": category,
        "report": report_text,
        "articles": articles,
        "auto_generated": auto_generated,
        "generated_at": generated_at,
    })

    by_category = {}
    for entry in updated:
        by_category.setdefault(entry["category"], []).append(entry)

    trimmed = []
    for cat, entries in by_category.items():
        entries.sort(key=lambda e: e["date"], reverse=True)
        trimmed.extend(entries[:MAX_ENTRIES_PER_CATEGORY])
    return trimmed


def persist(history, github_token=None, repo_name=None):
    return write_json(HISTORY_FILE, history, github_token, repo_name)
