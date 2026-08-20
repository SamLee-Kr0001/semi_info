"""
core/keywords.py
──────────────────
리포트 카테고리와 카테고리별 기본/저장 키워드를 관리한다.
카테고리는 사용자가 요청한 4대 축 - 종합(Daily) / 기술 동향 / 기업 변화 / SCM·공급망 - 으로 구성한다.
"""
from core.store import read_json, write_json

KEYWORD_FILE = "keywords.json"

CATEGORIES = ["Daily Report", "기술 동향", "기업 변화", "SCM·공급망"]

CATEGORY_META = {
    "Daily Report":  {"icon": "📰", "desc": "4개 축을 아우르는 종합 일일 브리핑"},
    "기술 동향":      {"icon": "🔬", "desc": "공정·소재·장비 기술 혁신 동향"},
    "기업 변화":      {"icon": "🏢", "desc": "투자·M&A·증설·경영진 등 기업 이슈"},
    "SCM·공급망":     {"icon": "🕸️", "desc": "수출입 규제, 원자재, 물류, 공급망 재편"},
}

DEFAULT_KEYWORDS = {
    "Daily Report": [
        "반도체 소재", "반도체 공급망", "EUV", "포토레지스트", "프리커서",
        "반도체 소부장", "중국 반도체", "미국 반도체 규제", "희토류 반도체",
    ],
    "기술 동향": [
        "EUV 노광", "차세대 소재", "High-k", "CMP 슬러리", "습식 식각액",
        "박막 증착", "하이브리드 본딩", "GAA 트랜지스터",
    ],
    "기업 변화": [
        "반도체 소재 투자", "반도체 증설", "반도체 M&A", "소재 기업 실적",
        "파운드리 증설", "반도체 소재 공장",
    ],
    "SCM·공급망": [
        "반도체 수출 규제", "희토류 수출 통제", "반도체 소재 공급망",
        "반도체 특수가스", "네온 가스 공급망", "실리콘 웨이퍼 공급",
    ],
}


def load_keywords(github_token=None, repo_name=None):
    data = read_json(KEYWORD_FILE, {}, github_token, repo_name)
    result = {}
    for cat in CATEGORIES:
        result[cat] = data.get(cat) or list(DEFAULT_KEYWORDS.get(cat, []))
    return result


def save_keywords(data, github_token=None, repo_name=None):
    return write_json(KEYWORD_FILE, data, github_token, repo_name)
