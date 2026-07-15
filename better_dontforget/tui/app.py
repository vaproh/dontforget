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

from ..core import crypto
from ..core import db as dbmod
from ..core.app import capture_note, decrypt_note, search_memory
from ..core.config import VALID_PROVIDERS, Config
from ..core.providers import AIProvider, build_provider
from ..core.reminder_parser import parse_reminder


class MainScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("x", "add_encrypted", "Encrypted"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("r", "remind", "Remind"),
        ("enter", "detail", "View"),
        ("s", "settings", "Settings"),
        ("t", "theme", "Theme"),
        ("/", "focus_search", "Search"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search notes… (type, then Enter)", id="search")
        with Horizontal(classes="main-split"):
            yield DataTable(id="notes", cursor_type="row")
            with Vertical(id="preview-pane"):
                yield Label("Preview", id="preview-title")
                yield Static(id="preview", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("id", "when", "note", "remind", "🔒")
        self.refresh_notes()
        # Focus the table (not the search box) so single-key bindings work.
        table.focus()

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
                n.reminder_at or "",
                "🔒" if n.encrypted else "",
                key=n.id,
            )
        self.query_one("#preview-title", Label).update(f"Preview — {len(rows)} note(s)")
        if rows:
            self._update_preview(rows[0].id)
        else:
            self._update_preview(None)

    def on_data_table_row_highlighted(self, event) -> None:
        try:
            nid = int(event.row_key.value)
        except Exception:
            return
        self._update_preview(nid)

    def _update_preview(self, nid) -> None:
        preview = self.query_one("#preview", Static)
        if nid is None:
            preview.update("")
            return
        note = dbmod.get_note(self.app.db, nid)
        if note is None:
            preview.update("")
            return
        lines = [f"#{note.id}  {note.timestamp}"]
        if note.encrypted:
            lines.append("(encrypted — open the detail view and unlock to read)")
        else:
            lines.append(note.raw_text)
        lines.append(f"Reminder: {note.reminder_at or 'none'}")
        preview.update("\n\n".join(lines))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search":
            return
        query = event.value.strip()
        if not query:
            self.refresh_notes()
            return
        rows = search_memory(self.app.db, query)
        self.refresh_notes(rows)
        self.query_one(DataTable).focus()

    def _selected_id(self) -> int | None:
        table = self.query_one(DataTable)
        try:
            return int(table.get_row_at(table.cursor_row)[0])
        except Exception:
            return None

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_add(self) -> None:
        self.app.push_screen(AddScreen(encrypt=False))

    def action_add_encrypted(self) -> None:
        self.app.push_screen(AddScreen(encrypt=True))

    def action_edit(self) -> None:
        nid = self._selected_id()
        if nid is not None:
            self.app.push_screen(EditScreen(nid))

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
        if nid is not None:
            self.app.push_screen(ReminderScreen(nid))

    def action_theme(self) -> None:
        self.app.dark = not self.app.dark
        self.app.config.dark = self.app.dark
        self.app.config.save()
        self.app.notify(f"Theme: {'dark' if self.app.dark else 'light'}")

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
        capture_note(
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


class EditScreen(Screen):
    def __init__(self, note_id: int) -> None:
        super().__init__()
        self.note_id = note_id
        self.note = dbmod.get_note(self.app.db, note_id)
        self._unlocked = False
        self._pass: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        note = self.note
        if note is None:
            yield Static("Note not found.")
            yield Footer()
            return
        assert note is not None
        with VerticalScroll():
            yield Label(f"Edit note #{self.note_id}")
            if note.encrypted:
                yield Input(placeholder="Passphrase to unlock", password=True, id="pass")
                yield Button("Unlock", variant="primary", id="unlock")
                yield TextArea(id="content", classes="grow", disabled=True)
            else:
                yield TextArea(note.raw_text, id="content", classes="grow")
            yield Input(
                value=note.reminder_at or "",
                placeholder="Reminder, e.g. 'tomorrow 9am' (optional)",
                id="remind",
            )
            yield Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
            )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id == "unlock":
            self._unlock()
            return
        if event.button.id == "save":
            self._save()

    def _unlock(self) -> None:
        self._pass = self.query_one("#pass", Input).value
        try:
            plain = decrypt_note(self.app.db, self.note_id, self._pass)
        except Exception:
            self.query_one("#pass", Input).placeholder = "Wrong passphrase, try again"
            return
        ta = self.query_one("#content", TextArea)
        ta.text = plain
        ta.disabled = False
        self._unlocked = True

    def _save(self) -> None:
        note = self.note
        assert note is not None
        content = self.query_one("#content", TextArea).text.strip()
        if not content:
            return
        spec = self.query_one("#remind", Input).value.strip()
        reminder_at = None
        if spec:
            _, reminder_at = parse_reminder("remind me " + spec, datetime.now())
        if note.encrypted:
            if not self._unlocked or not self._pass:
                self.app.notify("Unlock the note before saving.")
                return
            enc = crypto.encrypt(self._pass, content)
            dbmod.update_note(
                self.app.db,
                self.note_id,
                raw_text="",
                ai_tags="",
                reminder_at=reminder_at,
                encrypted=True,
                enc_content=enc,
            )
        else:
            dbmod.update_note(
                self.app.db,
                self.note_id,
                raw_text=content,
                ai_tags="",
                reminder_at=reminder_at,
            )
        self._return_to_main()

    def _return_to_main(self) -> None:
        self.app.pop_screen()
        main = self.app.query(MainScreen)
        if main:
            main.first().refresh_notes()


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
        assert note is not None
        with VerticalScroll():
            yield Label(f"Note #{note.id}  ({note.timestamp})")
            if note.encrypted:
                yield Static("(encrypted — enter passphrase to view)", id="body", markup=False)
                yield Input(placeholder="Passphrase", password=True, id="pass")
                yield Button("Unlock", id="unlock")
            else:
                yield Static(note.raw_text, id="body", markup=False)
            yield Label(f"Reminder: {note.reminder_at or 'none'}")
            yield Horizontal(
                Button("Edit", id="edit"),
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
        elif event.button.id == "edit":
            self.app.pop_screen()
            self.app.push_screen(EditScreen(self.note_id))
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
            yield Label("Theme")
            yield Switch(value=cfg.dark, id="dark")
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
        cfg.dark = self.query_one("#dark", Switch).value
        cfg.save()
        self.app.config = cfg
        self.app.provider = build_provider(cfg)
        self.app.dark = cfg.dark
        self.app.pop_screen()


class BetterDontforgetApp(App):
    CSS = """
    #search { dock: top; }
    .main-split { height: 1fr; }
    #notes { width: 2fr; height: 1fr; }
    #preview-pane { width: 1fr; height: 1fr; border: round $accent; padding: 1; }
    #preview { height: 1fr; }
    .grow { height: 10; }
    """

    config: Config
    db: sqlite3.Connection
    provider: AIProvider

    def __init__(self) -> None:
        super().__init__()
        from ..cli_helpers import load_app_context

        self.config, self.db, self.provider = load_app_context()

    def on_mount(self) -> None:
        self.dark = self.config.dark
        self.push_screen(MainScreen())

    def on_unmount(self) -> None:
        try:
            dbmod.close_db(self.db)
        except Exception:
            pass
