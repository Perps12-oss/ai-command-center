"""ADR-018 M3: only ExecutionOrchestrator may publish TOOL_INVOKE."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "arch_lint.py"
_spec = importlib.util.spec_from_file_location("arch_lint", _SCRIPT)
assert _spec and _spec.loader
lint = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lint
_spec.loader.exec_module(lint)


def test_repo_has_no_unauthorized_tool_invoke_publishers() -> None:
    violations = lint.scan_tree(_ROOT / "ai_command_center")
    r5 = [v for v in violations if v.rule == "R5"]
    assert not r5, (
        "unauthorized TOOL_INVOKE publisher(s) (ADR-018 M3):\n"
        + "\n".join(f"  {v.file}:{v.line} {v.message}" for v in r5)
    )


def test_execution_orchestrator_is_only_allowlisted_publisher() -> None:
    assert lint._TOOL_INVOKE_PUBLISHER_ALLOWLIST == frozenset(
        {"services/execution_orchestrator_service.py"}
    )
