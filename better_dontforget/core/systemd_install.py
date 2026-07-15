"""Install / uninstall / query the Better Dontforget systemd user notifier.

Linux-only. The unit templates are bundled as package data under
``better_dontforget/systemd_units/`` and are written into the user systemd
directory with the real binary path substituted, so the service works regardless
of how the package was installed (``pip``, ``uv tool install``, ``pipx``, …).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from rich.console import Console

console = Console()

UNIT_NAME = "better-dontforget-notify"
SERVICE = f"{UNIT_NAME}.service"
TIMER = f"{UNIT_NAME}.timer"

TEMPLATES = files("better_dontforget") / "systemd_units"


class NotifierState:
    RUNNING = "running"
    INSTALLED_INACTIVE = "installed_inactive"
    NOT_INSTALLED = "not_installed"
    UNSUPPORTED = "unsupported"


def _unit_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "systemd" / "user"


def _detect_binary() -> str:
    for name in ("better-dontforget", "bdf"):
        found = shutil.which(name)
        if found:
            return found
    invoked = Path(sys.argv[0]).name if sys.argv else ""
    if invoked in ("better-dontforget", "bdf"):
        resolved = shutil.which(invoked)
        if resolved:
            return resolved
    return str(Path.home() / ".local" / "bin" / "better-dontforget")


def _run(*args: str, silent: bool = False) -> int:
    try:
        return subprocess.run(
            args,
            check=False,
            stdout=subprocess.DEVNULL if silent else None,
            stderr=subprocess.DEVNULL if silent else None,
        ).returncode
    except Exception:
        return 1


def write_units(unit_dir: Path, binary: str) -> None:
    """Copy the bundled unit files into ``unit_dir``, rewriting the ExecStart path."""
    unit_dir.mkdir(parents=True, exist_ok=True)
    service = (TEMPLATES / SERVICE).read_text().replace("__BINARY__", binary)
    (unit_dir / SERVICE).write_text(service)
    (unit_dir / TIMER).write_text((TEMPLATES / TIMER).read_text())


def install_notifier() -> int:
    """Install and enable the systemd user timer. Returns a process exit code."""
    if platform.system().lower() != "linux":
        console.print("[yellow]systemd user services are Linux-only; nothing installed.[/yellow]")
        return 0

    binary = _detect_binary()
    unit_dir = _unit_dir()
    try:
        write_units(unit_dir, binary)
    except Exception as exc:
        console.print(f"[red]Could not write unit files: {exc}[/red]")
        return 1

    systemctl = shutil.which("systemctl")
    if systemctl is None:
        console.print("[yellow]systemctl not found. Unit files written to:[/yellow]")
        console.print(f"  {unit_dir}")
        console.print("Enable them manually once systemd is available.")
        return 0

    _run(systemctl, "--user", "daemon-reload")
    if _run(systemctl, "--user", "enable", "--now", TIMER) != 0:
        console.print("[red]Failed to enable the timer (see systemctl output above).[/red]")
        return 1
    console.print(f"[green]✔ Notifier installed and enabled ({TIMER}).[/green]")
    return 0


def uninstall_notifier() -> int:
    """Disable and remove the systemd user notifier. Returns a process exit code."""
    if platform.system().lower() != "linux":
        console.print("[yellow]systemd user services are Linux-only.[/yellow]")
        return 0

    systemctl = shutil.which("systemctl")
    unit_dir = _unit_dir()
    if systemctl is not None:
        _run(systemctl, "--user", "disable", "--now", TIMER)
    for path in (unit_dir / SERVICE, unit_dir / TIMER):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    console.print("[green]✔ Notifier removed.[/green]")
    return 0


def notifier_status() -> str:
    """Return the state of the notifier: running / installed_inactive /
    not_installed / unsupported."""
    if platform.system().lower() != "linux":
        return NotifierState.UNSUPPORTED
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return NotifierState.UNSUPPORTED
    if _run(systemctl, "--user", "is-active", TIMER, silent=True) == 0:
        return NotifierState.RUNNING
    if _run(systemctl, "--user", "is-enabled", TIMER, silent=True) == 0:
        return NotifierState.INSTALLED_INACTIVE
    return NotifierState.NOT_INSTALLED
