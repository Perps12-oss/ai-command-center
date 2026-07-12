"""Tests for ComplianceEngine."""

import pytest

from ai_command_center.operator.compliance_engine import (
    ComplianceEngine,
    ComplianceViolation,
    Severity,
    ViolationType,
)
from ai_command_center.operator.mode_resolver import OperatorMode


@pytest.fixture
def engine(mock_event_bus):
    return ComplianceEngine(mock_event_bus)


class TestComplianceEngine:
    """Tests for ComplianceEngine.validate()"""

    def test_empty_response_passes(self, engine):
        """Empty response has no violations."""
        violations = engine.validate("", OperatorMode.CHAT)
        assert len(violations) == 0

    def test_normal_response_passes(self, engine):
        """Normal response with evidence passes."""
        response = "The bug is in the loop at line 42. Therefore, the fix is to add a bounds check."
        violations = engine.validate(response, OperatorMode.INVESTIGATION)
        assert len(violations) == 0

    def test_detects_forbidden_pattern(self, engine):
        """Engine detects forbidden patterns."""
        response = "I am not sure if this will work"
        violations = engine.validate(response, OperatorMode.CHAT)
        assert any(v.violation_type == ViolationType.FORBIDDEN_CLAIM for v in violations)

    def test_detects_command_contract_violation(self, engine):
        """Command mode without commands fails contract check."""
        response = "This is a normal response without any actionable items"
        violations = engine.validate(response, OperatorMode.COMMAND)
        assert any(
            v.violation_type == ViolationType.CONTRACT_VIOLATION for v in violations
        )

    def test_command_with_action_passes(self, engine):
        """Command mode with command indicators passes."""
        response = "I'll run the tests for you. Execute: pytest tests/"
        violations = engine.validate(response, OperatorMode.COMMAND)
        assert not any(
            v.violation_type == ViolationType.CONTRACT_VIOLATION for v in violations
        )

    def test_investigation_without_evidence_fails(self, engine):
        """Investigation mode without evidence fails."""
        response = "The code is broken"  # No evidence markers
        violations = engine.validate(response, OperatorMode.INVESTIGATION)
        assert any(v.violation_type == ViolationType.MISSING_EVIDENCE for v in violations)

    def test_investigation_with_evidence_passes(self, engine):
        """Investigation mode with evidence passes."""
        response = "The code is broken because of a null pointer. Therefore, add null check."
        violations = engine.validate(response, OperatorMode.INVESTIGATION)
        assert not any(
            v.violation_type == ViolationType.MISSING_EVIDENCE for v in violations
        )

    def test_universal_claims_require_evidence(self, engine):
        """Universal claims ('always', 'never') require evidence."""
        response = "This always fails in production"
        violations = engine.validate(response, OperatorMode.INVESTIGATION)
        assert any(v.violation_type == ViolationType.MISSING_EVIDENCE for v in violations)

    def test_registered_capability_passes(self, engine):
        """Response referencing registered capability passes."""
        engine.register_capability("file_system.read")
        response = "I can use file_system.read to read the file"
        violations = engine.validate(response, OperatorMode.COMMAND)
        assert not any(
            v.violation_type == ViolationType.HALLUCINATED_CAPABILITY for v in violations
        )


class TestComplianceViolation:
    """Tests for ComplianceViolation dataclass."""

    def test_violation_creation(self):
        """ComplianceViolation can be created with all fields."""
        violation = ComplianceViolation(
            violation_type=ViolationType.HALLUCINATED_CAPABILITY,
            severity=Severity.HIGH,
            message="Test violation",
            location="line 42",
            suggestion="Fix this",
            evidence_required=True,
        )
        assert violation.violation_type == ViolationType.HALLUCINATED_CAPABILITY
        assert violation.severity == Severity.HIGH
        assert violation.location == "line 42"
        assert violation.suggestion == "Fix this"
        assert violation.evidence_required is True
