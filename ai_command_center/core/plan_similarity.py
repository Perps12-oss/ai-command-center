"""Plan similarity / stuck-loop detection (ADR-019 M4)."""

from __future__ import annotations

import json
from typing import Any


def _tokenize(text: str) -> set[str]:
    return {tok for tok in text.lower().split() if tok}


def jaccard_similarity(a: str, b: str) -> float:
    """Token Jaccard similarity in [0, 1]. Empty strings → 1.0 if both empty else 0.0."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def serialize_plan(plan: Any) -> str:
    """Stable string form of a plan for similarity comparison."""
    if plan is None:
        return ""
    if hasattr(plan, "to_dict"):
        data = plan.to_dict()
    elif isinstance(plan, dict):
        data = plan
    else:
        data = {"repr": str(plan)}
    return json.dumps(data, sort_keys=True, default=str)


def is_stuck(
    plan_history: list[str],
    *,
    min_plans: int = 3,
    threshold: float = 0.92,
) -> bool:
    """True when the last three plan serializations are pairwise near-duplicates."""
    if len(plan_history) < min_plans:
        return False
    a, b, c = plan_history[-3], plan_history[-2], plan_history[-1]
    return (
        jaccard_similarity(a, b) >= threshold
        and jaccard_similarity(b, c) >= threshold
    )


__all__ = ["jaccard_similarity", "serialize_plan", "is_stuck"]
