from __future__ import annotations

import argparse
import json
from pathlib import Path

from scraper.storage import append_jsonl, load_state, save_state, write_csv

DEFAULT_URL = "https://jcr.clarivate.com/jcr/browse-journals?app=jcr&referrer=target%3Dhttps:%2F%2Fjcr.clarivate.com%2Fjcr%2Fbrowse-journals&Init=Yes&authCode=null&SrcApp=IC2LS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape JCR browse-journals table and detail pages")
    parser.add_argument("--url", default=DEFAULT_URL, help="Browse journals URL")
    parser.add_argument("--state", default="data/state.json", help="Path to state file")
    parser.add_argument("--rows-jsonl", default="data/journals.jsonl", help="Path to table rows JSONL")
    parser.add_argument("--details-json", default="data/details.json", help="Path to detail JSON")
    parser.add_argument("--details-csv", default="data/details.csv", help="Path to detail CSV")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument("--min-delay", type=float, default=0.6, help="Minimum randomized delay between actions (seconds)")
    parser.add_argument("--max-delay", type=float, default=1.8, help="Maximum randomized delay between actions (seconds)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state_path = Path(args.state)
    rows_path = Path(args.rows_jsonl)
    details_json_path = Path(args.details_json)
    details_csv_path = Path(args.details_csv)

    state = load_state(state_path)

    from playwright.sync_api import sync_playwright
    from scraper.browse_table import BrowseTableScraper

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        context = browser.new_context()
        scraper = BrowseTableScraper(
            context=context,
            start_url=args.url,
            min_delay_seconds=args.min_delay,
            max_delay_seconds=args.max_delay,
        )

        rows = scraper.collect_table_rows(state)
        for row in rows:
            append_jsonl(rows_path, row)

        details = scraper.scrape_journal_details(state)
        save_state(state_path, state)

        details_json_path.parent.mkdir(parents=True, exist_ok=True)
        details_json_path.write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
        write_csv(details_csv_path, details)

        browser.close()

    print(f"Saved {len(rows)} new table rows")
    print(f"Saved {len(details)} detail records")
    print(f"State file: {state_path}")


if __name__ == "__main__":
    main()
