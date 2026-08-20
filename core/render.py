"""
core/render.py
────────────────
AI가 생성한 Markdown 리포트를 안전한 HTML로 변환한다 (경량 파서: ##/### 헤딩, 단락, **볼드**만 지원).
인용 번호 [n]은 실제 기사 링크로 치환한다.
"""
import re
from urllib.parse import urlparse


def sanitize_url(url_str):
    try:
        parsed = urlparse(url_str)
        if parsed.scheme in ("http", "https"):
            return url_str
    except Exception:
        pass
    return "#"


def inject_citation_links(report_text, articles):
    def replace(match):
        try:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(articles):
                link = sanitize_url(articles[idx].get("Link", "#"))
                return f"<a href='{link}' target='_blank'>[{match.group(1)}]</a>"
        except Exception:
            pass
        return match.group(0)

    return re.sub(r"\[(\d+)\]", replace, report_text)


def _inline_format(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


def markdown_to_html(report_text):
    lines = report_text.strip().split("\n")
    html_parts = []
    para_buf = []

    def flush():
        if para_buf:
            html_parts.append("<p>" + " ".join(para_buf) + "</p>")
            para_buf.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("### "):
            flush()
            html_parts.append(f"<h3>{_inline_format(stripped[4:].strip())}</h3>")
        elif stripped.startswith("## "):
            flush()
            html_parts.append(f"<h2>{_inline_format(stripped[3:].strip())}</h2>")
        elif stripped.startswith("#"):
            flush()
            html_parts.append(f"<h2>{_inline_format(stripped.lstrip('#').strip())}</h2>")
        elif stripped.startswith(("- ", "* ")):
            flush()
            html_parts.append(f"<p>• {_inline_format(stripped[2:].strip())}</p>")
        else:
            para_buf.append(_inline_format(stripped))
    flush()
    return "\n".join(html_parts)


def extract_executive_summary(report_text):
    """'Executive Summary' 섹션 본문만 추출 (요약 카드 표시용). 없으면 첫 문단을 사용."""
    match = re.search(
        r"##\s*[^\n]*Executive Summary[^\n]*\n(.*?)(?=\n##|\Z)",
        report_text, re.IGNORECASE | re.DOTALL,
    )
    body = match.group(1).strip() if match else report_text.strip().split("\n\n")[0]
    body = re.sub(r"^#+\s*", "", body, flags=re.MULTILINE).strip()
    return body
