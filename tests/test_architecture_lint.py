"""Risk area #2 - AST architecture linter behaviour + repo ratchet.

The first group validates the linter logic against synthetic sources (always
deterministic, platform independent). The final test scans the *real* package
against a committed baseline so any *new* boundary violation fails CI.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "arch_lint.py"
_spec = importlib.util.spec_from_file_location("arch_lint", _SCRIPT)
assert _spec and _spec.loader
lint = importlib.util.module_from_spec(_spec)
# Register before exec so dataclasses can resolve string annotations.
sys.modules[_spec.name] = lint
_spec.loader.exec_module(lint)


def _rules(path: str, src: str) -> set[str]:
    return {v.rule for v in lint.analyze_source(path, src)}


# ── R1: UI importing services/backend ─────────────────────────────────────────
def test_r1_flags_ui_importing_services() -> None:
    src = "from ai_command_center.services.asset_service import AssetService\n"
    assert "R1" in _rules("ai_command_center/ui/components/widget.py", src)


def test_r1_flags_ui_plain_import_backend() -> None:
    src = "import ai_command_center.backend.engine\n"
    assert "R1" in _rules("ai_command_center/ui/views/home.py", src)


def test_r1_allows_ui_importing_eventbus_and_appstate() -> None:
    src = (
        "from ai_command_center.core.event_bus import EventBus\n"
        "from ai_command_center.core.app_state import AppState\n"
    )
    assert _rules("ai_command_center/ui/views/home.py", src) == set()


def test_r1_does_not_flag_service_importing_service() -> None:
    src = "from ai_command_center.services.base import BaseService\n"
    assert "R1" not in _rules("ai_command_center/services/chat_service.py", src)


# ── R2: instantiating *Service outside services/ or composition root ───────────
def test_r2_flags_service_instantiation_in_ui() -> None:
    src = "def build():\n    return ChatService(bus)\n"
    assert "R2" in _rules("ai_command_center/ui/views/chat.py", src)


def test_r2_allows_service_instantiation_in_composition_root() -> None:
    src = "def wire():\n    return ChatService(bus)\n"
    assert "R2" not in _rules("ai_command_center/application.py", src)


def test_r2_allows_service_instantiation_within_services() -> None:
    src = "def make():\n    return ToolExecutorService(bus, registry)\n"
    assert "R2" not in _rules("ai_command_center/services/factory.py", src)


def test_r2_ignores_base_service() -> None:
    src = "x = BaseService(bus)\n"
    assert "R2" not in _rules("ai_command_center/ui/views/chat.py", src)


# ── R3: mutating an AppState instance outside the app_state module ─────────────
def test_r3_flags_appstate_attribute_assignment() -> None:
    src = "def handler(app_state):\n    app_state.current_view = 'chat'\n"
    assert "R3" in _rules("ai_command_center/ui/views/chat.py", src)


def test_r3_allows_assignment_inside_appstate_module() -> None:
    src = "def _set(app_state):\n    app_state.phase = 'idle'\n"
    assert "R3" not in _rules("ai_command_center/core/app_state.py", src)


def test_r3_ignores_non_appstate_objects() -> None:
    src = "def f(widget):\n    widget.title = 'hello'\n"
    assert "R3" not in _rules("ai_command_center/ui/views/chat.py", src)


# ── R4: service importing peer service ────────────────────────────────────────
def test_r4_flags_service_importing_peer_service() -> None:
    src = "from ai_command_center.services.chat_handler_service import ChatHandlerService\n"
    assert "R4" in _rules("ai_command_center/services/tool_executor_service.py", src)


def test_r4_allows_service_importing_base() -> None:
    src = "from ai_command_center.services.base import BaseService\n"
    assert "R4" not in _rules("ai_command_center/services/chat_service.py", src)


def test_r4_allows_grandfathered_peer_import() -> None:
    src = "from ai_command_center.services.command_router_service import INTENT_CHAT\n"
    assert "R4" not in _rules("ai_command_center/services/chat_handler_service.py", src)


# ── repo ratchet ──────────────────────────────────────────────────────────────
def test_no_new_architecture_violations_in_repo() -> None:
    baseline_path = _ROOT / "tests" / "arch_lint_baseline.json"
    baseline = lint._load_baseline(baseline_path)
    violations = lint.scan_tree(_ROOT / "ai_command_center")
    parse_errors = [v for v in violations if v.rule == "PARSE"]
    assert not parse_errors, f"linter failed to parse files: {parse_errors}"

    new = [v for v in violations if v.key() not in baseline]
    assert not new, (
        "new architecture boundary violation(s) detected:\n"
        + "\n".join(f"  [{v.rule}] {v.file}:{v.line} {v.message}" for v in new)
    )
