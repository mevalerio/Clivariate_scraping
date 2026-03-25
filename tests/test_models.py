import unittest

from scraper.models import CrawlState, JournalRow


class TestModels(unittest.TestCase):
    def test_journal_row_to_dict(self):
        row = JournalRow(
            key="1234-5678",
            title="Test Journal",
            detail_url="https://example.com/journal/1",
            issn="1234-5678",
            table_page=3,
            raw={"cells": ["A", "B"]},
        )
        data = row.to_dict()
        self.assertEqual(data["key"], "1234-5678")
        self.assertEqual(data["table_page"], 3)
        self.assertEqual(data["raw"]["cells"], ["A", "B"])

    def test_crawl_state_roundtrip(self):
        state = CrawlState(
            next_table_page=2,
            seen_keys={"k1", "k2"},
            pending_detail_urls=["u1"],
            completed_detail_urls={"u2"},
            failed_detail_urls={"u3": 1},
        )

        data = state.to_dict()
        rebuilt = CrawlState.from_dict(data)

        self.assertEqual(rebuilt.next_table_page, 2)
        self.assertEqual(rebuilt.seen_keys, {"k1", "k2"})
        self.assertEqual(rebuilt.pending_detail_urls, ["u1"])
        self.assertEqual(rebuilt.completed_detail_urls, {"u2"})
        self.assertEqual(rebuilt.failed_detail_urls, {"u3": 1})


if __name__ == "__main__":
    unittest.main()
