#!/usr/bin/env python3
"""Build deck/index.html from deck/template.html + content/slides.json.

- Injects slides.json and verify.md item counts into the page.
- With --fonts, downloads glyph subsets (only the characters the deck uses)
  from Google Fonts into assets/fonts/ and writes the @font-face block.

Usage: python3 deck/build.py [--fonts]
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "deck"
FONTS = ROOT / "assets" / "fonts"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

FAMILIES = [
    # (css family name, google family spec, file prefix)
    ("IBM Plex Sans KR", "IBM+Plex+Sans+KR:wght@400;500;600;700", "plexkr"),
    ("IBM Plex Mono", "IBM+Plex+Mono:wght@400;500;600", "plexmono"),
    ("Noto Sans SC", "Noto+Sans+SC:wght@400;500;600", "notosc"),
]


def short(t, n=34):
    return t if len(t) <= n else t[:n].rstrip() + "…"


def verify_counts():
    text = (ROOT / "content" / "verify.md").read_text(encoding="utf-8")
    counts = {}
    high = {}
    items = []
    for line in text.splitlines():
        m = re.match(r"\|\s*([VJCEX])(\d{2})\s*\|", line)
        if not m:
            continue
        k = m.group(1)
        counts[k] = counts.get(k, 0) + 1
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[-1] == "상":
            high[k] = high.get(k, 0) + 1
            items.append({"id": k + m.group(2), "item": short(cells[1].replace("**", ""))})
    return {"counts": counts, "high": high,
            "total": sum(counts.values()), "highTotal": sum(high.values()), "highItems": items}


def used_chars(data, template):
    chars = set(json.dumps(data, ensure_ascii=False)) | set(template)
    chars |= {chr(c) for c in range(0x20, 0x7F)}
    chars |= set("①②③④ⓐⓑⓒⓓ→↔·–—‘’“”×²▨■□△○%†※~")
    return "".join(sorted(c for c in chars if c >= " " and c not in "\n\r\t"))


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    return body if binary else body.decode("utf-8")


def build_fonts(text):
    FONTS.mkdir(parents=True, exist_ok=True)
    blocks = []
    for fam, spec, prefix in FAMILIES:
        url = ("https://fonts.googleapis.com/css2?family=" + spec + "&text="
               + urllib.parse.quote(text) + "&display=swap")
        css = fetch(url)
        for face in re.findall(r"@font-face\s*{[^}]+}", css):
            weight = re.search(r"font-weight:\s*(\d+)", face).group(1)
            src = re.search(r"url\((https://[^)]+)\)", face).group(1)
            name = f"{prefix}-{weight}.woff2"
            (FONTS / name).write_bytes(fetch(src, binary=True))
            blocks.append(
                "@font-face{font-family:'%s';font-style:normal;font-weight:%s;"
                "font-display:swap;src:url('../assets/fonts/%s') format('woff2')}"
                % (fam, weight, name))
            print("font", name, (FONTS / name).stat().st_size, "bytes")
    (FONTS / "fonts.css").write_text("\n".join(blocks) + "\n", encoding="utf-8")


def main():
    template = (DECK / "template.html").read_text(encoding="utf-8")
    data = json.loads((ROOT / "content" / "slides.json").read_text(encoding="utf-8"))
    data["verify"] = verify_counts()
    if "--fonts" in sys.argv:
        build_fonts(used_chars(data, template))
    font_css = (FONTS / "fonts.css").read_text(encoding="utf-8") if (FONTS / "fonts.css").exists() else ""
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (template.replace("/*__FONTS__*/", font_css)
                    .replace("__DECK_DATA__", payload))
    (DECK / "index.html").write_text(html, encoding="utf-8")
    print("wrote deck/index.html,", len(data["slides"]), "slides, verify", data["verify"])


if __name__ == "__main__":
    main()
