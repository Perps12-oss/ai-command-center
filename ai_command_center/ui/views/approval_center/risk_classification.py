"""Risk composition helpers for Approval Center (no invented domain data)."""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionStepSnapshot,
)
from ai_command_center.domain.execution_plan import RiskTier, capability_risk_for
from ai_command_center.domain.permission_check_snapshot import PendingCheck

_VALID_TIERS = frozenset({"low", "medium", "high", "critical", "unknown"})

# Map known permission strings onto capability names consumed by RiskTier helpers.
_PERMISSION_TO_CAPABILITY: dict[str, str] = {
    "launch_tool": "shell",
    "shell": "shell",
    "modify_file": "modify_file",
    "delete_file": "delete_file",
    "git_push": "git_push",
    "send_email": "send_email",
    "create_note": "create_note",
    "create_task": "create_task",
    "create_entity": "create_entity",
    "search_files": "search_files",
    "use_ai": "use_ai",
}


@dataclass(frozen=True, slots=True)
class RiskClassificationView:
    """UI-only composition result for Risk Classification panel."""

    tier: str  # low | medium | high | critical | unknown
    reason: str
    source: str  # execution_step | capability_map | unknown


def _normalize_tier(raw: str) -> str:
    tier = str(raw or "").strip().lower()
    if tier in _VALID_TIERS:
        return tier
    return ""


def _awaiting_or_current_step(
    library: ExecutionLibrarySnapshot | None,
) -> ExecutionStepSnapshot | None:
    if library is None:
        return None
    plan = library.active_plan
    if not plan.is_active and plan.status != "awaiting_approval":
        # Still allow current_step when plan idle if a step carries risk.
        pass
    awaiting = [
        s
        for s in plan.steps
        if str(s.status).lower() in {"awaiting_approval", "awaiting"}
    ]
    if awaiting:
        return awaiting[0]
    return plan.current_step


def classify_approval_risk(
    pending: PendingCheck | None,
    *,
    execution_library: ExecutionLibrarySnapshot | None = None,
) -> RiskClassificationView:
    """Compose risk with explicit source and rationale (Correction #2)."""
    step = _awaiting_or_current_step(execution_library)
    if step is not None:
        tier = _normalize_tier(step.risk)
        if tier and tier != "unknown":
            reason = (
                f"Active execution step '{step.step_id or step.capability or '—'}' "
                f"projects risk '{tier}'"
                + (f" for capability '{step.capability}'" if step.capability else "")
            )
            return RiskClassificationView(
                tier=tier,
                reason=reason,
                source="execution_step",
            )
        if step.capability:
            mapped = capability_risk_for(step.capability)
            return RiskClassificationView(
                tier=mapped.value,
                reason=(
                    f"Capability '{step.capability}' maps to {mapped.value} "
                    f"via existing capability risk mapping"
                ),
                source="capability_map",
            )

    if pending is not None and pending.permissions:
        highest: RiskTier | None = None
        chosen_perm = ""
        for perm in pending.permissions:
            key = str(perm).strip().lower()
            capability = _PERMISSION_TO_CAPABILITY.get(key, key)
            tier = capability_risk_for(capability)
            if highest is None or (
                (tier == RiskTier.HIGH)
                or (tier == RiskTier.MEDIUM and highest == RiskTier.LOW)
            ):
                highest = tier
                chosen_perm = key
        if highest is not None:
            return RiskClassificationView(
                tier=highest.value,
                reason=(
                    f"Requested permission '{chosen_perm}' maps to {highest.value} "
                    f"via existing capability risk mapping"
                ),
                source="capability_map",
            )

    return RiskClassificationView(
        tier="unknown",
        reason="No execution step risk or capability mapping available in projections",
        source="unknown",
    )
