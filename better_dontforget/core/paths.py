"""XDG base-directory compliant paths for Better Dontforget."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "better-dontforget"

_LEGACY_DB_NAME = "memory.db"
_DB_NAME = "better-dontforget.db"
_CONFIG_NAME = "config.toml"


def _xdg_dir(env_var: str, fallback: Path) -> Path:
    base = os.environ.get(env_var)
    if base:
        return Path(base) / APP_NAME
    return fallback / APP_NAME


def config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", Path.home() / ".config")


def data_dir() -> Path:
    return _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share")


def config_path() -> Path:
    return config_dir() / _CONFIG_NAME


def db_path() -> Path:
    return data_dir() / _DB_NAME


def legacy_db_candidates() -> list[Path]:
    """Locations where an upstream memory.db might already exist."""
    return [
        Path.cwd() / _LEGACY_DB_NAME,
        Path.home() / _LEGACY_DB_NAME,
    ]
