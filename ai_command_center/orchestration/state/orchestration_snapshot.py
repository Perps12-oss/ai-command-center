"""Last orchestration run snapshot for developer inspector."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OrchestrationRunSnapshot:
    request_id: str = ""
    query: str = ""
    intent: str = ""
    provider_id: str = ""
    execution_success: bool = False
    execution_facts: dict[str, Any] = field(default_factory=dict)
    execution_error: str | None = None
    truth_valid: bool = False
    truth_detail: str = ""
    response_source: str = ""
    response_text: str = ""
    receipt_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "query": self.query,
            "intent": self.intent,
            "provider_id": self.provider_id,
            "execution_success": self.execution_success,
            "execution_facts": dict(self.execution_facts),
            "execution_error": self.execution_error,
            "truth_valid": self.truth_valid,
            "truth_detail": self.truth_detail,
            "response_source": self.response_source,
            "response_text": self.response_text,
            "receipt_id": self.receipt_id,
        }
