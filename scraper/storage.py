from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from scraper.models import CrawlState, JournalRow


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_state(path: Path) -> CrawlState:
    if not path.exists():
        return CrawlState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CrawlState.from_dict(payload)


def save_state(path: Path, state: CrawlState) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def append_jsonl(path: Path, row: JournalRow) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def write_csv(path: Path, records: Iterable[dict[str, Any]]) -> None:
    records = list(records)
    if not records:
        return

    ensure_parent(path)
    fieldnames = sorted({key for record in records for key in record})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
