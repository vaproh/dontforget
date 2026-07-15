# ROADMAP — Better Dontforget

Status: `[ ]` not started · `[~]` in progress · `[x]` complete · `[!]` blocked

This roadmap reflects actual repository findings: upstream is a FastAPI
server + bash curl client (Gemini-only, FTS5 SQLite, no TUI/reminders/
encryption/XDG). Better Dontforget becomes a self-contained CLI+TUI app (see
PRD for the justified architecture change).

## Phase 0: Repository archaeology  [x]
- Inspected `main.py`, `mem-cli`, `pyproject.toml`, `README.md`, `.gitignore`.
- Findings: server/client model; `memory.db` + FTS5; Gemini tagging/synthesis;
  capture loses input on AI failure; no TUI/reminders/encryption/XDG.
- Acceptance: contract docs created from real findings.

## Phase 1: Project contract & docs  [x]
- [x] `PRD.md`, `AGENTS.md` created.
- [x] `ROADMAP.md`, `Justfile` created.
- [x] `docs/docs.md`, `docs/config.md` created.

## Phase 2: XDG paths & configuration foundation  [x]
- Goal: XDG-compliant paths + TOML config with CLI management.
- Tasks:
  - [x] `core/paths.py` — XDG config/data dirs with env + fallback.
  - [x] `core/config.py` — load/save TOML; `config show|set|reset`; secret masking.
  - [x] `cli.py` — `config` subcommand.
- Tests: XDG env handling, fallback paths, config persistence, secret masking.
- Acceptance: config lives in XDG; no manual editing required; `just check` green.

## Phase 3: Storage + multi-provider AI  [x]
- Goal: preserve FTS5 storage with migration; provider abstraction.
- Tasks:
  - [x] `core/db.py` — schema/migration; CRUD; FTS search; due-reminder queries.
  - [x] `core/models.py` — Note model.
  - [x] `core/providers.py` — `AIProvider` base, `GeminiProvider`, `OpenAICompatProvider`.
  - [x] `core/ai.py` — tagging, keyword extraction, synthesis, provider selection.
  - [x] Migration of legacy `./memory.db` into XDG data dir.
- Tests: provider selection, failure handling, malformed JSON, migration, FTS search.
- Acceptance: capture/search work with Gemini and OpenAI-compatible; no real keys.

## Phase 4: Optional per-note encryption  [x]
- Goal: explicit, authenticated per-note encryption.
- Tasks:
  - [x] `core/crypto.py` — Fernet + PBKDF2; encrypt/decrypt; fail-closed.
  - [x] Integrate `--encrypt` in capture; TUI encrypted-note create/unlock.
  - [x] Ensure encrypted content not sent to AI.
- Tests: round-trip, wrong passphrase, persistence, no-plaintext-leak.
- Acceptance: encryption optional + explicit; tests pass.

## Phase 5: Optional reminders + notifications  [x]
- Goal: reminders persisted; desktop notifications on due.
- Tasks:
  - [x] `core/reminder_parser.py` — deterministic NL time parsing.
  - [x] `core/reminders.py` — due/overdue detection; mark notified.
  - [x] `core/notifications.py` — `Notifier` abstraction; `notify-send` backend.
  - [x] `cli.py` — `notify-pending` one-shot; CLI wiring.
  - [x] `packaging/` — systemd user service + timer.
- Tests: persistence, due/overdue, duplicate prevention, success/failure state,
  missed-reminder recovery.
- Acceptance: notifications reliable across exits/restarts; no duplicates.

## Phase 6: Improved TUI  [x]
- Goal: keyboard-driven TUI over the core logic.
- Tasks:
  - [x] `tui/app.py` — list/add/edit/delete/search; reminder attach/remove;
        encrypted create/unlock; settings.
  - [x] Keep TUI thin; all logic in `core/` (testable without display).
- Tests: core-driven TUI smoke test (run_test).
- Acceptance: TUI covers required operations; handles resize/errors.

## Phase 7: Documentation & hardening  [x]
- [x] `docs/docs.md`, `docs/config.md` accurate to implementation.
- [x] `README.md` updated to Better Dontforget.
- [x] Packaging/systemd docs; troubleshooting.

## Phase 8: Final PRD audit + quality gate  [x]
- [x] Audit every PRD requirement (implemented/tested or deferred w/ reason).
- [x] Scope audit (not a calendar/task-manager/notes-app).
- [x] `just check` passes (fmt, lint, mypy, 55 tests, build).

## Dependency order
Phase 2 (paths/config) → Phase 3 (db/ai) → Phase 4 (crypto) and Phase 5
(reminders/notifications) can proceed after Phase 3 → Phase 6 (TUI) after 2–5 →
Phase 7 docs → Phase 8 audit.

## Phase 9: TUI polish & CLI color control  [x]
- [x] TUI: live preview pane for the highlighted note (full text, tags, reminder).
- [x] TUI: edit existing notes (`e`) for plaintext + encrypted (unlock → re-encrypt).
- [x] TUI: dark/light theme toggle (`t`) persisted via `config dark`.
- [x] TUI: keyboard nav — table focused on launch, `/` focuses search, refocus
      after search so single-key bindings work (fixes search box stealing focus).
- [x] CLI: `--color` / `--no-color` flags + `NO_COLOR` env support; `config show`
      and `help` reflect the invoked alias (`bdf` vs `better-dontforget`).
- [x] Tests: config `dark`, CLI color flag, TUI edit/theme/preview.
- [x] `just check` green (64 tests).

## Phase 10: Notifier installer, remind status check, drop auto-tagging  [~]
- Target release: **v1.1.0** (bundles Phase 9 polish + this phase; unreleased).
- Goal: make the notifier trivially installable; warn when reminders cannot fire;
  remove low-value automatic AI tagging while preserving the schema column.
- Tasks:
  - [x] `core/systemd_install.py` — `install_notifier()` / `uninstall_notifier()` /
       `notifier_status()`. Bundle unit templates as package data under
       `better_dontforget/systemd_units/` (moved from `packaging/`).
  - [x] `cli.py` — `install-notifier` / `uninstall-notifier` subcommands; auto-detect
       the real `better-dontforget`/`bdf` binary path; degrade gracefully when
       `systemctl` is absent (write units + print manual steps).
  - [x] `cli.py` — `remind`/`ask`/`q` (and capture with `--remind`) call
       `notifier_status()` and print an install/enable hint when the notifier is
       not active.
  - [x] Drop automatic tagging: stop calling `ai.generate_tags` on capture; remove
       `_TAG_PROMPT` / `generate_tags`; strip tags from CLI/TUI output. Keep the
       `ai_tags` DB column (no migration needed).
  - [x] `Justfile` — `install-notifier` recipe wrapping `uv run better-dontforget
       install-notifier`.
  - [x] Docs: replace manual `cp` systemd steps with `bdf install-notifier`;
       document the remind status hint; document dropped tagging.
  - [x] Tests: `notifier_status` states (running/installed_inactive/not_installed/
       unsupported); `write_units` placeholder rewrite; `remind` + capture print the
       install hint when inactive.
- Acceptance: `bdf install-notifier` installs + enables the timer; `remind` warns
  when inactive; tagging no longer generated; `just check` green.

## Release lineage
- **v1.0.0** — first public release: CLI+TUI, multi-provider AI, optional reminders
  + notifications, optional encryption, XDG config. (Phase 0–8.)
- **v1.1.0** (planned) — TUI polish + color control (Phase 9) **and** notifier
  installer command, remind status check, and dropped auto-tagging (Phase 10).

