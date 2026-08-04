"""Runtime identity fingerprint used to reject stale freeze reports."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.runtime_identity import (
    REQUIRED_FREEZE_FIX,
    assert_event_bus_budget_format,
    collect_runtime_identity,
    print_runtime_identity,
)
from ai_command_center.ui.app import ACC_UI_FREEZE_FIX


def test_required_freeze_fix_matches_app_constant() -> None:
    assert ACC_UI_FREEZE_FIX == REQUIRED_FREEZE_FIX == "v6"


def test_collect_runtime_identity_paths(tmp_path: Path) -> None:
    identity = collect_runtime_identity(main_file=str(tmp_path / "main.py"))
    assert identity.freeze_fix == "v6"
    assert identity.is_current
    assert "event_bus" in identity.event_bus_path.replace("\\", "/")
    assert identity.package_root


def test_print_runtime_identity_emits_two_lines(capsys) -> None:
    identity = print_runtime_identity(main_file=__file__, stream=None)
    # stdout + stderr mirrors
    captured = capsys.readouterr()
    assert "ACC_UI_RUNTIME freeze_fix=v6" in captured.out
    assert "ACC_UI_RUNTIME main=" in captured.out
    assert "ACC_UI_RUNTIME freeze_fix=v6" in captured.err
    assert identity.is_current


def test_event_bus_budget_format_includes_handler() -> None:
    assert assert_event_bus_budget_format() is True


def test_main_py_wires_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "main.py").read_text(encoding="utf-8")
    assert "print_runtime_identity" in text
    assert "Ctrl+Shift+P for Performance Inspector" in text
