# Clivariate_scraping

A Python + Playwright scraper that:
1. walks the paginated JCR **Browse Journals** table,
2. collects each journal row,
3. visits each journal detail page,
4. stores resumable crawl state.

## Target

- `https://jcr.clarivate.com/jcr/browse-journals?app=jcr&referrer=target%3Dhttps:%2F%2Fjcr.clarivate.com%2Fjcr%2Fbrowse-journals&Init=Yes&authCode=null&SrcApp=IC2LS`

## Project layout

```text
scraper/
  browse_table.py      # Pagination + row collection + detail crawl
  journal_detail.py    # Generic detail extraction helper
  models.py            # Dataclasses for rows/state
  storage.py           # State + file writers
  run.py               # CLI entrypoint
tests/
  test_models.py
  test_storage.py
requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
python -m scraper.run --headed
```

With randomized delays between navigation actions:

```bash
python -m scraper.run --headed --min-delay 1.2 --max-delay 3.0
```

Quick small-batch test (example: first 2 table pages and 5 detail URLs):

```bash
python -m scraper.run --headed --max-table-pages 2 --max-detail-urls 5
```

Table-only mode (skip all journal detail page visits):

```bash
python -m scraper.run --headed --table-only
```

Minimal verification run (first part of table only):

```bash
python -m scraper.run --headed --table-only --max-table-pages 1
```

Headless mode (default):

```bash
python -m scraper.run
```

## How to test

### 1) Unit tests (no browser required)

```bash
python -m unittest discover -s tests -v
```

This validates:
- model serialization/deserialization (`JournalRow`, `CrawlState`),
- state save/load,
- JSONL and CSV writing.

### 2) CLI wiring check

```bash
python -m scraper.run --help
```

If this fails with `ModuleNotFoundError: playwright`, run `pip install -r requirements.txt`.

### 3) End-to-end smoke test (real site)

```bash
python -m scraper.run --headed
```

Then verify outputs:

```bash
python - <<'PY'
from pathlib import Path
for p in [
  Path('data/state.json'),
  Path('data/journals.jsonl'),
  Path('data/details.json'),
  Path('data/details.csv'),
]:
  print(p, 'exists=' + str(p.exists()), 'size=' + (str(p.stat().st_size) if p.exists() else '0'))
PY
```

## Output files

- `data/state.json`: resumable crawl state.
- `data/journals.jsonl`: table rows discovered.
- `data/details.json`: detail records from journal subpages.
- `data/details.csv`: CSV export of detail records.

## Notes

- You likely need valid JCR access/authentication in the browser session.
- Selectors are intentionally centralized in `scraper/browse_table.py` (`Selectors` dataclass) to adjust when UI changes.
- For Angular Material pages (like `mat-table`), default row parsing now supports `mat-table mat-row` in addition to classic `table tbody tr`.
- To reduce bot-like timing patterns, use `--min-delay` / `--max-delay` to randomize pauses between table/detail navigation actions.
- To run a lightweight smoke test, use `--max-table-pages` and `--max-detail-urls` so you only scrape a small subset.
- If you only need data from the main browse table, run with `--table-only` to skip detail-page crawling completely.
- The scraper attempts to auto-accept common cookie consent banners (e.g., `Accept`, `I Agree`, OneTrust buttons) before table extraction.
- For robustness: keep retries conservative and review `failed_detail_urls` in `state.json` after runs.
