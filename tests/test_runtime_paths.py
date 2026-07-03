"""Runtime path helpers for dev vs frozen builds."""

from __future__ import annotations

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
