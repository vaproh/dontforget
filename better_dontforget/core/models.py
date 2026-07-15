"""Note data model for Better Dontforget."""

from __future__ import annotations

from dataclasses import dataclass

REMINDER_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Note:
    id: int
    timestamp: str
    raw_text: str
    ai_tags: str
    reminder_at: str | None = None
    notified: bool = False
    encrypted: bool = False
    enc_content: str | None = None

    @property
    def display_text(self) -> str:
        if self.encrypted:
            return "(encrypted note — unlock to view)"
        return self.raw_text

    def to_search_row(self) -> dict[str, object]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "raw_text": self.display_text,
            "ai_tags": self.ai_tags,
        }
