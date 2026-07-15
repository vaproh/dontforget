from better_dontforget.core import ai
from better_dontforget.core import db as dbmod
from better_dontforget.core.app import capture_note, decrypt_note, query_memory, search_memory
from better_dontforget.core.config import Config
from better_dontforget.core.providers import NullProvider, ProviderError


def test_extract_keywords(fake_provider):
    kws = ai.extract_keywords(fake_provider, "what did I owe?")
    assert kws == ["kw1", "kw2"]


def test_synthesize_raises_on_failure(fake_provider):
    fake_provider.fail = True
    try:
        ai.synthesize(fake_provider, "q", "ctx")
        assert False
    except ProviderError:
        pass


def test_query_memory_returns_answer(fake_provider, xdg_tmp):
    fake_provider.keywords = ["akash", "owe"]
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="I owe Akash 432 rs", ai_tags="debt")
    rows, answer = query_memory(conn, fake_provider, "how much do I owe?")
    assert len(rows) >= 1
    assert answer == "synthesized answer"
    dbmod.close_db(conn)


def test_query_memory_falls_back_without_ai(xdg_tmp):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="I owe Akash 432 rs", ai_tags="debt")
    rows, answer = query_memory(conn, NullProvider(), "akash")
    assert any("Akash" in r.raw_text for r in rows)
    assert answer is None
    dbmod.close_db(conn)


def test_search_memory(xdg_tmp):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="ratatui is the rust tui lib", ai_tags="rust")
    rows = search_memory(conn, "ratatui")
    assert any("ratatui" in r.raw_text for r in rows)
    dbmod.close_db(conn)


def test_capture_encrypts_without_ai(xdg_tmp):
    conn = dbmod.open_db()
    nid, tags, dt = capture_note(
        conn,
        Config(),
        NullProvider(),
        "secret thing",
        encrypt=True,
        passphrase="pw",
    )
    note = dbmod.get_note(conn, nid)
    assert note is not None
    assert note.encrypted is True
    assert note.raw_text == ""
    plain = decrypt_note(conn, nid, "pw")
    assert plain == "secret thing"
    dbmod.close_db(conn)
