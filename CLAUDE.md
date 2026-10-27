# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Semi Insight" — a Korean-language semiconductor-materials news briefing tool. It collects Google News RSS headlines for a keyword list, asks Google Gemini to write an analyst-style daily report, and archives the results. Code comments, prompts, log messages and UI text are in Korean; keep that convention.

There is no test suite, linter config, or build step.

## Commands

```bash
pip install -r requirements.txt

# Streamlit dashboard (port 8501; the devcontainer runs this automatically)
streamlit run app.py

# Headless daily report generator (what GitHub Actions runs)
GEMINI_API_KEY=... GITHUB_TOKEN=... REPO_NAME=owner/repo python generate_report.py
```

`app.py` reads secrets from `.streamlit/secrets.toml` (gitignored): `GEMINI_API_KEY`, `GITHUB_TOKEN`, `REPO_NAME`. Without `GITHUB_TOKEN` it falls back to local JSON files and skips GitHub sync.

## Architecture

Two independent entry points share the same data files but **no code** — `generate_report.py` is a deliberate Streamlit-free copy of the fetch/report logic in `app.py`. When changing news collection, the Gemini prompt/request, or constants (`MAX_HISTORY`, `NEWS_LIMIT`, `_NEWS_EDITIONS`, etc.), update both files so they stay in sync.

- **`generate_report.py`** — run by `.github/workflows/daily_report.yml` daily at 21:00 UTC (06:00 KST). Picks the target KST date (previous day if before 06:00), skips if that date already exists in history, loads keywords, fetches news in the window 12:00 KST prior day → 06:00 KST target day, calls Gemini, and prepends the entry to history.
- **`app.py`** — Streamlit UI: keyword manager, manual report generation, and a month-grouped archive viewer of past reports. Theme tokens (light/dark) are hand-coded from the design spec in `apple.md`, injected as CSS.

### Data / persistence

- **The GitHub repo itself is the database.** Both scripts read and write `keywords.json` and `daily_history.json` through the GitHub Contents API (PyGithub), which creates the `[Auto] Update daily_history.json ...` commits. The workflow does not `git commit` — the script commits via the API. Expect frequent upstream bot commits to `daily_history.json`; pull before editing it.
- `keywords.json`: `{"Daily Report": [keyword, ...]}`.
- `daily_history.json`: list, newest first, capped at `MAX_HISTORY = 30` (to stay under the Contents API 1MB limit). Entry shape: `date` (YYYY-MM-DD), `report` (markdown), `articles` (list of `{Title, Link, Date, Source, ParsedDate}`), `auto_generated`, `generated_at`.

### News collection

Google News RSS search per keyword, queried in both the KR (`hl=ko`) and US (`hl=en-US`) editions, parallelized with a thread pool. Per-keyword limit is `max(8, NEWS_LIMIT // len(keywords))`. Results outside the time window are dropped; if fewer than 5 remain, it falls back to the unfiltered raw results (no re-crawl). Requests use `verify=False` intentionally.

### Gemini

Called via REST (`generativelanguage.googleapis.com/v1beta/.../generateContent`), not an SDK. Default model `gemini-2.0-flash`; on 404 it queries available models and falls back. `thinkingConfig.thinkingBudget = 0` is required — gemini-2.5 thinking tokens previously ate the `maxOutputTokens` budget and truncated reports (not the article count). `app.py` additionally injects citation links from the article list into the generated report.
