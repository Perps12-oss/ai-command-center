"""Runtime path helpers for dev vs frozen builds."""

from __future__ import annotations

import sys
from unittest.mock import patch

from ai_command_center.platform import runtime_paths


def test_is_frozen_false_in_dev() -> None:
    with patch.object(sys, "frozen", False, create=True):
        assert runtime_paths.is_frozen() is False


def test_get_install_dir_dev_points_at_repo_root() -> None:
    with patch.object(runtime_paths, "is_frozen", return_value=False):
        assert (runtime_paths.get_install_dir() / "main.py").is_file()


def test_get_runtime_data_dir_uses_windows_appdata(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(runtime_paths.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))

    path = runtime_paths.get_runtime_data_dir()

    assert path == tmp_path / "AppData" / "Roaming" / "AICommandCenter"
    assert path.is_dir()


def test_get_runtime_data_dir_uses_linux_xdg(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(runtime_paths.sys, "platform", "linux")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    path = runtime_paths.get_runtime_data_dir()

    assert path == tmp_path / "xdg" / "AICommandCenter"
    assert path.is_dir()


def test_get_runtime_data_dir_uses_macos_application_support(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(runtime_paths.sys, "platform", "darwin")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(runtime_paths.Path, "home", classmethod(lambda _cls: tmp_path))

    path = runtime_paths.get_runtime_data_dir()

    assert path == tmp_path / "Library" / "Application Support" / "AICommandCenter"
    assert path.is_dir()
