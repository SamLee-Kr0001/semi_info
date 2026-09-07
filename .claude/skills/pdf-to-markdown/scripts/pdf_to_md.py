#!/usr/bin/env python3
"""Convert a PDF file into a Markdown file.

Heuristics used:
- Font size relative to the document's median body-text size determines
  heading levels (#, ##, ###).
- Lines starting with a bullet glyph or "1." / "(1)" become list items.
- A vertical gap larger than the body line height starts a new paragraph.
- Tables detected by pdfplumber are rendered as Markdown tables and the
  words inside their bounding box are excluded from the surrounding text.
- Embedded images can optionally be extracted alongside the Markdown file.
"""
import argparse
import os
import re
import statistics
import sys
from pathlib import Path

import pdfplumber

BULLET_RE = re.compile(r"^\s*[•●▪◦‣∙·-]\s+")
NUMBERED_RE = re.compile(r"^\s*(\d+[.)]|\(\d+\))\s+")


def bbox_overlaps(bbox_a, bbox_b):
    ax0, ay0, ax1, ay1 = bbox_a
    bx0, by0, bx1, by1 = bbox_b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def word_in_any_bbox(word, bboxes):
    wbox = (word["x0"], word["top"], word["x1"], word["bottom"])
    return any(bbox_overlaps(wbox, b) for b in bboxes)


def group_words_into_lines(words, line_tolerance=3):
    lines = []
    current = []
    current_top = None
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        if current_top is None or abs(w["top"] - current_top) <= line_tolerance:
            current.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            lines.append(current)
            current = [w]
            current_top = w["top"]
    if current:
        lines.append(current)
    return lines


def render_table(rows):
    rows = [
        ["" if c is None else str(c).replace("\n", " ").strip() for c in row]
        for row in rows
    ]
    rows = [r for r in rows if any(cell for cell in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def collect_body_size(pdf):
    sizes = []
    for page in pdf.pages:
        for w in page.extract_words(extra_attrs=["size"]):
            sizes.append(round(w.get("size", 0), 1))
    return statistics.median(sizes) if sizes else 0


def heading_level(size, body_size):
    if body_size <= 0:
        return None
    ratio = size / body_size
    if ratio >= 1.8:
        return 1
    if ratio >= 1.5:
        return 2
    if ratio >= 1.25:
        return 3
    return None


def extract_page_images(page, page_index, pdf_stem, image_dir):
    saved = []
    for img_index, img in enumerate(page.images, start=1):
        try:
            bbox = (
                max(img["x0"], 0),
                max(img["top"], 0),
                min(img["x1"], page.width),
                min(img["bottom"], page.height),
            )
            if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                continue
            cropped = page.within_bbox(bbox)
            rendered = cropped.to_image(resolution=150)
            img_name = f"{pdf_stem}_p{page_index}_{img_index}.png"
            rendered.save(str(image_dir / img_name))
            saved.append((img["top"], img_name))
        except Exception:
            continue
    return saved


def convert_pdf(pdf_path, out_path=None, image_dir=None):
    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path.with_suffix(".md")
    image_dir_path = Path(image_dir) if image_dir else None

    with pdfplumber.open(str(pdf_path)) as pdf:
        body_size = collect_body_size(pdf)
        page_sections = []

        for page_index, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables]

            words = page.extract_words(extra_attrs=["size"])
            words = [w for w in words if not word_in_any_bbox(w, table_bboxes)]
            lines = group_words_into_lines(words)

            blocks = [(min(w["top"] for w in line), "text", line) for line in lines]
            blocks += [(t.bbox[1], "table", t) for t in tables]

            if image_dir_path:
                image_dir_path.mkdir(parents=True, exist_ok=True)
                for top, img_name in extract_page_images(
                    page, page_index, pdf_path.stem, image_dir_path
                ):
                    blocks.append((top, "image", img_name))

            blocks.sort(key=lambda b: b[0])

            page_md = []
            prev_bottom = None
            for top, kind, payload in blocks:
                if kind == "table":
                    rendered = render_table(payload.extract())
                    if rendered:
                        page_md.append(rendered)
                    prev_bottom = payload.bbox[3]
                    continue

                if kind == "image":
                    rel = f"{image_dir_path.name}/{payload}"
                    page_md.append(f"![]({rel})")
                    continue

                line = payload
                text = " ".join(w["text"] for w in line).strip()
                if not text:
                    continue
                avg_size = statistics.mean(w.get("size", body_size) for w in line)
                level = heading_level(avg_size, body_size)
                line_top = min(w["top"] for w in line)
                gap = None if prev_bottom is None else line_top - prev_bottom
                prev_bottom = max(w["bottom"] for w in line)

                if level:
                    page_md.append(f"{'#' * level} {text}")
                elif BULLET_RE.match(text):
                    page_md.append("- " + BULLET_RE.sub("", text))
                elif NUMBERED_RE.match(text):
                    page_md.append("1. " + NUMBERED_RE.sub("", text, count=1))
                else:
                    if (
                        gap is not None
                        and body_size > 0
                        and gap > body_size * 1.4
                        and page_md
                        and not page_md[-1].startswith("#")
                    ):
                        page_md.append("")
                    page_md.append(text)

            if page_md:
                page_sections.append("\n\n".join(page_md))

        markdown = "\n\n---\n\n".join(page_sections) + "\n"

    out_path.write_text(markdown, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Convert a PDF file to Markdown.")
    parser.add_argument("pdf", help="Path to the input PDF file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output Markdown file (default: same name, .md extension)",
    )
    parser.add_argument(
        "--images",
        help="Directory to extract embedded images into (relative paths are used in the Markdown)",
        default=None,
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"error: file not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    out = convert_pdf(args.pdf, args.output, args.images)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
