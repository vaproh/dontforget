import asyncio

from better_dontforget import cli
from better_dontforget.core import db as dbmod
from better_dontforget.core import systemd_install
from better_dontforget.core.config import Config
from better_dontforget.tui.app import BetterDontforgetApp


def test_capture_quick_note(xdg_tmp, capsys):
    rc = cli.main(["the rust tui library is ratatui"])
    assert rc == 0
    conn = dbmod.open_db()
    notes = dbmod.list_notes(conn, 10)
    assert any("ratatui" in n.raw_text for n in notes)
    dbmod.close_db(conn)


def test_no_color_flag(xdg_tmp, capsys):
    rc = cli.main(["--no-color", "a plaintext note for color test"])
    assert rc == 0
    conn = dbmod.open_db()
    notes = dbmod.list_notes(conn, 10)
    assert any("color test" in n.raw_text for n in notes)
    dbmod.close_db(conn)


def test_remind_recall_uses_literal_words(xdg_tmp, fake_provider):
    # Even when the AI returns generic keywords, the literal question words must
    # carry recall so remind finds the note.
    from better_dontforget.core.app import query_memory

    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="i lent rahul 69 rupees")
    rows, _ = query_memory(conn, fake_provider, "how much lent rahul?")
    dbmod.close_db(conn)
    assert any("rahul" in n.raw_text for n in rows)


def test_capture_encrypted(xdg_tmp):
    rc = cli.main(["--encrypt", "--passphrase", "pw", "secret note"])
    assert rc == 0
    conn = dbmod.open_db()
    note = next(n for n in dbmod.list_notes(conn, 10) if n.encrypted)
    assert note.encrypted is True
    dbmod.close_db(conn)


def test_capture_with_reminder(xdg_tmp):
    rc = cli.main(["--remind", "tomorrow 9am", "check the library"])
    assert rc == 0
    conn = dbmod.open_db()
    note = next(n for n in dbmod.list_notes(conn, 10) if n.reminder_at)
    assert note.reminder_at is not None
    dbmod.close_db(conn)


def test_config_set_and_show(xdg_tmp, capsys):
    assert cli.main(["config", "set", "provider", "openai"]) == 0
    assert Config.load().provider == "openai"
    # api_key masked in show
    cli.main(["config", "set", "api_key", "supersecret"])
    cli.main(["config", "show"])
    out = capsys.readouterr().out
    assert "supersecret" not in out
    assert "configured" in out


def test_search_command(xdg_tmp, capsys):
    cli.main(["ratatui is the rust tui library"])
    rc = cli.main(["search", "ratatui"])
    assert rc == 0
    assert "ratatui" in capsys.readouterr().out


def test_notify_pending_command(xdg_tmp, fake_notifier, monkeypatch):
    from datetime import datetime, timedelta

    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="due note", reminder_at=datetime.now() - timedelta(hours=1))
    dbmod.close_db(conn)

    monkeypatch.setattr(
        "better_dontforget.core.notifications.NotifySendNotifier",
        lambda: fake_notifier,
    )
    rc = cli.main(["notify-pending"])
    assert rc == 0
    assert len(fake_notifier.sent) == 1


def test_tui_smoke(xdg_tmp):
    app = BetterDontforgetApp()

    async def run():
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("q")

    asyncio.run(run())


def test_remind_warns_when_notifier_missing(xdg_tmp, capsys, monkeypatch):
    monkeypatch.setattr(systemd_install, "notifier_status", lambda: "not_installed")
    rc = cli.main(["remind", "anything?"])
    assert rc == 0
    assert "install-notifier" in capsys.readouterr().out


def test_capture_reminder_warns_when_notifier_missing(xdg_tmp, capsys, monkeypatch):
    monkeypatch.setattr(systemd_install, "notifier_status", lambda: "not_installed")
    rc = cli.main(["--remind", "tomorrow 9am", "check the library"])
    assert rc == 0
    assert "install-notifier" in capsys.readouterr().out


def test_help_is_proper_usage(capsys):
    rc = cli.main(["--help"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "USAGE" in out
    assert "OPTIONS" in out
    assert "COMMANDS" in out
    assert "install-notifier" in out
    assert "tui" in out
