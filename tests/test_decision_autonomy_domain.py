"""AutonomyScore + DecisionRecord domain (ADR-021 / ADR-022)."""

from __future__ import annotations

from ai_command_center.domain.autonomy_score import AutonomyScore
from ai_command_center.domain.decision_record import DecisionRecord


def test_autonomy_score_aggregate_and_escalate() -> None:
    score = AutonomyScore.compute(
        policy_confidence=0.9,
        evidence_confidence=0.9,
        verification_confidence=0.9,
        execution_confidence=0.9,
        threshold=0.6,
    )
    assert score.aggregate >= 0.9
    assert not score.escalate

    low = AutonomyScore.compute(
        policy_confidence=0.2,
        evidence_confidence=0.2,
        verification_confidence=0.2,
        execution_confidence=0.2,
        threshold=0.6,
    )
    assert low.escalate

    blocked = AutonomyScore.compute(
        policy_confidence=1.0,
        evidence_confidence=1.0,
        verification_confidence=1.0,
        execution_confidence=1.0,
        hard_policy_block=True,
    )
    assert blocked.escalate


def test_decision_record_roundtrip() -> None:
    record = DecisionRecord(
        record_id="r1",
        run_id="run",
        step_id="s1",
        capability="shell",
        evidence={"obs": 1},
        policy={"require_approval": True},
        summary="awaiting approval",
    )
    data = record.to_dict()
    back = DecisionRecord.from_dict(data)
    assert back.record_id == "r1"
    assert back.policy["require_approval"] is True


def test_decision_record_missing_marker_never_empty_dict() -> None:
    from ai_command_center.domain.decision_record import MISSING_MARKER, is_missing

    record = DecisionRecord(record_id="r2", summary="ok")
    data = record.to_dict()
    assert data["receipt"] == {"status": MISSING_MARKER}
    assert data["verification"] == {"status": MISSING_MARKER}
    assert "receipt" in data and "evidence" in data
    assert is_missing(data["receipt"])
    assert data["receipt"] != {}


def test_decision_record_card_only_when_pending_intention() -> None:
    from ai_command_center.domain.decision_record import should_mount_decision_card

    assert should_mount_decision_card(actor_type="intention", pending=True)
    assert not should_mount_decision_card(actor_type="intention", pending=False)
    assert not should_mount_decision_card(actor_type="tool", pending=True)


def test_decision_record_reasoning_shows_missing_not_blank_success() -> None:
    from ai_command_center.domain.decision_record import MISSING_MARKER, reasoning_copy

    text = reasoning_copy(
        {
            "summary": "step completed: notes.search",
            "evidence": {"observations": []},
            "policy": {"require_approval": False},
            "receipt": {"status": MISSING_MARKER},
            "verification": {"status": MISSING_MARKER},
        },
        fallback="mode prose",
    )
    assert "missing" in text
    assert "blank" not in text
