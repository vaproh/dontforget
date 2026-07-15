"""High-level operations composing storage, AI, crypto and reminders.

These functions are used by both the CLI and the TUI so behavior stays
consistent and testable without a UI.
"""

from __future__ import annotations

from datetime import datetime

from . import ai, crypto, db, reminder_parser
from .config import Config
from .models import Note
from .providers import AIProvider, NullProvider, ProviderError


def capture_note(
    conn,
    config: Config,
    provider: AIProvider,
    text: str,
    *,
    encrypt: bool = False,
    passphrase: str | None = None,
    reminder_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[int, str, datetime | None]:
    """Store a quick note. Returns ``(note_id, tags, reminder_at)``.

    Capture is local and synchronous. AI tagging is best-effort: if the provider
    is unavailable or fails, the note is still saved (without tags). Encrypted
    notes are never sent to AI.
    """
    clean_text, parsed_dt = reminder_parser.parse_reminder(text, now)
    if reminder_at is None:
        reminder_at = parsed_dt

    if encrypt:
        if not passphrase:
            raise ValueError("A passphrase is required to encrypt a note.")
        enc_content = crypto.encrypt(passphrase, clean_text)
        note_id = db.add_note(
            conn,
            raw_text="",
            ai_tags="",
            reminder_at=reminder_at,
            encrypted=True,
            enc_content=enc_content,
        )
        return note_id, "", reminder_at

    tags: list[str] = []
    if not isinstance(provider, NullProvider):
        tags = ai.generate_tags(provider, clean_text)
    tags_str = ", ".join(tags)
    note_id = db.add_note(conn, raw_text=clean_text, ai_tags=tags_str, reminder_at=reminder_at)
    return note_id, tags_str, reminder_at


def query_memory(conn, provider: AIProvider, question: str) -> tuple[list[Note], str | None]:
    """AI-assisted retrieval. Returns ``(rows, synthesized_answer)``.

    Falls back to raw FTS listing when AI is unavailable.
    """
    keywords = (
        ai.extract_keywords(provider, question)
        if not isinstance(provider, NullProvider)
        else question.split()
    )
    rows = db.search(conn, keywords)
    answer: str | None = None
    if rows and not isinstance(provider, NullProvider):
        context = ai.format_context(rows)
        try:
            answer = ai.synthesize(provider, question, context)
        except ProviderError:
            answer = None
    return rows, answer


def search_memory(conn, query: str) -> list[Note]:
    keywords = query.split()
    return db.search(conn, keywords)


def decrypt_note(conn, note_id: int, passphrase: str) -> str:
    note = db.get_note(conn, note_id)
    if note is None or not note.encrypted:
        raise ValueError("Note is not encrypted.")
    return crypto.decrypt(passphrase, note.enc_content or "")
