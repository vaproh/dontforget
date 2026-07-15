"""Shared test fixtures for Better Dontforget.

Tests never require real API keys, network, or a graphical desktop. AI providers
and notifiers are faked; XDG paths point at temporary directories.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from better_dontforget.core.providers import ProviderError


@pytest.fixture
def xdg_tmp(tmp_path, monkeypatch):
    """Point all XDG roots at a temp tree and clear conflicting env vars."""
    for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"):
        monkeypatch.delenv(var, raising=False)
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    cfg.mkdir()
    data.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    return tmp_path


@pytest.fixture
def xdg_fallback(tmp_path, monkeypatch):
    """No XDG vars set; fall back to a temp HOME."""
    for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"):
        monkeypatch.delenv(var, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return tmp_path


class FakeProvider:
    """A deterministic AIProvider stand-in for tests."""

    name = "fake"

    def __init__(
        self,
        tags=None,
        keywords=None,
        answer="synthesized answer",
        fail=False,
        malformed=False,
    ):
        self.tags = tags if tags is not None else ["tag1", "tag2"]
        self.keywords = keywords if keywords is not None else ["kw1", "kw2"]
        self.answer = answer
        self.fail = fail
        self.malformed = malformed
        self.calls = []

    def complete(self, prompt, *, system=None, json_mode=False):
        self.calls.append((prompt, system, json_mode))
        if self.fail:
            raise ProviderError("fake failure")
        if json_mode:
            if self.malformed:
                return "this is not json {"
            if "keywords" in prompt.lower():
                return json.dumps({"keywords": self.keywords})
            return json.dumps({"tags": self.tags})
        return self.answer


@pytest.fixture
def fake_provider():
    return FakeProvider()


class FakeNotifier:
    def __init__(self):
        self.sent = []
        self.fail = False

    def notify(self, title, message):
        if self.fail:
            return False
        self.sent.append((title, message))
        return True


@pytest.fixture
def fake_notifier():
    return FakeNotifier()


def make_legacy_db(path: Path) -> None:
    """Create an upstream-style memory.db (no reminder/encryption columns)."""
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE memories ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, "
        "raw_text TEXT, ai_tags TEXT)"
    )
    conn.execute(
        "INSERT INTO memories (raw_text, ai_tags) VALUES (?, ?)",
        ("legacy wifi note", "network"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def past_dt():
    return datetime.now() - timedelta(hours=1)


@pytest.fixture
def future_dt():
    return datetime.now() + timedelta(hours=1)
