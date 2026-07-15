"""SQLite storage engine for Better Dontforget.

Preserves the upstream architecture: a standard ``memories`` table backed by an
FTS5 ``memories_idx`` index kept in sync via triggers. The schema is extended
with optional reminder and encryption columns through a backward-compatible
migration. Existing upstream ``memory.db`` files are migrated on first run.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import REMINDER_FORMAT, Note
from .paths import db_path, legacy_db_candidates


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def _migrate_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "memories"):
        conn.execute(
            """
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                raw_text TEXT,
                ai_tags TEXT,
                reminder_at DATETIME,
                notified INTEGER DEFAULT 0,
                encrypted INTEGER DEFAULT 0,
                enc_content TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_idx
            USING fts5(raw_text, ai_tags, content='memories', content_rowid='id');
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
              INSERT INTO memories_idx(rowid, raw_text, ai_tags)
              VALUES (new.id, new.raw_text, new.ai_tags);
            END;
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
              INSERT INTO memories_idx(memories_idx, rowid, raw_text, ai_tags)
              VALUES ('delete', old.id, old.raw_text, old.ai_tags);
            END;
            """
        )
        # Seed FTS index with any pre-existing rows (e.g. after migration copy).
        conn.execute(
            "INSERT INTO memories_idx(rowid, raw_text, ai_tags) "
            "SELECT id, raw_text, ai_tags FROM memories WHERE id NOT IN "
            "(SELECT rowid FROM memories_idx);"
        )
    else:
        for col, ddl in (
            ("reminder_at", "DATETIME"),
            ("notified", "INTEGER DEFAULT 0"),
            ("encrypted", "INTEGER DEFAULT 0"),
            ("enc_content", "TEXT"),
        ):
            if not _column_exists(conn, "memories", col):
                conn.execute(f"ALTER TABLE memories ADD COLUMN {col} {ddl}")
        if not _table_exists(conn, "memories_idx"):
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_idx
                USING fts5(raw_text, ai_tags, content='memories', content_rowid='id');
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                  INSERT INTO memories_idx(rowid, raw_text, ai_tags)
                  VALUES (new.id, new.raw_text, new.ai_tags);
                END;
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                  INSERT INTO memories_idx(memories_idx, rowid, raw_text, ai_tags)
                  VALUES ('delete', old.id, old.raw_text, old.ai_tags);
                END;
                """
            )
            conn.execute(
                "INSERT INTO memories_idx(rowid, raw_text, ai_tags) "
                "SELECT id, raw_text, ai_tags FROM memories"
            )
    conn.commit()


def _migrate_legacy_db(target: Path) -> None:
    """Copy an upstream memory.db into the XDG data location if we have none."""
    if target.exists():
        return
    for candidate in legacy_db_candidates():
        if candidate.exists():
            shutil.copyfile(candidate, target)
            break


def open_db(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    _migrate_legacy_db(path)
    conn = _connect(path)
    _migrate_schema(conn)
    return conn


def close_db(conn: sqlite3.Connection) -> None:
    conn.close()


def add_note(
    conn: sqlite3.Connection,
    *,
    raw_text: str = "",
    ai_tags: str = "",
    reminder_at: datetime | None = None,
    encrypted: bool = False,
    enc_content: str | None = None,
) -> int:
    reminder_str = reminder_at.strftime(REMINDER_FORMAT) if reminder_at else None
    cur = conn.execute(
        """
        INSERT INTO memories (raw_text, ai_tags, reminder_at, notified, encrypted, enc_content)
        VALUES (?, ?, ?, 0, ?, ?)
        """,
        (raw_text, ai_tags, reminder_str, 1 if encrypted else 0, enc_content),
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def get_note(conn: sqlite3.Connection, note_id: int) -> Note | None:
    row = conn.execute("SELECT * FROM memories WHERE id = ?", (note_id,)).fetchone()
    return _row_to_note(row) if row else None


def list_notes(conn: sqlite3.Connection, limit: int = 50) -> list[Note]:
    rows = conn.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_row_to_note(r) for r in rows]


def delete_note(conn: sqlite3.Connection, note_id: int) -> bool:
    cur = conn.execute("DELETE FROM memories WHERE id = ?", (note_id,))
    conn.commit()
    return cur.rowcount > 0


def update_note(
    conn: sqlite3.Connection,
    note_id: int,
    *,
    raw_text: str | None = None,
    ai_tags: str | None = None,
    reminder_at: datetime | None = None,
    clear_reminder: bool = False,
    encrypted: bool | None = None,
    enc_content: str | None = None,
) -> bool:
    sets: list[str] = []
    params: list[object] = []
    if raw_text is not None:
        sets.append("raw_text = ?")
        params.append(raw_text)
    if ai_tags is not None:
        sets.append("ai_tags = ?")
        params.append(ai_tags)
    if clear_reminder:
        sets.append("reminder_at = NULL")
        sets.append("notified = 0")
    elif reminder_at is not None:
        sets.append("reminder_at = ?")
        params.append(reminder_at.strftime(REMINDER_FORMAT))
        sets.append("notified = 0")
    if encrypted is not None:
        sets.append("encrypted = ?")
        params.append(1 if encrypted else 0)
    if enc_content is not None:
        sets.append("enc_content = ?")
        params.append(enc_content)
    if not sets:
        return False
    params.append(note_id)
    conn.execute(f"UPDATE memories SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    return True


def _clean_keywords(keywords: list[str]) -> list[str]:
    return [re.sub(r"[^a-zA-Z0-9]", "", k) for k in keywords if k]


def search(conn: sqlite3.Connection, keywords: list[str], limit: int = 30) -> list[Note]:
    clean = _clean_keywords(keywords)
    if not clean:
        return []
    ids: list[int] = []
    for joiner in (" AND ", " OR "):
        query = joiner.join(f'"{k}"' for k in clean)
        try:
            rows = conn.execute(
                "SELECT rowid FROM memories_idx WHERE memories_idx MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        ids = [r["rowid"] for r in rows]
        if len(ids) >= 5:
            break
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    notes = conn.execute(f"SELECT * FROM memories WHERE id IN ({placeholders})", ids).fetchall()
    by_id = {n["id"]: _row_to_note(n) for n in notes}
    return [by_id[i] for i in ids if i in by_id][:limit]


def get_due_reminders(conn: sqlite3.Connection, now: datetime | None = None) -> list[Note]:
    now = now or datetime.now()
    marker = now.strftime(REMINDER_FORMAT)
    rows = conn.execute(
        "SELECT * FROM memories WHERE reminder_at IS NOT NULL "
        "AND reminder_at <= ? AND notified = 0 ORDER BY reminder_at ASC",
        (marker,),
    ).fetchall()
    return [_row_to_note(r) for r in rows]


def mark_notified(conn: sqlite3.Connection, note_ids: list[int]) -> None:
    if not note_ids:
        return
    placeholders = ",".join("?" * len(note_ids))
    conn.execute(f"UPDATE memories SET notified = 1 WHERE id IN ({placeholders})", note_ids)
    conn.commit()


def count_notes(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])


def _row_to_note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"],
        timestamp=row["timestamp"],
        raw_text=row["raw_text"] or "",
        ai_tags=row["ai_tags"] or "",
        reminder_at=row["reminder_at"],
        notified=bool(row["notified"]),
        encrypted=bool(row["encrypted"]),
        enc_content=row["enc_content"],
    )
