---
name: pdf-to-markdown
description: Convert a PDF file into a Markdown (.md) file, preserving headings, paragraphs, bullet/numbered lists, and tables, with optional extraction of embedded images. Use this whenever the user asks to convert a PDF to Markdown/.md, turn a PDF report into text for this project, or extract a PDF's structured content (e.g. a semiconductor market report) as Markdown.
---

# PDF → Markdown Conversion

Converts a PDF into a single Markdown file using `pdfplumber` for text,
font-size, and table extraction. Headings, lists, and tables are inferred
heuristically — always skim the output and fix obvious misclassifications
(e.g. a large pull-quote wrongly tagged as a heading) before treating it as
final.

## When to use

- The user gives a `.pdf` file (path or upload) and asks for Markdown, plain
  text, or "extract the content" in a structured form.
- A PDF report needs to be summarized or fed into this project (e.g. as
  source material for `app.py` or `generate_report.py`).

## How it works

1. Ensure `pdfplumber` is installed:
   ```bash
   pip install -r .claude/skills/pdf-to-markdown/requirements.txt
   ```
2. Run the converter:
   ```bash
   python3 .claude/skills/pdf-to-markdown/scripts/pdf_to_md.py <input.pdf> -o <output.md>
   ```
   - `-o/--output` is optional; defaults to the input filename with a `.md`
     extension in the same directory.
   - `--images <dir>` additionally extracts embedded images as PNGs into
     `<dir>` and references them from the Markdown with relative paths.
3. Open the generated `.md` file and spot-check:
   - Heading levels (`#`, `##`, `###`) are assigned by comparing each line's
     font size to the document's median body-text size — a document with
     unusual typography (e.g. all-caps body text at one size) can produce
     wrong levels.
   - Tables only render correctly when pdfplumber can detect them (usually
     requires visible ruling lines or a consistent lattice); a table drawn
     with plain positioned text and no lines may fall back to space-joined
     text instead of a Markdown table — verify and hand-fix if so.
   - Multi-column layouts are read left-to-right by line position and are
     not column-aware; for two-column PDFs, verify reading order and
     re-order manually if columns got interleaved.

## Notes

- The script has no dependency on the rest of this repository — it can be
  pointed at any PDF path.
- For scanned/image-only PDFs (no extractable text layer), this script will
  produce little or no output; use OCR first (see the general-purpose `pdf`
  skill, if available) and then re-run this conversion on the OCR'd PDF.
