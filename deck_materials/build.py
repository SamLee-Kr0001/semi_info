#!/usr/bin/env python3
"""Build deck_materials/index.html from template.html + slides.json.

With --fonts, re-subsets the shared fonts in assets/fonts/ so they cover the
characters of both decks (deck/ and deck_materials/).

Usage: python3 deck_materials/build.py [--fonts]
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

spec = importlib.util.spec_from_file_location("deck1_build", ROOT / "deck" / "build.py")
deck1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck1)


def main():
    template = (HERE / "template.html").read_text(encoding="utf-8")
    data = json.loads((HERE / "slides.json").read_text(encoding="utf-8"))
    if "--fonts" in sys.argv:
        d1 = json.loads((ROOT / "content" / "slides.json").read_text(encoding="utf-8"))
        t1 = (ROOT / "deck" / "template.html").read_text(encoding="utf-8")
        chars = set(deck1.used_chars(data, template)) | set(deck1.used_chars(d1, t1))
        chars |= set("₀₁₂₃₄₅₆₇₈₉")
        deck1.build_fonts("".join(sorted(chars)))
    font_css = (ROOT / "assets" / "fonts" / "fonts.css").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("/*__FONTS__*/", font_css).replace("__DECK_DATA__", payload)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print("wrote deck_materials/index.html,", len(data["slides"]), "slides")


if __name__ == "__main__":
    main()
