# PRD — Better Dontforget

## Project name

**Better Dontforget** (repository: `better-dontforget`)

## Project summary

Better Dontforget is a focused improvement of the upstream `bugswriter/dontforget`
(author Suraj Kushwah) project. It is an AI-assisted terminal tool for quickly
capturing and retrieving small personal memory dumps, enhanced with a better TUI,
configurable AI providers, optional reminders with persistent desktop
notifications, optional per-note encryption, XDG-compliant storage, and
CLI/TUI-based configuration.

## Relationship to upstream `dontforget`

The upstream project is a Python **FastAPI server** (`main.py`) plus a bash
**curl client** (`mem-cli`). It stores raw notes in SQLite with an FTS5 full-text
index, uses Google Gemini to auto-generate search tags on capture and to
synthesize answers on query, and requires a long-running server plus a secret key.

Better Dontforget **preserves**:

* the SQLite + FTS5 storage engine and its data (with backward-compatible migration);
  * the quick-capture workflow (capture is fully local; automatic tagging was
    removed in 1.1.0);
* the AI-assisted retrieval / synthesis workflow;
* the Gemini provider (kept as a first-class provider).

Better Dontforget **changes the runtime shape** with demonstrated justification:
the upstream client/server model forces a running server and makes capture
synchronously dependent on AI (a failed AI call loses the note). The requested
improvements — reliable notifications while the CLI/TUI is closed, an interactive
TUI, per-note encryption, XDG storage, and config without manual file editing —
are a poor fit for a required-running HTTP server driven by a bash `curl` script.
Better Dontforget is therefore a **self-contained CLI + TUI application** that
talks directly to local storage and to AI providers, while keeping the storage
format and useful AI behavior intact. The legacy server/client files are retained
under `legacy/` for reference and attribution; they are not part of the shipped
application.

## Product philosophy

> The primary product is a quick personal memory-dump tool. Reminders are an
> optional capability attached to a note, not the primary abstraction. Encryption
> is also optional and explicitly selected per note. Better Dontforget must not
> evolve into a calendar, task manager, project manager, full notes application,
> knowledge base, or second-brain system.

> The goal is to improve the existing upstream project with the smallest coherent
> changes. A ground-up rewrite is not desired unless repository inspection
> demonstrates that preserving the existing implementation would make the
> requirements substantially harder, less reliable, or less maintainable.

## Target use case

Fast, low-friction capture and later retrieval of small personal facts:

```text
the rust tui library was called ratatui
wifi password is written behind the router
John recommended Severance
remind me tomorrow to check that library
```

## Existing upstream behavior being preserved

* SQLite + FTS5 storage and schema (`memories` + `memories_idx`).
* AI-assisted retrieval / synthesis (capture-time tagging was dropped in 1.1.0).
* AI-assisted query synthesis over retrieved memories.
* The `remember` / `remind` / `delete` conceptual operations.

## Improvements introduced by Better Dontforget

1. Improved TUI.
2. Multiple configurable AI/LLM providers (Gemini + OpenAI-compatible).
3. Optional reminders attached to quick notes.
4. Desktop notifications for due reminders.
5. Reliable background notification processing.
6. Persistent reminders that survive application exits and machine restarts.
7. Optional per-note encryption.
8. XDG-compliant application paths.
9. Configuration through CLI and TUI rather than manual file editing.
10. Better project documentation and agentic development infrastructure.

## v1 requirements

* Self-contained CLI + TUI (no required server).
* Quick capture works without AI; AI failure never loses user input.
* Multiple AI providers behind a small abstraction; OpenAI-compatible covers
  OpenAI and OpenRouter via a configurable base URL.
* Optional reminders persisted per note; due/overdue detection.
* Desktop notifications via the platform mechanism (`notify-send`/libnotify).
* One-shot `notify-pending` command + optional systemd user timer/service for
  reliable processing while the interactive app is closed and after restarts.
* `bdf install-notifier` command that installs and enables the systemd user timer
  automatically (1.1.0); `remind` warns when the notifier is inactive.
* Optional per-note encryption (authenticated, passphrase-derived key).
* XDG-compliant config/data paths.
* CLI `config` subcommand and TUI settings; no manual file editing required.
* Backward-compatible migration of existing upstream `memory.db`.

## Explicit non-goals

* Calendar, task manager, project manager, to-do app, document editor.
* Personal wiki, knowledge graph, second-brain, kanban, Markdown knowledge base.
* Cloud sync, collaboration, user accounts, team features, mobile apps.
* Vector databases, embeddings, semantic-search/RAG pipelines.
* Recurring reminder engines / complex recurrence rules (v1).
* Custom daemons, IPC, RPC, socket servers, or service frameworks.
* Automatic AI tagging (removed in 1.1.0; search/recall use the raw note text).
* Telegram/ntfy/email/SMS/mobile push/webhook notification transports (v1).

## Quick-note behavior

* `better-dontforget "anything"` captures a note instantly.
* Capture is synchronous and fully local — no AI call is made on capture. Your
  input is never lost.
* A normal note never requires a reminder or encryption.
* Optional flags: `--encrypt` (encrypted note), `--remind "<when>"` (attach
  reminder). Encrypted notes are not sent to AI.

## AI behavior

* On capture: no AI is invoked; notes are stored as-is.
* On query (`remind`/`ask`): AI extracts keywords, FTS retrieves candidates, AI
  synthesizes an answer. If AI is unavailable, falls back to raw FTS listing.
* On `search`: direct FTS listing (no AI).
* Only the content needed for the requested operation is sent to the provider.

## Multiple-provider behavior

* Providers: `gemini` (default), `openai` (OpenAI-compatible: OpenAI, OpenRouter),
  `groq` (OpenAI-compatible: Groq).
* Selected via `config set provider <name>`.
* Credentials read from config or environment (`GEMINI_API_KEY`, `OPENAI_API_KEY`).
* `openai` provider supports a configurable `base_url` for OpenRouter/self-hosted.
* Provider calls are mockable; tests never use real keys.

## Optional-reminder behavior

* A reminder is an optional `reminder_at` timestamp on a note.
* Set via `--remind "<spec>"` or from natural-language intent ("remind me
  tomorrow to …") parsed by a deterministic heuristic.
* Ordinary notes remain ordinary notes.
* No calendar semantics, recurrence, or task-completion workflow in v1.

## Desktop-notification behavior

* When a reminder becomes due, a local desktop notification is sent via
  `notify-send` (libnotify), the established Linux mechanism.
* Notification is attempted only for due, not-yet-delivered reminders.
* Marked delivered only after successful delivery; duplicates avoided.

## Persistent missed-reminder behavior

* Reminders are persisted in the database.
* A reminder due while the machine is off cannot notify at that instant.
* On next `notify-pending` run (e.g. after login via systemd timer), due and
  unnotified reminders (including overdue ones) are detected and notified.
* Policy: all due unnotified reminders are notified; no recurrence, so volume is
  naturally bounded. No silent discarding.

## Optional per-note encryption

* Explicit only: `--encrypt` flag or TUI explicit action.
* Uses `cryptography` Fernet (authenticated) with PBKDF2 key derivation from a
  passphrase (prompted at runtime, never stored).
* Encrypted content is not sent to external AI.
* Plaintext is never persisted; decrypted content is never logged.
* Incorrect passphrase fails closed (decryption error surfaced, no leak).

## TUI requirements

* View, add, edit, delete notes; search/filter; inspect reminder state; attach/
  remove reminder; create encrypted note; unlock/decrypt; access settings.
* Keyboard-driven; handles resize and ordinary errors gracefully.
* Not a full notes editor: no analytics, kanban, calendar, nested trees.

## CLI requirements

* `better-dontforget "text"` quick capture; `--encrypt`, `--remind`.
* Subcommands: `remind`/`ask`, `search`, `list`, `delete`, `tui`, `config`,
  `notify-pending`.
* Backward-compatible intent with upstream `mem` (remember/remind/delete).

## Configuration behavior

* Stored as TOML in `$XDG_CONFIG_HOME/better-dontforget/config.toml`.
* Managed via `config show|set|reset` and TUI settings.
* `config show` masks secrets ("API key: configured").
* No manual file editing required.

## XDG requirements

* Config: `$XDG_CONFIG_HOME/better-dontforget/`
* Data (DB): `$XDG_DATA_HOME/better-dontforget/`
* State/cache/runtime only if actually needed (not created speculatively).
* Fallbacks to `~/.config`, `~/.local/share` when base vars unset.
* Existing `./memory.db` is migrated into the XDG data dir on first run.

## Reliability requirements

See "Reliability invariants" in the mission. Key: capture never lost; AI failure
non-fatal; reminder/encryption optional and explicit; notification success gated
on delivery; config + data in XDG; no secret leakage.

## Error-handling expectations

* Missing/invalid credentials: clear message; capture and local search still work.
* AI rate limits/timeouts/malformed responses: degrade gracefully, never lose input.
* Notification failure: leave reminder unnotified, retry next run.
* Wrong encryption passphrase: fail closed.

## Compatibility expectations

* Existing upstream `memory.db` data is preserved via migration.
* Upstream behavior (tags, FTS retrieval) preserved.
* Legacy `mem`/server retained under `legacy/` for attribution only.

## v1.1.0 changes (post-1.0.0)

These changes shipped after the initial 1.0.0 release and are reflected in the
documentation and `ROADMAP.md` Phase 10:

* **Notifier installer:** `bdf install-notifier` / `bdf uninstall-notifier` install
  and enable (or remove) the systemd user timer, auto-detecting the installed
  binary path. Replaces the manual `cp` of unit files.
* **Remind status check:** `remind`/`ask`/`q` (and capturing a note with
  `--remind`) print a hint to install or start the notifier when reminders cannot
  fire.
* **Dropped automatic tagging:** capture no longer calls the AI for tags; the
  `ai_tags` column is retained for backward compatibility but is no longer
  populated. Search and recall always operate on the raw note text.
* **TUI/CLI polish:** live preview pane, in-place note editing, dark/light theme
  toggle (`t`), `--color`/`--no-color` + `NO_COLOR` support, and `help`/`config
  show` reflecting the invoked alias (`bdf` vs `better-dontforget`).

## Acceptance criteria

1. Quick capture works offline and without AI.
2. `just check` passes (fmt, lint, type, tests, build).
3. Multiple providers work; tests mock providers, no real keys.
4. Reminders persist; due + overdue detection works; no duplicate notify.
5. `notify-pending` works while app closed; systemd user unit documented.
6. Per-note encryption round-trips; wrong passphrase fails closed.
7. XDG paths used; config via CLI/TUI; secrets masked.
8. TUI supports required operations.
9. Docs match implementation; scope not expanded.

## Definition of done

All items in the mission's Definition of Done are satisfied: `just check` passes,
PRD/AGENTS/ROADMAP/docs consistent, features implemented and tested, scope
preserved as a focused improvement of `dontforget`.
