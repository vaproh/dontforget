"""Command-line interface for Better Dontforget.

Dispatch rules:
* ``better-dontforget`` with no arguments launches the TUI.
* ``better-dontforget "some text"`` captures a quick note (low friction).
* Subcommands (``remind``, ``search``, ``list``, ``delete``, ``config``,
  ``notify-pending``, ``tui``) provide the rest of the workflow.
"""

from __future__ import annotations

import getpass
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .core import db as dbmod
from .core import systemd_install
from .core.app import capture_note, query_memory, search_memory
from .core.config import Config, describe_secret
from .core.paths import config_path
from .core.providers import build_provider
from .core.reminder_parser import parse_reminder

console = Console()

KNOWN_SUBCOMMANDS = {
    "tui",
    "remind",
    "ask",
    "q",
    "search",
    "find",
    "list",
    "ls",
    "delete",
    "del",
    "rm",
    "config",
    "models",
    "notify-pending",
    "notify",
    "install-notifier",
    "uninstall-notifier",
    "version",
    "help",
}


def _config() -> Config:
    return Config.load()


def _provider(config: Config):
    return build_provider(config)


def _print_note_row(note) -> None:
    reminder = note.reminder_at or ""
    enc = " 🔒" if note.encrypted else ""
    rem = f" ⏰{reminder}" if reminder else ""
    console.print(f"[dim]#{note.id}[/dim] {note.display_text}{enc}{rem}")


def _warn_notifier_if_inactive(config) -> None:
    """Print a hint to install/start the notifier when reminders can't fire."""
    if not getattr(config, "notifications_enabled", True):
        return
    try:
        state = systemd_install.notifier_status()
    except Exception:
        return
    if state == systemd_install.NotifierState.NOT_INSTALLED:
        console.print(
            "[yellow]ℹ Reminders won't fire until the notifier is active. "
            "Set it up:[/yellow] [cyan]bdf install-notifier[/cyan]"
        )
    elif state == systemd_install.NotifierState.INSTALLED_INACTIVE:
        console.print(
            "[yellow]ℹ The reminder timer is installed but not running. "
            "Start it:[/yellow] [cyan]systemctl --user enable --now "
            "better-dontforget-notify.timer[/cyan]"
        )


def cmd_capture(argv: list[str]) -> int:
    encrypt = False
    reminder_spec: str | None = None
    passphrase: str | None = None
    text_parts: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--encrypt":
            encrypt = True
        elif arg == "--remind":
            i += 1
            reminder_spec = argv[i] if i < len(argv) else ""
        elif arg == "--passphrase":
            i += 1
            passphrase = argv[i] if i < len(argv) else ""
        elif arg.startswith("--remind="):
            reminder_spec = arg.split("=", 1)[1]
        elif arg.startswith("--passphrase="):
            passphrase = arg.split("=", 1)[1]
        else:
            text_parts.append(arg)
        i += 1

    text = " ".join(text_parts).strip()

    if not text:
        editor = os.environ.get("EDITOR", "vim")
        try:
            import tempfile

            tf = tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False)
            tf.close()
            os.system(f"{editor} {tf.name}")
            with open(tf.name) as fh:
                text = fh.read().strip()
            os.unlink(tf.name)
        except Exception:
            console.print("[red]Could not open editor; pass text directly.[/red]")
            return 1
    if not text:
        console.print("[red]Aborted: empty note.[/red]")
        return 1

    config = _config()
    provider = _provider(config)

    reminder_at: datetime | None = None
    if reminder_spec:
        _, reminder_at = parse_reminder("remind me " + reminder_spec, datetime.now())

    if encrypt and passphrase is None:
        passphrase = getpass.getpass("Passphrase to encrypt this note: ")

    conn = dbmod.open_db()
    try:
        note_id, tags, reminder_dt = capture_note(
            conn,
            config,
            provider,
            text,
            encrypt=encrypt,
            passphrase=passphrase,
            reminder_at=reminder_at,
        )
    finally:
        dbmod.close_db(conn)

    console.print(f"[green]✔ Saved[/green] as note #[bold]{note_id}[/bold]")
    if tags:
        console.print(f"[yellow]Tags:[/yellow] {tags}")
    if reminder_dt:
        console.print(f"[cyan]⏰ Reminder set for[/cyan] {reminder_dt}")
        _warn_notifier_if_inactive(config)
    if encrypt:
        console.print("[cyan]🔒 Encrypted note.[/cyan]")
    return 0


def cmd_install_notifier() -> int:
    return systemd_install.install_notifier()


def cmd_uninstall_notifier() -> int:
    return systemd_install.uninstall_notifier()


def cmd_remind(rest: list[str]) -> int:
    question = " ".join(rest).strip()
    if not question:
        console.print("[red]Missing query.[/red]")
        return 1
    config = _config()
    provider = _provider(config)
    _warn_notifier_if_inactive(config)
    conn = dbmod.open_db()
    try:
        rows, answer = query_memory(conn, provider, question)
    finally:
        dbmod.close_db(conn)

    if answer:
        console.print(f"\n[green]{answer}[/green]")
        if rows:
            refs = ", ".join(f"#{n.id}" for n in rows)
            console.print(f"[dim]↳ from {refs}[/dim]\n")
    elif rows:
        console.print("[yellow]AI unavailable; showing matches:[/yellow]")
        for note in rows:
            _print_note_row(note)
    else:
        console.print("No relevant info found.")
    return 0


def cmd_search(rest: list[str]) -> int:
    query = " ".join(rest).strip()
    if not query:
        console.print("[red]Missing search query.[/red]")
        return 1
    conn = dbmod.open_db()
    try:
        rows = search_memory(conn, query)
    finally:
        dbmod.close_db(conn)
    if not rows:
        console.print("No matches.")
        return 0
    for note in rows:
        _print_note_row(note)
    return 0


def cmd_list(rest: list[str]) -> int:
    limit = 50
    if rest and rest[0].isdigit():
        limit = int(rest[0])
    conn = dbmod.open_db()
    try:
        rows = dbmod.list_notes(conn, limit)
    finally:
        dbmod.close_db(conn)
    if not rows:
        console.print("No notes yet.")
        return 0
    for note in rows:
        _print_note_row(note)
    return 0


def cmd_delete(rest: list[str]) -> int:
    if not rest:
        console.print("[red]Provide a note id to delete.[/red]")
        return 1
    target = " ".join(rest).strip()
    if target.isdigit():
        note_id = int(target)
    else:
        console.print(
            "[yellow]Delete by id. Search first to find the id:[/yellow] "
            "better-dontforget search <query>"
        )
        return 1
    conn = dbmod.open_db()
    try:
        ok = dbmod.delete_note(conn, note_id)
    finally:
        dbmod.close_db(conn)
    if ok:
        console.print(f"[green]Deleted note #{note_id}.[/green]")
    else:
        console.print(f"[red]No note with id #{note_id}.[/red]")
        return 1
    return 0


def cmd_config(rest: list[str]) -> int:
    if not rest or rest[0] in ("list", "show"):
        return _config_show()
    action = rest[0]
    if action == "set":
        if len(rest) < 3:
            console.print("[red]Usage: config set <key> <value>[/red]")
            return 1
        key, value = rest[1], " ".join(rest[2:])
        config = _config()
        try:
            config.set(key, value)
        except (KeyError, ValueError) as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
        config.save()
        console.print(f"[green]Set {key}.[/green]")
        return 0
    if action == "reset":
        if len(rest) < 2:
            console.print("[red]Usage: config reset <key>[/red]")
            return 1
        key = rest[1]
        config = _config()
        try:
            config.reset(key)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
        config.save()
        console.print(f"[green]Reset {key} to default.[/green]")
        return 0
    console.print("[red]Unknown config action.[/red]")
    return 1


def _config_show() -> int:
    config = _config()
    table = Table(title="Better Dontforget configuration")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("provider", config.provider)
    table.add_row("model", config.effective_model())
    table.add_row("api_key", describe_secret(config))
    table.add_row("base_url", config.resolved_base_url() or "(default)")
    table.add_row("notifications_enabled", str(config.notifications_enabled))
    table.add_row("dark", str(config.dark))
    table.add_row("config_file", str(config_path()))
    console.print(table)
    console.print(
        "\n[dim]Secrets are never printed. Set credentials with "
        "`config set api_key <key>` or the environment "
        "(GEMINI_API_KEY / OPENAI_API_KEY).[/dim]"
    )
    return 0


def cmd_notify_pending() -> int:
    from .core.notifications import NotifySendNotifier, NullNotifier
    from .core.reminders import process_pending

    config = _config()
    notifier = NotifySendNotifier() if config.notifications_enabled else NullNotifier()
    conn = dbmod.open_db()
    try:
        delivered = process_pending(conn, notifier)
    finally:
        dbmod.close_db(conn)
    if delivered:
        console.print(f"[green]Delivered {len(delivered)} reminder(s).[/green]")
    else:
        console.print("No pending reminders.")
    return 0


def cmd_models() -> int:
    from .core.providers import ProviderError, list_models

    config = _config()
    provider = _provider(config)
    try:
        models = list_models(provider)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    if not models:
        console.print("No models returned by the provider.")
        return 0
    current = config.effective_model()
    for mid in models:
        marker = " [cyan](current)[/cyan]" if mid == current else ""
        console.print(f"  {mid}{marker}")
    console.print("\n[dim]Select one with: better-dontforget config set model <id>[/dim]")
    return 0


def _print_help(prog: str = "better-dontforget") -> None:
    console.print(
        f"""[bold]Better Dontforget[/bold] — quick personal memory dumps

[green]{prog} "anything"[/green]            capture a quick note
[green]{prog} "text" --encrypt[/green]      capture an encrypted note
[green]{prog} "text" --remind "tomorrow 9am"[/green]  attach a reminder
[green]{prog} remind "question"[/green]     AI-assisted recall
[green]{prog} search "query"[/green]        full-text search
[green]{prog} list[/green]                  list recent notes
[green]{prog} delete <id>[/green]           delete a note
[green]{prog} config show|set|reset[/green] manage configuration
[green]{prog} models[/green]              list models for the current provider
[green]{prog} notify-pending[/green]        deliver due reminders
[green]{prog} install-notifier[/green]      install + enable the systemd reminder timer
[green]{prog} uninstall-notifier[/green]    remove the systemd reminder timer
[green]{prog} tui[/green]                   launch the TUI

Run with no arguments to open the TUI.
"""
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    prog = Path(sys.argv[0]).name

    # Color control: explicit --color / --no-color flags, else the standard
    # NO_COLOR env var disables color. Without either, colors are automatic.
    force_color: bool | None = None
    if "--no-color" in argv:
        force_color = False
        argv.remove("--no-color")
    if "--color" in argv:
        force_color = True
        argv.remove("--color")
    if force_color is None and os.environ.get("NO_COLOR") is not None:
        force_color = False
    if force_color is True:
        globals()["console"] = Console(force_terminal=True)
    elif force_color is False:
        globals()["console"] = Console(no_color=True)

    if not argv:
        return _launch_tui()
    cmd = argv[0]
    if cmd in ("-h", "--help", "help"):
        _print_help(prog)
        return 0
    if cmd in ("-v", "--version", "version"):
        from . import __version__

        console.print(f"{prog} {__version__}")
        return 0
    if cmd in KNOWN_SUBCOMMANDS:
        rest = argv[1:]
        if cmd == "tui":
            return _launch_tui()
        if cmd in ("remind", "ask", "q"):
            return cmd_remind(rest)
        if cmd in ("search", "find"):
            return cmd_search(rest)
        if cmd in ("list", "ls"):
            return cmd_list(rest)
        if cmd in ("delete", "del", "rm"):
            return cmd_delete(rest)
        if cmd == "config":
            return cmd_config(rest)
        if cmd == "models":
            return cmd_models()
        if cmd in ("notify-pending", "notify"):
            return cmd_notify_pending()
        if cmd in ("install-notifier", "uninstall-notifier"):
            if cmd == "install-notifier":
                return cmd_install_notifier()
            return cmd_uninstall_notifier()
    # Not a known subcommand -> treat as capture text.
    return cmd_capture(argv)


def _launch_tui() -> int:
    from .tui.app import BetterDontforgetApp

    app = BetterDontforgetApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
