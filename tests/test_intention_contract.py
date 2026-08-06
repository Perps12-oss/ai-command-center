"""Tests for Intention validation and PlanStep mapping (ADR-018)."""

from __future__ import annotations

from ai_command_center.core.intention_validation import (
    parse_intention_payload,
    validate_intention,
    validate_intention_payload,
)
from ai_command_center.domain.intention import Intention
from ai_command_center.domain.planner_plan import PlanStep


def test_intention_roundtrip_plan_step() -> None:
    step = PlanStep(
        step_id="s1",
        capability="shell",
        args={"command": "echo hi"},
        require_approval=False,
    )
    intention = Intention.from_plan_step(step)
    assert intention.capability == "shell"
    back = intention.to_plan_step()
    assert back.capability == step.capability
    assert back.args == step.args


def test_parse_rejects_executable_tool_shape() -> None:
    result = parse_intention_payload({"tool": "shell", "arguments": {"command": "x"}})
    assert not result.ok
    assert result.kind == "parse"


def test_validation_requires_shell_command() -> None:
    intention = Intention(capability="shell", args={})
    result = validate_intention(intention)
    assert not result.ok
    assert result.kind == "validation"
    assert "command" in result.message


def test_validation_unknown_capability() -> None:
    intention = Intention(capability="not_a_real_tool", args={})
    result = validate_intention(intention, known_capabilities=frozenset({"shell"}))
    assert not result.ok
    assert result.kind == "validation"


def test_validate_payload_ok() -> None:
    result = validate_intention_payload(
        {"capability": "shell", "args": {"command": "echo ok"}, "step_id": "1"},
        known_capabilities=frozenset({"shell"}),
    )
    assert result.ok
    assert result.intention is not None
    assert result.intention.capability == "shell"
