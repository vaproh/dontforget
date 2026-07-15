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

    Capture is local and synchronous and makes no AI call. Encrypted notes are
    never sent to AI. Automatic tagging was removed in 1.1.0; ``tags`` is always
    an empty string (the ``ai_tags`` column is retained for compatibility).
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

    note_id = db.add_note(conn, raw_text=clean_text, ai_tags="", reminder_at=reminder_at)
    return note_id, "", reminder_at


def query_memory(conn, provider: AIProvider, question: str) -> tuple[list[Note], str | None]:
    """AI-assisted retrieval. Returns ``(rows, synthesized_answer)``.

    The question's own words are always searched as a baseline so recall does not
    depend entirely on the AI's keyword extraction (a weak model may drop the
    exact terms that appear in a note). AI keywords, when available, augment the
    literal terms.
    """
    keywords = question.split()
    if not isinstance(provider, NullProvider):
        keywords = ai.extract_keywords(provider, question) + keywords
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
