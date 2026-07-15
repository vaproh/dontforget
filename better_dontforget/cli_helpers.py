"""Shared application context loader for CLI and TUI."""

from __future__ import annotations

import sqlite3

from .core import db as dbmod
from .core.config import Config
from .core.providers import AIProvider, build_provider


def load_app_context() -> tuple[Config, sqlite3.Connection, AIProvider]:
    """Open config, database, and build the AI provider together."""
    config = Config.load()
    conn = dbmod.open_db()
    provider = build_provider(config)
    return config, conn, provider
