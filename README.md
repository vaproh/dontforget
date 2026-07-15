# 🧠 Better Dontforget

> 🍴 **A fork of [`bugswriter/dontforget`](https://github.com/bugswriter/dontforget).**

**Better Dontforget** is a focused improvement of the upstream `dontforget`
project: an AI-assisted terminal tool for quickly capturing and retrieving small
personal memory dumps, enhanced with a better TUI, configurable AI providers,
optional reminders with persistent desktop notifications, optional per-note
encryption, XDG-compliant storage, and CLI/TUI-based configuration.

> It is a quick personal memory-dump tool. Reminders and encryption are optional
> and per-note. It is **not** a calendar, task manager, or full notes application.

## 📦 Install

From [PyPI](https://pypi.org/project/better-dontforget/):

```bash
pip install better-dontforget
better-dontforget config set provider gemini
better-dontforget config set api_key "$GEMINI_API_KEY"
```

Or, for development from source:

```bash
uv sync
better-dontforget "anything"
```

## ✨ Features

* **⚡ Zero-friction capture:** `better-dontforget "anything"`. Works offline; AI
  tagging is best-effort and never loses your input.
* **🔍 Search & AI recall:** full-text search (`search`) and AI-assisted answers
  (`remind`) over your memories (SQLite + FTS5).
* **🤖 Multiple AI providers:** Gemini (default) and OpenAI-compatible
  (OpenAI, OpenRouter, self-hosted), behind a small provider abstraction.
* **🖥️ Improved TUI:** view/add/edit/delete/search, reminders, encryption, and
  settings — all keyboard-driven.
* **⏰ Optional reminders:** attach a due time to a note via `--remind` or natural
  language ("remind me tomorrow to …").
* **🔔 Desktop notifications:** due reminders notify via `notify-send` (libnotify),
  with a one-shot `notify-pending` command and optional systemd user timer that
  survives restarts.
* **🔐 Optional per-note encryption:** authenticated (Fernet + PBKDF2), passphrase
  based, explicit per note; encrypted content is never sent to AI.
* **📁 XDG-compliant storage** and **CLI/TUI configuration** (no manual file editing).

## 🚀 Quick start

```bash
uv sync
better-dontforget config set provider gemini
better-dontforget config set api_key "$GEMINI_API_KEY"

better-dontforget "ratatui was that rust tui library"
better-dontforget "remind me tomorrow 9am to check that library"
better-dontforget search "rust tui"
better-dontforget tui
```

The short alias **`bdf`** is also installed (`bdf "ratatui was that rust tui library"`, `bdf search "rust tui"`, …).

See [`docs/docs.md`](docs/docs.md) for full usage and
[`docs/config.md`](docs/config.md) for configuration.

## 🛠️ Development

```bash
just install     # uv sync
just check       # format + lint + type + tests + build (canonical gate)
just test
just lint
just fmt
just type
```

## 📄 License

GPL-3. Upstream `dontforget` by Suraj Kushwah; legacy server/client retained under
`legacy/` for attribution.

## 🙏 Credits

Better Dontforget is a fork of [`bugswriter/dontforget`](https://github.com/bugswriter/dontforget)
by **Suraj Kushwah**. The original SQLite + FTS5 storage engine and AI-assisted
capture/recall concept are carried over and extended; the legacy FastAPI
server and bash `curl` client are preserved under `legacy/` for reference.

