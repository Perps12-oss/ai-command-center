"""Immutable AppState snapshot for the Orchestration Run system.

Consolidates:
  - orchestration_run: The last orchestration run
  - run_history: Historical orchestration runs (new)
  - provider_health_map: Provider health snapshots (unified)

Constitutional fixes:
  - execution_facts: dict[str, Any] -> tuple[tuple[str, str], ...] (immutable)
  - Class moved from orchestration/state/ to domain/ (proper ownership)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.provider_health_snapshot import ProviderHealthSnapshot


# Maximum history entries to retain
_MAX_RUN_HISTORY = 50


def _dict_to_immutable(d: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Convert a dict to immutable tuple of key-value pairs."""
    return tuple((str(k), str(v)) for k, v in d.items())


def _immutable_to_dict(t: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """Convert immutable tuple back to dict for backward compatibility."""
    return dict(t)


@dataclass(frozen=True, slots=True)
class OrchestrationRunEntry:
    """Immutable snapshot of a single orchestration run for history."""

    request_id: str = ""
    query: str = ""
    intent: str = ""
    provider_id: str = ""
    execution_success: bool = False
    execution_facts: tuple[tuple[str, str], ...] = ()
    execution_error: str | None = None
    truth_valid: bool = False
    truth_detail: str = ""
    response_source: str = ""
    response_text: str = ""
    receipt_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Convert to dict for backward compatibility."""
        return {
            "request_id": self.request_id,
            "query": self.query,
            "intent": self.intent,
            "provider_id": self.provider_id,
            "execution_success": self.execution_success,
            "execution_facts": _immutable_to_dict(self.execution_facts),
            "execution_error": self.execution_error,
            "truth_valid": self.truth_valid,
            "truth_detail": self.truth_detail,
            "response_source": self.response_source,
            "response_text": self.response_text,
            "receipt_id": self.receipt_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class OrchestrationRunSnapshot:
    """Immutable AppState projection of the orchestration system.

    Constitutional fixes:
      - execution_facts is now tuple[tuple[str, str], ...] (immutable)
      - Class is in domain/ (proper ownership per Invariant 13)
      - Includes run_history for audit trail
      - Includes provider_health_map for unified diagnostics
    """

    # Current/last run
    request_id: str = ""
    query: str = ""
    intent: str = ""
    provider_id: str = ""
    execution_success: bool = False
    execution_facts: tuple[tuple[str, str], ...] = ()  # IMMUTABLE - was dict[str, Any]
    execution_error: str | None = None
    truth_valid: bool = False
    truth_detail: str = ""
    response_source: str = ""
    response_text: str = ""
    receipt_id: str = ""
    trace_id: str = ""
    span_id: str = ""

    # Run history (new)
    run_history: tuple[OrchestrationRunEntry, ...] = ()
    total_runs: int = 0

    # Provider health (unified from provider_health_map)
    provider_health: tuple[ProviderHealthSnapshot, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Convert to dict for backward compatibility."""
        return {
            "request_id": self.request_id,
            "query": self.query,
            "intent": self.intent,
            "provider_id": self.provider_id,
            "execution_success": self.execution_success,
            "execution_facts": _immutable_to_dict(self.execution_facts),
            "execution_error": self.execution_error,
            "truth_valid": self.truth_valid,
            "truth_detail": self.truth_detail,
            "response_source": self.response_source,
            "response_text": self.response_text,
            "receipt_id": self.receipt_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "run_history": [e.to_dict() for e in self.run_history],
            "total_runs": self.total_runs,
            "provider_health": [p.to_dict() for p in self.provider_health],
        }

    @property
    def last_run(self) -> OrchestrationRunEntry | None:
        """Return the most recent run entry if available."""
        return self.run_history[0] if self.run_history else None

    @property
    def execution_facts_dict(self) -> dict[str, str]:
        """Get execution_facts as dict for backward compatibility."""
        return _immutable_to_dict(self.execution_facts)
