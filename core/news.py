"""
core/news.py
─────────────
5개국(한국/미국/일본/대만/중국) Google News RSS 기반 뉴스 수집.
정확한 원문 출처(매체명·링크·발행일)를 그대로 보존해 Report의 인용 근거로 사용한다.
"""
import logging
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import requests
import urllib3
from bs4 import BeautifulSoup

from core.gemini import translate_keyword, translate_titles

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

COUNTRIES = {
    "KR": {"gl": "KR", "hl": "ko",    "flag": "🇰🇷", "label": "한국", "lang_key": "KR"},
    "US": {"gl": "US", "hl": "en",    "flag": "🇺🇸", "label": "미국", "lang_key": "EN"},
    "JP": {"gl": "JP", "hl": "ja",    "flag": "🇯🇵", "label": "일본", "lang_key": "JP"},
    "TW": {"gl": "TW", "hl": "zh-TW", "flag": "🇹🇼", "label": "대만", "lang_key": "TW"},
    "CN": {"gl": "CN", "hl": "zh-CN", "flag": "🇨🇳", "label": "중국", "lang_key": "CN"},
}


def _rss_url(term, country_conf, days):
    return (
        f"https://news.google.com/rss/search?q={quote(term)}+when:{days}d"
        f"&hl={country_conf['hl']}&gl={country_conf['gl']}&ceid={country_conf['gl']}:{country_conf['hl']}"
    )


def _fetch_one(term, country_code, days, limit, timeout=6):
    conf = COUNTRIES[country_code]
    items_out = []
    try:
        res = requests.get(_rss_url(term, conf, days), timeout=timeout, verify=False)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "xml")
        for item in soup.find_all("item")[:limit]:
            title = item.title.text.strip() if item.title else ""
            link = item.link.text.strip() if item.link else ""
            source = item.source.text.strip() if item.source else "Google News"
            date_raw = item.pubDate.text if item.pubDate else ""
            if not title or not link:
                continue
            parsed_date = None
            try:
                pub_dt = datetime.strptime(date_raw, "%a, %d %b %Y %H:%M:%S %Z")
                parsed_date = (pub_dt + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            items_out.append({
                "Title": title,
                "Link": link,
                "Date": date_raw,
                "ParsedDate": parsed_date,
                "Source": source,
                "Country": country_code,
                "Flag": conf["flag"],
                "CountryLabel": conf["label"],
            })
    except Exception as e:
        logger.warning(f"뉴스 수집 오류 [{country_code} / {term}]: {e}")
    return items_out


def collect_news(api_key, keywords, days=3, per_country_limit=3, countries=None,
                  translate_foreign=True, limit=40):
    """
    키워드마다 5개국 언어로 번역 후 각국 Google News RSS를 조회한다.
    반환: [{Title, TitleKo, Link, Date, ParsedDate, Source, Country, Flag, CountryLabel}, ...]
    한국어가 아닌 기사 제목은 Gemini로 한국어 번역을 덧붙인다(TitleKo).
    """
    countries = countries or list(COUNTRIES.keys())
    all_items = []

    for kw in keywords:
        if api_key:
            trans_map = translate_keyword(api_key, kw)
        else:
            trans_map = {"EN": kw, "JP": kw, "TW": kw, "CN": kw}
        trans_map["KR"] = kw

        for country_code in countries:
            conf = COUNTRIES[country_code]
            term = trans_map.get(conf["lang_key"], kw)
            found = _fetch_one(term, country_code, days, per_country_limit)
            all_items.extend(found)
            time.sleep(0.1)

    # 제목 기준 중복 제거 (동일 이슈가 여러 매체/키워드에서 중복 검색되는 경우 방지)
    seen_titles = set()
    unique_items = []
    for item in all_items:
        key = item["Title"]
        if key not in seen_titles:
            seen_titles.add(key)
            unique_items.append(item)

    # 최신순 정렬 (파싱 실패 항목은 뒤로) 후 상한 적용 (번역 비용/시간 제어)
    unique_items.sort(key=lambda x: x["ParsedDate"] or "0000-00-00", reverse=True)
    unique_items = unique_items[:limit]

    if translate_foreign and api_key:
        foreign_idx = [i for i, x in enumerate(unique_items) if x["Country"] != "KR"]
        foreign_titles = [unique_items[i]["Title"] for i in foreign_idx]
        translated = translate_titles(api_key, foreign_titles)
        for idx, ko_title in zip(foreign_idx, translated):
            unique_items[idx]["TitleKo"] = ko_title
    for item in unique_items:
        item.setdefault("TitleKo", item["Title"])

    return unique_items
