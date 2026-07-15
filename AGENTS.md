# AGENTS.md — Engineering Operating Manual

This file is the operating manual for autonomous coding agents working on
**Better Dontforget** (`better-dontforget`). Follow it precisely.

## Read first

Before editing anything, read in order:

1. `PRD.md` — product requirements and scope (source of truth for *what*).
2. `ROADMAP.md` — implementation progress and dependency order.
3. `docs/docs.md` and `docs/config.md` — documented user behavior.
4. The relevant source under `better_dontforget/` — inspect before changing.

## Repository layout (how to navigate)

```
better_dontforget/        # the importable package — all shipped code
  __init__.py             # __version__
  cli.py                  # dispatch: subcommands + bare-positional capture
  core/                   # provider-agnostic logic (no UI); unit-testable
    paths.py              # XDG config/data directory resolution
    config.py             # TOML load/save; `config` subcommand logic; secret masking
    db.py                 # SQLite + FTS5 schema, migration, CRUD, search, due queries
    models.py             # Note dataclass
    providers.py          # AIProvider base + GeminiProvider / OpenAICompatProvider
    ai.py                 # keyword extraction + answer synthesis (tagging removed in 1.1.0)
    crypto.py             # Fernet + PBKDF2 per-note encryption
    reminder_parser.py    # deterministic natural-language time parsing
    reminders.py          # due/overdue detection; mark-notified
    notifications.py      # Notifier abstraction + NotifySendNotifier (libnotify)
    systemd_install.py    # (1.1.0) install/uninstall/status of the notifier
  tui/app.py              # Textual TUI — thin; delegates to core/
tests/                    # pytest suite (fake providers/notifiers, temp XDG dirs)
docs/                     # docs.md (usage), config.md (configuration)
legacy/                   # upstream FastAPI server + bash client (attribution only)
packaging/                # systemd unit templates (moved into the package in 1.1.0)
.github/workflows/        # ci.yml (just check), publish.yml (PyPI trusted publishing)
Justfile                  # developer workflow (see "Built-in tools" below)
pyproject.toml            # hatchling build, deps, console scripts (better-dontforget, bdf)
CHANGELOG.md              # versioned change log
```

Rule of thumb: **UI code lives in `cli.py` / `tui/`; everything else lives in
`core/`.** Keep behavior in `core/` so it can be tested without a display or
network. Tests inject a fake `AIProvider` and a fake `Notifier`.

## Built-in tools

### CLI (`better-dontforget`, alias `bdf`)

| Invocation | Purpose |
| --- | --- |
| `bdf "text"` | Capture a quick note (opens `$EDITOR` if no text given). |
| `bdf --encrypt [--passphrase X] "text"` | Capture an encrypted note. |
| `bdf --remind "<spec>" "text"` | Capture with a reminder (`--remind=tomorrow 9am`). |
| `bdf --color` / `bdf --no-color` | Force / disable ANSI color (`NO_COLOR` env also works). |
| `bdf remind\|ask\|q "question"` | AI-assisted recall over memories. |
| `bdf search\|find "query"` | Full-text search (no AI). |
| `bdf list\|ls [n]` | List recent notes (default 50). |
| `bdf delete\|del\|rm <id>` | Delete a note by id. |
| `bdf config show\|set\|reset <key> [val]` | Manage configuration (secrets masked). |
| `bdf models` | List models for the current provider. |
| `bdf notify-pending\|notify` | Deliver due reminders now (one-shot). |
| `bdf install-notifier` / `bdf uninstall-notifier` | Install / remove the systemd user timer **(1.1.0)**. |
| `bdf tui` | Launch the TUI (also the default when run with no args). |
| `bdf version` / `bdf help` | Print version / usage. |

When a `remind` runs (or a note is captured with `--remind`) and the notifier is
not active, `bdf` prints a hint to run `bdf install-notifier` (or to start the
timer) so reminders are never silently lost.

### `just` recipes

| Recipe | What it runs |
| --- | --- |
| `just install` | `uv sync` |
| `just build` | `uv build` (wheel + sdist) |
| `just run ARGS...` | `uv run better-dontforget ARGS` |
| `just fmt` | `uv run ruff format .` |
| `just lint` | `uv run ruff check .` |
| `just type` | `uv run mypy better_dontforget` |
| `just test` | `uv run pytest` |
| `just check` | **Canonical gate:** fmt-check + lint + type + test + build |
| `just install-notifier` | **(1.1.0)** `uv run better-dontforget install-notifier` |

### Notifications (Linux)

`notify-pending` is driven by a systemd **user** timer (`better-dontforget-notify.timer`)
that runs a few minutes after boot and then every few minutes (`Persistent=true`
catches runs missed while the machine was off). It is installed with a single
command: `bdf install-notifier`. The unit templates currently live in `packaging/`
and are bundled into the package as `better_dontforget/systemd_units/` in 1.1.0.

## Golden rules

* Preserve upstream behavior unless intentionally changing it (document why).
* Prefer the smallest coherent change: **extend → refactor → replace (justified)**.
* Avoid speculative abstractions and unnecessary dependencies.
* Keep reminders **optional** and encryption **optional + explicit**.
* Respect XDG conventions; never dump files into `$HOME` directly.
* Never turn the project into a calendar, task manager, or full notes app.
* Never silently expand scope beyond `PRD.md`.

## Workflow

1. Inspect relevant code before editing.
2. Implement the smallest coherent solution for the milestone in `ROADMAP.md`.
3. Add/update tests for behavioral changes.
4. Update affected docs alongside behavior changes.
5. Run focused tests during development.
6. Before declaring done: run the canonical quality gate.

## Quality gate

The single canonical full-project verification command is:

```text
just check
```

`just check` runs formatting verification, linting, static analysis, the test
suite, and build verification. Never claim completion while `just check` fails.

## Testing discipline

* Tests must not require real API keys, paid services, network, or a graphical
  desktop notification server.
* Mock external AI providers (inject a fake `AIProvider`).
* Mock/abstract the notifier (`Notifier`) for notification tests.
* Use temp XDG dirs and temp DB files in tests.
* Do not overmock pure internal logic into meaningless tests.
* Cover: capture, provider selection, provider failure, malformed responses,
  config persistence, XDG env + fallback, reminder persistence, due/overdue
  detection, duplicate prevention, notification success/failure state,
  encryption round-trip, wrong-passphrase, CLI behavior, migration.

## Reliability invariants (must hold)

1. A quick note is never silently lost.
2. AI failure does not destroy user input.
3. A normal note needs no reminder.
4. A normal note needs no encryption.
5. Encryption only when explicitly requested.
6. Reminder state persists across exits/restarts.
7. A reminder missed while the machine is off stays pending.
8. A notification counts as delivered only after delivery succeeds.
9. Delivered reminders are not re-notified without cause.
10. Config persists in an XDG-compliant location.
11. User data is not silently discarded during migration.
12. API keys never appear in ordinary displayed config output.
13. Tests never depend on external paid services.
14. The project stays a focused improvement of `dontforget`.

## Compatibility / secrets

* Preserve upstream `memory.db` via migration; never silently destroy data.
* Document intentional compatibility breaks in `ROADMAP.md` and PRD.
* Never print secrets; `config show` masks keys as `configured`.
* Never send encrypted note content to external AI.

## ROADMAP maintenance

Keep `ROADMAP.md` updated continuously. A task is complete only when
implementation exists, tests pass, docs are updated, and no known regression
remains in scope. Use status markers: `[ ]` not started, `[~]` in progress,
`[x]` complete, `[!]` blocked.

## Justfile workflow

Use `just` recipes: `just build`, `just run`, `just fmt`, `just lint`,
`just test`, `just check`. See `Justfile` for details.
