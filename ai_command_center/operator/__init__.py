"""Operator package — model-agnostic operator behavior.

This package implements Phase 8 of the implementation plan:
- OperatorKernel: Core orchestration
- IntentResolver: User intent classification
- ModeResolver: Operator mode detection
- ComplianceEngine: Hallucination detection and validation
- ResponseContracts: Structured response schemas
"""

from ai_command_center.operator.kernel import OperatorKernel
from ai_command_center.operator.intent_resolver import IntentResolver, Intent, IntentType
from ai_command_center.operator.mode_resolver import ModeResolver, OperatorMode
from ai_command_center.operator.compliance_engine import ComplianceEngine, ComplianceViolation
from ai_command_center.operator.response_contracts import (
    ChatResponse,
    CommandResponse,
    InvestigationResponse,
    ArchitectResponse,
    ResponseContract,
)

__all__ = [
    # Kernel
    "OperatorKernel",
    # Intent
    "IntentResolver",
    "Intent",
    "IntentType",
    # Mode
    "ModeResolver",
    "OperatorMode",
    # Compliance
    "ComplianceEngine",
    "ComplianceViolation",
    # Contracts
    "ChatResponse",
    "CommandResponse",
    "InvestigationResponse",
    "ArchitectResponse",
    "ResponseContract",
]
