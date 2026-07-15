"""Better Dontforget TUI (textual)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TextArea,
)

from ..core import db as dbmod
from ..core.app import capture_note, decrypt_note, search_memory
from ..core.config import VALID_PROVIDERS, Config
from ..core.providers import AIProvider, build_provider
from ..core.reminder_parser import parse_reminder


class MainScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("s", "settings", "Settings"),
        ("d", "delete", "Delete"),
        ("r", "remind", "Remind"),
        ("x", "add_encrypted", "Encrypted"),
        ("enter", "detail", "View"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(placeholder="Search notes… (Enter)", id="search")
            yield DataTable(id="notes", cursor_type="row")
            yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("id", "when", "note", "tags", "remind", "🔒")
        self.refresh_notes()

    def refresh_notes(self, rows=None) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=False)
        if rows is None:
            conn = self.app.db
            rows = dbmod.list_notes(conn, 200)
        for n in rows:
            table.add_row(
                str(n.id),
                n.timestamp,
                (n.display_text[:60] + ("…" if len(n.display_text) > 60 else "")),
                n.ai_tags,
                n.reminder_at or "",
                "🔒" if n.encrypted else "",
                key=n.id,
            )
        self.query_one("#status", Static).update(f"{len(rows)} notes")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search":
            return
        query = event.value.strip()
        if not query:
            self.refresh_notes()
            return
        rows = search_memory(self.app.db, query)
        self.refresh_notes(rows)

    def _selected_id(self) -> int | None:
        table = self.query_one(DataTable)
        try:
            return int(table.get_row_at(table.cursor_row)[0])
        except Exception:
            return None

    def action_add(self) -> None:
        self.app.push_screen(AddScreen(encrypt=False))

    def action_add_encrypted(self) -> None:
        self.app.push_screen(AddScreen(encrypt=True))

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_detail(self) -> None:
        nid = self._selected_id()
        if nid is not None:
            self.app.push_screen(DetailScreen(nid))

    def action_delete(self) -> None:
        nid = self._selected_id()
        if nid is None:
            return
        dbmod.delete_note(self.app.db, nid)
        self.refresh_notes()

    def action_remind(self) -> None:
        nid = self._selected_id()
        if nid is None:
            return
        self.app.push_screen(ReminderScreen(nid))

    def action_quit(self) -> None:
        self.app.exit()


class AddScreen(Screen):
    def __init__(self, encrypt: bool = False) -> None:
        super().__init__()
        self.encrypt = encrypt

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Label("New note" + (" (encrypted)" if self.encrypt else ""))
            yield TextArea(id="content", classes="grow")
            yield Input(placeholder="Reminder, e.g. 'tomorrow 9am' (optional)", id="remind")
            if self.encrypt:
                yield Input(placeholder="Passphrase", password=True, id="pass")
            yield Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
            )
        yield Footer()

    def action_quit(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id == "save":
            self._save()

    def _save(self) -> None:
        content = self.query_one("#content", TextArea).text.strip()
        if not content:
            self.query_one("#content", TextArea).focus()
            return
        remind_spec = self.query_one("#remind", Input).value.strip()
        reminder_at = None
        if remind_spec:
            _, reminder_at = parse_reminder("remind me " + remind_spec, datetime.now())
        passphrase = None
        if self.encrypt:
            passphrase = self.query_one("#pass", Input).value
            if not passphrase:
                return
        note_id, tags, dt = capture_note(
            self.app.db,
            self.app.config,
            self.app.provider,
            content,
            encrypt=self.encrypt,
            passphrase=passphrase,
            reminder_at=reminder_at,
        )
        self.app.pop_screen()
        self.app.query_one(MainScreen).refresh_notes()


class ReminderScreen(Screen):
    def __init__(self, note_id: int) -> None:
        super().__init__()
        self.note_id = note_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Label(f"Set reminder for note #{self.note_id}")
            yield Input(placeholder="e.g. 'tomorrow 9am' or 'in 2 hours'", id="spec")
            yield Horizontal(
                Button("Set", variant="primary", id="set"),
                Button("Clear", id="clear"),
                Button("Back", id="back"),
            )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        spec = self.query_one("#spec", Input).value.strip()
        if event.button.id == "clear":
            dbmod.update_note(self.app.db, self.note_id, clear_reminder=True)
        else:
            _, dt = parse_reminder("remind me " + spec, datetime.now())
            if dt:
                dbmod.update_note(self.app.db, self.note_id, reminder_at=dt)
        self.app.pop_screen()
        self.app.query_one(MainScreen).refresh_notes()


class DetailScreen(Screen):
    def __init__(self, note_id: int) -> None:
        super().__init__()
        self.note_id = note_id

    def compose(self) -> ComposeResult:
        yield Header()
        note = dbmod.get_note(self.app.db, self.note_id)
        if note is None:
            yield Static("Note not found.")
            yield Footer()
            return
        with VerticalScroll():
            yield Label(f"Note #{note.id}  ({note.timestamp})")
            if note.encrypted:
                yield Static("(encrypted — enter passphrase to view)", id="body")
                yield Input(placeholder="Passphrase", password=True, id="pass")
                yield Button("Unlock", id="unlock")
            else:
                yield Static(note.raw_text, id="body")
            if note.ai_tags:
                yield Label(f"Tags: {note.ai_tags}")
            yield Label(f"Reminder: {note.reminder_at or 'none'}")
            yield Horizontal(
                Button("Set reminder", id="remind"),
                Button("Delete", variant="error", id="delete"),
                Button("Back", id="back"),
            )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "delete":
            dbmod.delete_note(self.app.db, self.note_id)
            self.app.pop_screen()
            self.app.query_one(MainScreen).refresh_notes()
        elif event.button.id == "remind":
            self.app.pop_screen()
            self.app.push_screen(ReminderScreen(self.note_id))
        elif event.button.id == "unlock":
            passphrase = self.query_one("#pass", Input).value
            try:
                plain = decrypt_note(self.app.db, self.note_id, passphrase)
                self.query_one("#body", Static).update(plain)
            except Exception as exc:
                self.query_one("#body", Static).update(f"[decrypt failed] {exc}")


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        cfg = self.app.config
        yield Header()
        with VerticalScroll():
            yield Label("Settings")
            yield Label("AI provider")
            yield Select(
                [(p, p) for p in VALID_PROVIDERS],
                value=cfg.provider,
                id="provider",
                allow_blank=False,
            )
            yield Input(value=cfg.model, placeholder="model (blank = default)", id="model")
            yield Input(
                value=cfg.resolved_base_url(),
                placeholder="base_url (openai-compatible, optional)",
                id="base_url",
            )
            yield Input(
                value=cfg.api_key, placeholder="API key (optional; or use env)", id="api_key"
            )
            yield Label("Desktop notifications")
            yield Switch(value=cfg.notifications_enabled, id="notifications")
            yield Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Back", id="back"),
            )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        cfg = self.app.config
        cfg.provider = self.query_one("#provider", Select).value
        cfg.model = self.query_one("#model", Input).value.strip()
        cfg.base_url = self.query_one("#base_url", Input).value.strip()
        cfg.api_key = self.query_one("#api_key", Input).value.strip()
        cfg.notifications_enabled = self.query_one("#notifications", Switch).value
        cfg.save()
        self.app.config = cfg
        self.app.provider = build_provider(cfg)
        self.app.pop_screen()


class BetterDontforgetApp(App):
    CSS = """
    #notes { height: 1fr; }
    .grow { height: 6; }
    """

    config: Config
    db: sqlite3.Connection
    provider: AIProvider

    def __init__(self) -> None:
        super().__init__()
        from ..cli_helpers import load_app_context

        self.config, self.db, self.provider = load_app_context()

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def on_unmount(self) -> None:
        try:
            dbmod.close_db(self.db)
        except Exception:
            pass
