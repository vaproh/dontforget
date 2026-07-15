# AGENTS.md — Engineering Operating Manual

This file is the operating manual for autonomous coding agents working on
**Better Dontforget** (`better-dontforget`). Follow it precisely.

## Read first

Before editing anything, read in order:

1. `PRD.md` — product requirements and scope (source of truth for *what*).
2. `ROADMAP.md` — implementation progress and dependency order.
3. `docs/docs.md` and `docs/config.md` — documented user behavior.
4. The relevant source under `better_dontforget/` — inspect before changing.

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
