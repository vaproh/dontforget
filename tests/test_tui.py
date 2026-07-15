"""Tests for the Better Dontforget TUI (textual)."""

import asyncio

from textual.widgets import DataTable, TextArea

from better_dontforget.core import db as dbmod
from better_dontforget.tui.app import BetterDontforgetApp


def test_tui_edit_note(xdg_tmp):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="original text", ai_tags="old")
    dbmod.close_db(conn)

    app = BetterDontforgetApp()

    async def run():
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one(DataTable)
            table.move_cursor(row=0)
            await pilot.pause()
            await pilot.press("e")
            await pilot.pause()
            app.screen.query_one("#content", TextArea).text = "edited text"
            await pilot.click("#save")
            await pilot.pause()

    asyncio.run(run())

    conn = dbmod.open_db()
    note = dbmod.list_notes(conn, 10)[0]
    dbmod.close_db(conn)
    assert note.raw_text == "edited text"


def test_tui_theme_toggle(xdg_tmp):
    app = BetterDontforgetApp()

    async def run():
        async with app.run_test() as pilot:
            await pilot.pause()
            initial = app.dark
            await pilot.press("t")
            await pilot.pause()
            assert app.dark is not initial

    asyncio.run(run())


def test_tui_preview_on_highlight(xdg_tmp):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="preview me", ai_tags="tag")
    dbmod.close_db(conn)

    app = BetterDontforgetApp()

    async def run():
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one(DataTable)
            table.move_cursor(row=0)
            await pilot.pause()
            preview = app.screen.query_one("#preview")
            assert "preview me" in str(preview._Static__content)

    asyncio.run(run())
