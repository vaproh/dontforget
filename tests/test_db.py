import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from better_dontforget.core import db as dbmod


def make_legacy_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE memories ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, "
        "raw_text TEXT, ai_tags TEXT)"
    )
    conn.execute(
        "INSERT INTO memories (raw_text, ai_tags) VALUES (?, ?)",
        ("legacy wifi note", "network"),
    )
    conn.commit()
    conn.close()


def test_add_list_get_delete(xdg_tmp):
    conn = dbmod.open_db()
    nid = dbmod.add_note(conn, raw_text="hello world", ai_tags="greeting")
    note = dbmod.get_note(conn, nid)
    assert note is not None
    assert note.raw_text == "hello world"
    assert note.ai_tags == "greeting"
    assert not note.encrypted
    notes = dbmod.list_notes(conn, 10)
    assert any(n.id == nid for n in notes)
    assert dbmod.delete_note(conn, nid)
    assert dbmod.get_note(conn, nid) is None
    dbmod.close_db(conn)


def test_fts_search(xdg_tmp):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="the rust tui library is ratatui", ai_tags="rust,tui")
    dbmod.add_note(conn, raw_text="completely unrelated banana", ai_tags="fruit")
    rows = dbmod.search(conn, ["rust", "tui"])
    assert len(rows) >= 1
    assert any("ratatui" in r.raw_text for r in rows)
    dbmod.close_db(conn)


def test_legacy_migration_preserves_data(xdg_tmp):
    from better_dontforget.core.paths import db_path

    legacy = xdg_tmp / "memory.db"
    make_legacy_db(legacy)
    # Point the XDG data dir's db at the legacy file by copying into place.
    target = db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(legacy.read_bytes())
    conn = dbmod.open_db(target)
    notes = dbmod.list_notes(conn, 10)
    assert any(n.raw_text == "legacy wifi note" for n in notes)
    # new columns exist and are sane
    note = next(n for n in notes if n.raw_text == "legacy wifi note")
    assert note.reminder_at is None
    assert note.encrypted is False
    # FTS works after migration
    rows = dbmod.search(conn, ["wifi"])
    assert any("legacy wifi" in r.raw_text for r in rows)
    dbmod.close_db(conn)


def test_reminder_columns_persist(xdg_tmp):
    conn = dbmod.open_db()
    when = datetime.now() + timedelta(days=1)
    nid = dbmod.add_note(conn, raw_text="buy milk", reminder_at=when)
    note = dbmod.get_note(conn, nid)
    assert note is not None
    assert note.reminder_at is not None
    dbmod.close_db(conn)


def test_encryption_columns_persist(xdg_tmp):
    conn = dbmod.open_db()
    nid = dbmod.add_note(conn, raw_text="", encrypted=True, enc_content="salt:tok")
    note = dbmod.get_note(conn, nid)
    assert note is not None
    assert note.encrypted is True
    assert note.enc_content == "salt:tok"
    dbmod.close_db(conn)
