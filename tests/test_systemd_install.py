"""Tests for the systemd notifier installer (no real systemd touched)."""

from unittest.mock import patch

from better_dontforget.core import systemd_install as si


def test_write_units_rewrites_binary(tmp_path):
    si.write_units(tmp_path, "/opt/bdf")
    svc = tmp_path / "better-dontforget-notify.service"
    timer = tmp_path / "better-dontforget-notify.timer"
    assert svc.exists() and timer.exists()
    text = svc.read_text()
    assert "__BINARY__" not in text
    assert "ExecStart=/opt/bdf notify-pending" in text


def test_notifier_status_running():
    with (
        patch.object(si, "_run", lambda *a, **k: 0),
        patch.object(si.platform, "system", lambda: "Linux"),
        patch.object(si.shutil, "which", lambda n: "/bin/systemctl"),
    ):
        assert si.notifier_status() == si.NotifierState.RUNNING


def test_notifier_status_installed_inactive():
    def fake_run(*a, **k):
        return 0 if "is-enabled" in a else 1

    with (
        patch.object(si, "_run", fake_run),
        patch.object(si.platform, "system", lambda: "Linux"),
        patch.object(si.shutil, "which", lambda n: "/bin/systemctl"),
    ):
        assert si.notifier_status() == si.NotifierState.INSTALLED_INACTIVE


def test_notifier_status_not_installed():
    with (
        patch.object(si, "_run", lambda *a, **k: 1),
        patch.object(si.platform, "system", lambda: "Linux"),
        patch.object(si.shutil, "which", lambda n: "/bin/systemctl"),
    ):
        assert si.notifier_status() == si.NotifierState.NOT_INSTALLED


def test_notifier_status_unsupported():
    with patch.object(si.platform, "system", lambda: "Darwin"):
        assert si.notifier_status() == si.NotifierState.UNSUPPORTED
