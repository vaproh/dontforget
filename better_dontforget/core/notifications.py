"""Desktop notification abstraction for Better Dontforget.

The default backend shells out to ``notify-send`` (libnotify), the established
Linux desktop-notification mechanism. A :class:`NullNotifier` is used in
headless environments / tests, and a :class:`FakeNotifier` is provided for
tests that need to assert on delivered notifications.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol


class Notifier(Protocol):
    def notify(self, title: str, message: str) -> bool:
        """Return True only if the notification was successfully delivered."""
        ...


class NotifySendNotifier:
    def notify(self, title: str, message: str) -> bool:
        if not shutil.which("notify-send"):
            return False
        try:
            subprocess.run(
                ["notify-send", title, message],
                check=True,
                timeout=10,
                capture_output=True,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            return False


class NullNotifier:
    """Reports success without displaying anything (headless / disabled)."""

    def notify(self, title: str, message: str) -> bool:
        return True


class FakeNotifier:
    """Records notifications for tests. Set ``fail_next`` to simulate failure."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.fail = False

    def notify(self, title: str, message: str) -> bool:
        if self.fail:
            return False
        self.sent.append((title, message))
        return True
