"""
core/gemini.py
───────────────
Gemini API 래퍼. app.py(Streamlit)와 generate_report.py(GitHub Actions)가 공유한다.
- 모델 목록 조회 및 최적 모델 선택
- 키워드 다국어(EN/JP/TW/CN) 번역
- 기사 제목 배치 번역
- 출처 인용 기반 리포트 생성
"""
import json
import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL_PRIORITY = ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro", "gemini-1.5-flash")


def list_models(api_key):
    try:
        res = requests.get(f"{BASE_URL}/models?key={api_key}", timeout=10)
        if res.status_code == 200:
            return [
                m["name"].replace("models/", "")
                for m in res.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "vision" not in m["name"]
            ]
    except Exception as e:
        logger.warning(f"모델 목록 조회 실패: {e}")
    return []


def pick_best_model(api_key):
    models = list_models(api_key)
    for prefix in MODEL_PRIORITY:
        found = next((m for m in models if m.startswith(prefix)), None)
        if found:
            return found
    return models[0] if models else MODEL_PRIORITY[1]


def _call(api_key, model, prompt, timeout=60, max_retries=3):
    """Gemini generateContent 호출. 429는 지수 백오프로 재시도."""
    url = f"{BASE_URL}/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}],
    }
    retry_wait = 1
    for attempt in range(max_retries):
        try:
            res = requests.post(url, json=body, timeout=timeout)
            if res.status_code == 200:
                candidates = res.json().get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
                return None
            elif res.status_code == 429:
                logger.warning(f"Rate limit [{model}], {retry_wait}s 후 재시도")
                time.sleep(retry_wait)
                retry_wait *= 2
                continue
            else:
                logger.warning(f"Gemini 응답 오류 [{model}]: {res.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Gemini 호출 예외 [{model}]: {e}")
            return None
    return None


def translate_keyword(api_key, keyword):
    """키워드를 EN/JP/TW/CN으로 번역. 실패 시 원문 유지."""
    prompt = (
        f"Translate the semiconductor-industry search term '{keyword}' into English, Japanese, "
        f"Traditional Chinese (Taiwan), and Simplified Chinese (China). "
        f'Return ONLY JSON: {{"EN":"..","JP":"..","TW":"..","CN":".."}}'
    )
    text = _call(api_key, "gemini-2.0-flash", prompt, timeout=12, max_retries=1)
    if text:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {"EN": keyword, "JP": keyword, "TW": keyword, "CN": keyword}


def translate_titles(api_key, titles, target_lang="Korean"):
    """기사 제목 리스트를 일괄 번역. 실패 시 원문 유지."""
    if not titles:
        return []
    prompt = (
        f"Translate the following list of news headlines to {target_lang}. "
        f'Return ONLY a JSON array of the translated strings, same order, same length: {json.dumps(titles)}'
    )
    text = _call(api_key, "gemini-2.0-flash", prompt, timeout=30, max_retries=2)
    if text:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                if isinstance(result, list) and len(result) == len(titles):
                    return result
            except Exception:
                pass
    return titles


REPORT_PROMPT = """당신은 글로벌 반도체 소재 산업을 전담하는 전략 수석 애널리스트입니다.
아래 "{category}" 주제로 수집된 한국·미국·일본·대만·중국 5개국 뉴스를 근거로,
전문가 수준의 서술형 심층 분석 리포트를 작성하세요.

[작성 원칙 - 반드시 준수]
1. 단순 요약·제목 나열 금지. 기사를 그대로 번역하거나 나열하지 마세요.
2. 인과관계와 맥락을 짚는 하나의 자연스러운 논리 흐름의 서술형 문단으로 작성하세요. 개조식(bullet) 금지.
3. 모든 사실 진술 끝에는 반드시 근거 뉴스 번호를 [1], [2] 형식으로 인용하세요. 인용 없는 사실 주장은 금지합니다.
4. 국가별 시각차(예: 중국의 자립화 vs 미국의 규제, 일본/대만의 공급망 대응)가 있다면 명시적으로 대비하여 서술하세요.
5. 사실이 뉴스 데이터에 없으면 추측하지 말고 서술에서 제외하세요.

[뉴스 데이터 - 번호. 제목 (국가 | 매체 | 날짜)]
{news_context}

[리포트 구조 - Markdown]

## 📊 Executive Summary
오늘 "{category}" 관련 핵심 동향을 3~4문장으로 요약. 인용 포함.

## 🚨 Key Issues & Deep Dive
가장 중요한 이슈 2~3개를 소제목과 함께 서술형으로 심층 분석. 국가 간 온도차가 있으면 대비 서술. 인용 필수.

## 🕸️ Supply Chain & Corporate Impact
공급망 구조 변화, 기업의 전략적 움직임(투자/제휴/인수/증설/규제 대응)을 서술.

## 💡 Analyst's View
이 리포트가 시사하는 바와 향후 관전 포인트를 서술형으로 정리.
"""


def build_news_context(news_items):
    lines = []
    for i, item in enumerate(news_items):
        clean_title = re.sub(r"<[^>]+>", "", item.get("Title", ""))
        country = item.get("Country", "KR")
        source = item.get("Source", "Unknown")
        date = item.get("ParsedDate") or item.get("Date", "")
        lines.append(f"[{i+1}] {clean_title} ({country} | {source} | {date})")
    return "\n".join(lines)


def generate_report(api_key, news_items, category_label="반도체 소재"):
    """뉴스 데이터를 근거로 인용이 포함된 Markdown 리포트를 생성. (True, text) 또는 (False, 에러메시지)"""
    model = pick_best_model(api_key)
    news_context = build_news_context(news_items)
    prompt = REPORT_PROMPT.format(category=category_label, news_context=news_context)

    for candidate_model in dict.fromkeys([model, *MODEL_PRIORITY]):
        text = _call(api_key, candidate_model, prompt, timeout=60, max_retries=3)
        if text:
            return True, text
    return False, "AI 리포트 생성 실패 (모든 모델 응답 없음)"
