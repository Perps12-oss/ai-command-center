"""ComplianceEngine — validates responses and detects hallucinations.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.5
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.operator.mode_resolver import OperatorMode


class ViolationType(str, Enum):
    """Types of compliance violations."""

    HALLUCINATED_CAPABILITY = "hallucinated_capability"
    """Claim about a capability not in the registry."""

    INVALID_PROVIDER = "invalid_provider"
    """Reference to an unknown/external provider."""

    MISSING_EVIDENCE = "missing_evidence"
    """Claim without supporting evidence."""

    CONTRACT_VIOLATION = "contract_violation"
    """Response violates the mode's contract structure."""

    FORBIDDEN_CLAIM = "forbidden_claim"
    """Disallowed claim type per constitution."""

    EXTERNAL_URL_REFERENCE = "external_url_reference"
    """Unauthorized reference to external URLs."""


class Severity(str, Enum):
    """Violation severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceViolation:
    """A single compliance violation detected in a response."""

    violation_type: ViolationType
    severity: Severity
    message: str
    location: str | None = None  # Where in the response
    suggestion: str | None = None  # How to fix
    evidence_required: bool = False


class ComplianceEngine:
    """Validates responses for compliance with operator contracts.

    The compliance engine catches:
    - Hallucinated capabilities
    - Claims without evidence
    - Contract violations
    - Forbidden claims
    """

    # Forbidden phrases that indicate potential issues
    FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
        ("i am not sure", "Avoid uncertainty without evidence"),
        ("i cannot verify", "Must verify claims before making them"),
        ("might be", "Use definitive language or mark as speculation"),
    ]

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._capability_registry: set[str] = set()
        self._provider_registry: set[str] = set()

    def register_capability(self, capability: str) -> None:
        """Register a known capability for validation."""
        self._capability_registry.add(capability.lower())

    def register_provider(self, provider: str) -> None:
        """Register a known provider for validation."""
        self._provider_registry.add(provider.lower())

    def validate(
        self,
        response: str,
        mode: OperatorMode,
        workspace_context: dict[str, Any] | None = None,
    ) -> list[ComplianceViolation]:
        """Validate a response for compliance.

        Returns a list of violations found. Empty list means compliance.
        """
        violations: list[ComplianceViolation] = []

        # Check for forbidden patterns
        violations.extend(self._check_forbidden_patterns(response))

        # Check for contract violations
        violations.extend(self._check_contract_compliance(response, mode))

        # Check for capability hallucinations
        if self._capability_registry:
            violations.extend(self._check_capability_hallucinations(response))

        # Check for evidence requirements
        violations.extend(self._check_evidence_requirements(response))

        # Publish validation event
        self._bus.publish(
            "operator.compliance.validated",
            {
                "violation_count": len(violations),
                "severities": [v.severity.value for v in violations],
            },
            source="compliance_engine",
        )

        return violations

    def _check_forbidden_patterns(
        self,
        response: str,
    ) -> list[ComplianceViolation]:
        """Check for forbidden phrases in the response."""
        violations = []
        response_lower = response.lower()

        for pattern, suggestion in self.FORBIDDEN_PATTERNS:
            if pattern in response_lower:
                violations.append(
                    ComplianceViolation(
                        violation_type=ViolationType.FORBIDDEN_CLAIM,
                        severity=Severity.MEDIUM,
                        message=f"Forbidden pattern detected: '{pattern}'",
                        suggestion=suggestion,
                    )
                )

        return violations

    def _check_contract_compliance(
        self,
        response: str,
        mode: OperatorMode,
    ) -> list[ComplianceViolation]:
        """Check that response conforms to the mode's contract."""
        violations = []
        response_lower = response.lower()

        # COMMAND mode should produce actionable commands
        if mode.value == "command":
            command_indicators = ["run", "execute", "command", "install", "create"]
            if not any(ind in response_lower for ind in command_indicators):
                violations.append(
                    ComplianceViolation(
                        violation_type=ViolationType.CONTRACT_VIOLATION,
                        severity=Severity.HIGH,
                        message="Command mode response does not contain actionable commands",
                        suggestion="Response should include specific commands to execute",
                    )
                )

        # INVESTIGATION mode should produce findings with evidence
        if mode.value == "investigation":
            evidence_indicators = ["because", "therefore", "indicates", "evidence"]
            if not any(ind in response_lower for ind in evidence_indicators):
                violations.append(
                    ComplianceViolation(
                        violation_type=ViolationType.MISSING_EVIDENCE,
                        severity=Severity.MEDIUM,
                        message="Investigation mode response lacks evidence backing",
                        suggestion="Include evidence and reasoning for findings",
                    )
                )

        return violations

    def _check_capability_hallucinations(
        self,
        response: str,
    ) -> list[ComplianceViolation]:
        """Check for references to unregistered capabilities."""
        violations = []

        # Common hallucination patterns
        hallucination_indicators = [
            "i can use",
            "i have access to",
            "i know how to",
            "i can call",
        ]

        response_lower = response.lower()
        for indicator in hallucination_indicators:
            if indicator in response_lower:
                # Extract the claimed capability (simplified)
                idx = response_lower.find(indicator)
                potential_claim = response[idx : idx + 100]

                # Check if it references any known capability
                known_ref = any(cap in potential_claim for cap in self._capability_registry)
                if not known_ref and len(potential_claim) < 50:
                    violations.append(
                        ComplianceViolation(
                            violation_type=ViolationType.HALLUCINATED_CAPABILITY,
                            severity=Severity.HIGH,
                            message="Potential hallucinated capability reference",
                            location=f"near position {idx}",
                            suggestion="Verify this capability exists in the registry",
                        )
                    )

        return violations

    def _check_evidence_requirements(
        self,
        response: str,
    ) -> list[ComplianceViolation]:
        """Check for claims that require evidence."""
        violations = []

        # Claims that need evidence
        claim_patterns = [
            ("always", "Universal claims require evidence"),
            ("never", "Universal claims require evidence"),
            ("every", "Universal claims require evidence"),
            ("all", "Universal claims require evidence"),
            ("none", "Universal claims require evidence"),
        ]

        response_lower = response.lower()
        for pattern, suggestion in claim_patterns:
            if f" {pattern} " in f" {response_lower} ":
                violations.append(
                    ComplianceViolation(
                        violation_type=ViolationType.MISSING_EVIDENCE,
                        severity=Severity.MEDIUM,
                        message=f"Universal claim '{pattern}' detected",
                        suggestion=suggestion,
                    )
                )

        return violations


__all__ = [
    "ComplianceEngine",
    "ComplianceViolation",
    "Severity",
    "ViolationType",
]
