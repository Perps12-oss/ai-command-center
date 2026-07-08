"""Runtime path helpers for dev vs frozen builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

from ai_command_center.platform import runtime_paths


def test_is_frozen_false_in_dev() -> None:
    with patch.object(sys, "frozen", False, create=True):
        assert runtime_paths.is_frozen() is False


def test_get_install_dir_dev_points_at_repo_root() -> None:
    with patch.object(runtime_paths, "is_frozen", return_value=False):
        assert (runtime_paths.get_install_dir() / "main.py").is_file()


def test_runtime_data_dir_windows_uses_appdata(tmp_path) -> None:
    with patch.object(sys, "platform", "win32"):
        with patch.dict(os.environ, {"APPDATA": str(tmp_path)}, clear=False):
            path = runtime_paths.get_runtime_data_dir()
    assert path == tmp_path / "AICommandCenter"
    assert path.is_dir()


def test_runtime_data_dir_macos_uses_application_support(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = runtime_paths.get_runtime_data_dir()
    assert path == tmp_path / "Library" / "Application Support" / "AICommandCenter"
    assert path.is_dir()


def test_runtime_data_dir_linux_uses_xdg_data_home(tmp_path) -> None:
    xdg = tmp_path / "xdg"
    with patch.object(sys, "platform", "linux"):
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(xdg)}, clear=False):
            path = runtime_paths.get_runtime_data_dir()
    assert path == xdg / "AICommandCenter"
    assert path.is_dir()


def test_runtime_data_dir_linux_default_local_share(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = runtime_paths.get_runtime_data_dir()
    assert path == tmp_path / ".local" / "share" / "AICommandCenter"
    assert path.is_dir()
