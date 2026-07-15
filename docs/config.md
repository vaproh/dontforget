# Better Dontforget — Configuration

Configuration is a product workflow, not a file you must hand-edit. Settings live
as TOML in your XDG config directory and are managed through the CLI `config`
subcommand or the TUI settings screen.

## Configuration philosophy

* You should never need to manually create or edit `config.toml`.
* Defaults are sensible; the app works (capture + local search) with no config.
* Secrets are entered via `config set api_key` or environment variables, and are
  **never printed** in plaintext by `config show`.
* Storage and config follow XDG Base Directory conventions.

## XDG storage locations

| Purpose | Variable | Default path |
| --- | --- | --- |
| Config (`config.toml`) | `XDG_CONFIG_HOME` | `~/.config/better-dontforget/` |
| Data (`better-dontforget.db`) | `XDG_DATA_HOME` | `~/.local/share/better-dontforget/` |

If the base variables are unset, the fallbacks above are used. State/cache/runtime
directories are **not** created speculatively.

## Initial setup

```bash
uv sync
better-dontforget config set provider gemini
better-dontforget config set api_key "$GEMINI_API_KEY"
# or rely on the GEMINI_API_KEY / OPENAI_API_KEY environment variables
```

Capture and local search work immediately, even before any provider is set.

## CLI configuration commands

```bash
better-dontforget config show            # display current settings (secrets masked)
better-dontforget config set provider openai
better-dontforget config set model gpt-4o-mini
better-dontforget config set base_url https://openrouter.ai/api/v1
better-dontforget config set api_key sk-...
better-dontforget config set notifications_enabled true
better-dontforget config reset provider  # reset a key to its default
```

## TUI settings

Open the TUI (`better-dontforget tui`) and press `s`. The settings screen lets you
set the provider, model, base URL, API key, and desktop-notification toggle, then
**Save**. Changes are written to the same XDG config file.

## Available settings

| Key | Default | Valid values |
| --- | --- | --- |
| `provider` | `gemini` | `gemini`, `openai`, `groq` |
| `model` | `""` (provider default) | any model id; blank = provider default |
| `api_key` | `""` | provider API key (or use env var) |
| `base_url` | `""` | OpenAI-compatible base URL (optional; auto-set for `groq`) |
| `notifications_enabled` | `true` | `true` / `false` |

## AI provider configuration

* **gemini** — Google Gemini. Credential: `GEMINI_API_KEY` env var or
  `config set api_key`. Default model: `gemini-2.5-flash`.
* **openai** — OpenAI-compatible (OpenAI, OpenRouter, self-hosted). Credential:
  `OPENAI_API_KEY` env var or `config set api_key`. Default model: `gpt-4o-mini`.
  Set `base_url` for OpenRouter (`https://openrouter.ai/api/v1`) or a custom
  endpoint.
* **groq** — Groq's OpenAI-compatible API (fast open-weight models). Credential:
  `GROQ_API_KEY` env var or `config set api_key`. Default model:
  `llama-3.1-8b-instant`. The `base_url` is set automatically to
  `https://api.groq.com/openai/v1`; you normally don't need to set it.

When both a stored `api_key` and an environment variable are present, the stored
key takes precedence.

## Choosing a model

Each provider has a sensible default model, but you are free to choose any model
the provider offers. First, list the models available to your configured provider
(requires the provider's API key to be set):

```bash
better-dontforget models
bdf models
```

This queries the provider and prints the available model ids (the currently
selected one is marked). Then pick one:

```bash
better-dontforget config set model llama-3.1-8b-instant
better-dontforget config reset model   # revert to the provider default
```

`config show` displays the effective model. The default model is only a fallback
used when you haven't set one explicitly.

## API credential behavior

* Credentials are read from the config file or the relevant environment variable.
* The config file is written with `0600` permissions.
* `config show` prints `configured`, `set via environment`, or `not set` — never
  the key itself.
* Credentials are never written to logs, panic output, error messages, or test
  snapshots.

## Notification settings

`notifications_enabled` toggles whether `notify-pending` (and the systemd timer)
actually deliver desktop notifications. When disabled, reminders are still tracked
and persisted; they are simply not pushed to the desktop.

## Resetting settings

```bash
better-dontforget config reset <key>   # one key
```

To start fully fresh, remove the config file:

```bash
rm ~/.config/better-dontforget/config.toml
```

## Migration / compatibility

* Existing upstream `memory.db` (SQLite + FTS5) found in the current directory or
  your home is copied into the XDG data directory on first run.
* The schema is extended with optional `reminder_at`, `notified`, `encrypted`, and
  `enc_content` columns via a backward-compatible migration. Your existing notes
  and tags are preserved; no data is silently discarded.
