import json
import tempfile
import unittest
from pathlib import Path

from scraper.models import CrawlState, JournalRow
from scraper.storage import append_jsonl, load_state, save_state, write_csv


class TestStorage(unittest.TestCase):
    def test_state_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "state.json"
            state = CrawlState(seen_keys={"alpha"}, pending_detail_urls=["https://example.com/a"])

            save_state(state_path, state)
            loaded = load_state(state_path)

            self.assertEqual(loaded.seen_keys, {"alpha"})
            self.assertEqual(loaded.pending_detail_urls, ["https://example.com/a"])

    def test_jsonl_and_csv_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            jsonl_path = base / "journals.jsonl"
            csv_path = base / "details.csv"

            row = JournalRow(key="k", title="T", detail_url="https://example.com")
            append_jsonl(jsonl_path, row)

            lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["title"], "T")

            records = [{"detail_url": "https://example.com", "publisher": "P"}]
            write_csv(csv_path, records)
            csv_data = csv_path.read_text(encoding="utf-8")
            self.assertIn("detail_url", csv_data)
            self.assertIn("publisher", csv_data)


if __name__ == "__main__":
    unittest.main()
