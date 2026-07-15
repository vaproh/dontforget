"""Configuration model and persistence for Better Dontforget.

Configuration lives as TOML in the XDG config directory and is managed through
the CLI (`config show|set|reset`) and the TUI. Secrets are never printed in
plaintext by the display helpers here.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import tomli_w

from .paths import config_path

DEFAULTS: dict[str, Any] = {
    "provider": "gemini",
    "model": "",
    "api_key": "",
    "base_url": "",
    "notifications_enabled": True,
}

PROVIDER_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
}

VALID_PROVIDERS = ("gemini", "openai", "groq")


@dataclass
class Config:
    provider: str = "gemini"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    notifications_enabled: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        path = path or config_path()
        data: dict[str, Any] = {}
        if path.exists():
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        merged = {**DEFAULTS, **data}
        return cls(
            provider=merged.get("provider", DEFAULTS["provider"]),
            model=merged.get("model", "") or "",
            api_key=merged.get("api_key", "") or "",
            base_url=merged.get("base_url", "") or "",
            notifications_enabled=bool(merged.get("notifications_enabled", True)),
        )

    def save(self, path: Path | None = None) -> None:
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            tomli_w.dump(asdict(self), fh)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def set(self, key: str, value: str) -> None:
        if key not in DEFAULTS:
            raise KeyError(f"Unknown config key: {key}")
        if key == "provider":
            if value not in VALID_PROVIDERS:
                raise ValueError(
                    f"Invalid provider '{value}'. Choose from: {', '.join(VALID_PROVIDERS)}"
                )
            self.provider = value
        elif key == "notifications_enabled":
            self.notifications_enabled = value.strip().lower() in ("1", "true", "yes", "on")
        elif key == "model":
            self.model = value
        elif key == "base_url":
            self.base_url = value
        elif key == "api_key":
            self.api_key = value

    def reset(self, key: str) -> None:
        if key not in DEFAULTS:
            raise KeyError(f"Unknown config key: {key}")
        setattr(self, key, DEFAULTS[key])

    def effective_model(self) -> str:
        if self.model:
            return self.model
        return self.default_model()

    def default_model(self) -> str:
        if self.provider == "gemini":
            return "gemini-2.5-flash"
        if self.provider == "openai":
            return "gpt-4o-mini"
        if self.provider == "groq":
            return "llama-3.1-8b-instant"
        return ""

    def env_key(self) -> str | None:
        return PROVIDER_KEY_ENV.get(self.provider)

    def resolved_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        env = self.env_key()
        if env:
            return os.environ.get(env, "")
        return ""

    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        return os.environ.get("OPENAI_BASE_URL", "")


def describe_secret(config: Config) -> str:
    """Human-safe description of credential state (never the secret itself)."""
    if config.api_key:
        return "configured"
    env = config.env_key()
    if env and os.environ.get(env):
        return "set via environment"
    return "not set"
