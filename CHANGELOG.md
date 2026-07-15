# Changelog — Better Dontforget

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-07-15

Bundles the unreleased TUI/CLI polish (Phase 9) with the notifier installer,
remind status check, and the removal of low-value automatic AI tagging.

### Added
- `bdf install-notifier` / `bdf uninstall-notifier` commands that install the
  systemd user service + timer, auto-detect the installed binary path, and enable
  the timer. No more manual `cp` of unit files.
- A `notifier_status()` check: `remind`/`ask`/`q` (and capturing a note with
  `--remind`) now print a hint to install or start the notifier when reminders
  cannot fire.
- TUI dark/light theme toggle (`t`) persisted via `config dark`.
- CLI `--color` / `--no-color` flags plus `NO_COLOR` env support.
- TUI live preview pane and in-place note editing (`e`), including encrypted notes.

### Changed
- `remind` output streamlined: no separator/score line; shows the answer plus a dim
  `↳ from #id` reference.
- `remind` recall now always searches the literal question words (not only AI
  keywords), so it finds notes even when keyword extraction is weak.

### Removed
- Automatic AI tagging on capture. Tags added little functional value (search and
  recall use the raw text, not tags) and often produced vague labels. Existing
  `ai_tags` data is preserved in the database; the column remains.

### Fixed
- TUI keyboard navigation: the note table is focused on launch and `/` focuses the
  search box, after which single-key bindings work again (search box no longer
  steals focus).
- `help`/`config show` now reflect the invoked program name (`bdf` vs
  `better-dontforget`).

## [1.0.0] - 2026-07-15

First public release.

### Added
- Self-contained CLI + TUI (no required server) for quick personal memory dumps.
- Quick capture `better-dontforget "anything"`; works offline, AI failure never
  loses input.
- Full-text search (`search`) and AI-assisted recall (`remind`/`ask`).
- Multiple AI providers behind a small abstraction: `gemini` (default), `openai`
  (OpenAI-compatible: OpenAI, OpenRouter, self-hosted), `groq`.
- Optional reminders via `--remind "<spec>"` or natural-language intent.
- Desktop notifications via `notify-send` (libnotify) with a one-shot
  `notify-pending` command and optional systemd user timer/service.
- Optional per-note encryption (Fernet + PBKDF2), passphrase-based, never sent to AI.
- XDG-compliant config/data paths; `config show|set|reset` and TUI settings.
- Backward-compatible migration of upstream `memory.db` (SQLite + FTS5).
- `bdf` short alias for the console script.
- PyPI publishing via trusted publishing (`.github/workflows/publish.yml`).

[1.1.0]: https://github.com/vaproh/dontforget/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/vaproh/dontforget/releases/tag/v1.0.0
