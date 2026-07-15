# Better Dontforget — User Documentation

Better Dontforget is a focused improvement of the upstream `dontforget` project.
It is an AI-assisted terminal tool for quickly capturing and retrieving small
personal memory dumps, with a better TUI, configurable AI providers, optional
reminders with desktop notifications, optional per-note encryption, XDG-compliant
storage, and CLI/TUI-based configuration.

> **Scope:** This is a quick personal memory-dump tool. Reminders are optional and
> attached to a note. Encryption is optional and explicit per note. It is **not**
> a calendar, task manager, or full notes application.

## Relationship to upstream

Upstream `dontforget` was a FastAPI server plus a bash `curl` client, Gemini-only,
with no TUI, reminders, encryption, or XDG storage. Better Dontforget keeps the
useful parts — the SQLite + FTS5 storage engine (with migration of existing data)
and the AI-assisted tagging/retrieval workflow — but is a **self-contained CLI +
TUI application** so that capture works offline, notifications can fire while the
app is closed, and no server must be running. The legacy server/client is kept
under `legacy/` for attribution only.

## Installation

Requires Python 3.11+. Use `uv`:

```bash
uv sync                 # install dependencies into a local environment
uv run better-dontforget --version
```

Or install the console script:

```bash
uv tool install .       # makes `better-dontforget` available on your PATH
```

Configure an AI provider (see `docs/config.md`) before relying on AI features.
Capture and local search work without any provider configured.

## Quick start

The command is also available under the short alias **`bdf`**:

```bash
bdf "ratatui was that rust tui library"
bdf "John recommended Severance"
bdf "remind me tomorrow 9am to check that library"
bdf search "rust tui"
bdf remind "what rust tui library was recommended?"
bdf list
bdf tui
```

You can also use the full command name:

```bash
better-dontforget "ratatui was that rust tui library"
better-dontforget "John recommended Severance"
better-dontforget "remind me tomorrow 9am to check that library"
better-dontforget search "rust tui"
better-dontforget remind "what rust tui library was recommended?"
better-dontforget list
better-dontforget tui
```

## Quick capture

The lowest-friction operation is a bare positional argument:

```bash
better-dontforget "wifi password is written behind the router"
```

* Capture is local and synchronous — no AI call is made on capture.
* Your input is never lost; the note is saved even if no provider is configured.
* Run `better-dontforget` with no arguments to open the **TUI**.
* If you pass no text, your `$EDITOR` (default `vim`) opens for a longer note.

Optional flags:

```bash
better-dontforget --encrypt "private thing I want to remember"
better-dontforget --remind "tomorrow 9am" "check the library"
better-dontforget --encrypt --passphrase "hunter2" "secret backup code"
```

Color control (global):

```bash
better-dontforget --no-color "note text"   # disable ANSI colors
better-dontforget --color "note text"      # force colors (e.g. when piped)
```

Without either flag, colors are automatic (on a TTY). The standard `NO_COLOR`
environment variable also disables color.

Encrypted notes are **never** sent to an external AI provider.

## Command reference

For the authoritative, always-up-to-date list of options and subcommands, run:

```bash
bdf --help
```

It prints a structured screen with `USAGE`, an `OPTIONS` block (flags like
`--encrypt`, `--remind`, `--color`/`--no-color`, `--passphrase`, `-v/--version`),
and a `COMMANDS` block listing every subcommand together with its aliases
(`remind`/`ask`/`q`, `search`/`find`, `list`/`ls`, `delete`/`del`/`rm`, …).

## Viewing & searching notes

```bash
better-dontforget list            # recent notes (optionally `list 20`)
better-dontforget search "query"  # full-text search (no AI)
better-dontforget remind "question"  # AI-assisted recall over your memories
```

`remind` asks the AI to extract keywords, runs a full-text search, and
synthesizes an answer. If AI is unavailable it falls back to listing raw matches.

## TUI usage

Launch with `better-dontforget tui` (or with no arguments). The main screen shows
your notes in a table on the left and a live preview of the highlighted note on
the right.

| Key | Action |
| --- | --- |
| `a` | Add a note |
| `x` | Add an **encrypted** note |
| `e` | **Edit** the selected note (text, reminder) |
| `/` | Focus the search box (type, then Enter to filter; press a list key to return) |
| `enter` | View / unlock a note (detail screen) |
| `d` | Delete the selected note |
| `r` | Set or change the selected note's reminder |
| `s` | Open Settings |
| `t` | Toggle dark / light theme |
| `q` | Quit |

The detail screen lets you unlock an encrypted note (enter passphrase), **edit** it,
set/clear a reminder, and delete the note. The settings screen lets you choose the
AI provider, model, base URL, API key, toggle desktop notifications, and switch the
theme — all stored in your XDG config (no manual file editing required). The theme
preference (`dark`) can also be set from the CLI with
`better-dontforget config set dark false`.

## AI behavior & providers

On capture, **no AI call is made** — notes are saved locally as-is (automatic
tagging was removed because it added little value and search/recall use the raw
text, not tags). On `remind`, the provider extracts keywords and synthesizes an
answer from retrieved memories.

Supported providers (set with `config set provider <name>`):

* `gemini` (default) — Google Gemini. Needs `GEMINI_API_KEY` or `config set api_key`.
* `openai` — OpenAI-compatible APIs (OpenAI, OpenRouter, self-hosted). Needs
  `OPENAI_API_KEY` or `config set api_key`. Use `config set base_url <url>` for
  OpenRouter (`https://openrouter.ai/api/v1`) or a custom endpoint.
* `groq` — Groq's OpenAI-compatible API (fast open-weight models). Needs
  `GROQ_API_KEY` or `config set api_key`. `base_url` is set automatically to
  `https://api.groq.com/openai/v1`.

Only the content needed for the requested operation is sent to the provider.
Encrypted note content is never sent.

## Optional reminders

A reminder is an optional timestamp on a note. Add one with `--remind "<spec>"`
or natural-language intent ("remind me tomorrow to …"), or in the TUI with `r`.
A normal note never requires a reminder.

Natural-language time specs understood (deterministic, offline):

```text
tomorrow 9am
in 2 hours
in 3 days
next monday
today 18:00
2026-08-01 15:30
tonight / morning / evening / afternoon
```

## Desktop notifications

When a reminder becomes due, Better Dontforget sends a local desktop notification
via `notify-send` (libnotify) — the standard Linux desktop-notification mechanism.
A notification is marked delivered only after it is successfully sent, so a
reminder missed while the machine was off stays pending and is delivered the next
time notification processing runs.

## Missed reminders & restarts

Notification processing is a one-shot command:

```bash
better-dontforget notify-pending
```

It opens the database, finds reminders that are due and not yet delivered, sends
them, and marks successful deliveries. It works while the interactive CLI/TUI is
closed and after a restart. All due unnotified reminders are notified; there is no
recurrence, so volume is naturally bounded and there are no notification storms.

### systemd user integration (Linux)

Install the notifier with a single command — it copies the unit files, detects
your installed `better-dontforget`/`bdf` binary, and enables the timer:

```bash
bdf install-notifier       # install + enable the systemd user timer
```

`remind` (and capturing a note with `--remind`) will print a hint to run
`bdf install-notifier` when the notifier isn't active, and a hint to start the
timer when it's installed but not running — so you never silently lose a reminder.

To remove it:

```bash
bdf uninstall-notifier
```

<details>
<summary>Manual install (advanced)</summary>

If you prefer to set it up by hand, the unit templates are bundled inside the
installed package. Locate and copy them, then enable the timer:

```bash
UNIT_DIR=$(python -c "import better_dontforget,os;print(os.path.join(os.path.dirname(better_dontforget.__file__),'systemd_units'))")
mkdir -p ~/.config/systemd/user
cp "$UNIT_DIR/better-dontforget-notify.service" ~/.config/systemd/user/
cp "$UNIT_DIR/better-dontforget-notify.timer"    ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now better-dontforget-notify.timer
```

</details>

Useful commands:

```bash
systemctl --user status better-dontforget-notify.timer
systemctl --user cat better-dontforget-notify.service
systemctl --user disable --now better-dontforget-notify.timer   # disable
```

The timer runs `notify-pending` shortly after boot and every few minutes, and
`Persistent=true` ensures runs missed during shutdown are caught on the next boot.

## Optional encryption

```bash
better-dontforget --encrypt "my secret"
```

* Uses authenticated encryption (Fernet) with a key derived from your passphrase
  via PBKDF2-HMAC-SHA256 (`cryptography` library). No custom crypto.
* The passphrase is prompted at runtime and never stored.
* Plaintext is never persisted; only the salt + ciphertext token is stored.
* Wrong passphrase fails closed (decryption error; no leak).
* Decrypt in the TUI detail screen with the passphrase.

## Common errors & troubleshooting

* **"No AI provider is configured"** — capture and search still work. Set an API
  key to enable tagging/recall, or ignore the message.
* **`remind` returns "No relevant info found"** — recall searches your literal
  question words plus AI-extracted keywords over the raw text; try rephrasing or
  check with `search`.
* **No notification appears** — `notify-send` (libnotify) must be installed and a
  desktop session active. Run `better-dontforget notify-pending` manually to test.
* **Reminder not delivered** — if no notification backend is available, the
  reminder stays pending (by design) and is retried later.
* **Old `memory.db` not showing** — it is migrated into the XDG data directory on
  first run; your existing data is preserved.

## Limitations / non-goals

* Linux-first. Desktop notifications and systemd integration are Linux-specific
  (libnotify / systemd user units). Core logic is portable.
* No calendar, task manager, recurrence engine, vector search, cloud sync, or
  collaboration features (intentionally).
* Encryption is per-note and passphrase-based; there is no key-management platform.
