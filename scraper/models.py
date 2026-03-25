from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class JournalRow:
    key: str
    title: str
    detail_url: str
    issn: str | None = None
    eissn: str | None = None
    category: str | None = None
    publisher: str | None = None
    table_page: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlState:
    next_table_page: int = 1
    seen_keys: set[str] = field(default_factory=set)
    pending_detail_urls: list[str] = field(default_factory=list)
    completed_detail_urls: set[str] = field(default_factory=set)
    failed_detail_urls: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["seen_keys"] = sorted(self.seen_keys)
        payload["completed_detail_urls"] = sorted(self.completed_detail_urls)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CrawlState":
        return cls(
            next_table_page=payload.get("next_table_page", 1),
            seen_keys=set(payload.get("seen_keys", [])),
            pending_detail_urls=list(payload.get("pending_detail_urls", [])),
            completed_detail_urls=set(payload.get("completed_detail_urls", [])),
            failed_detail_urls=dict(payload.get("failed_detail_urls", {})),
        )
