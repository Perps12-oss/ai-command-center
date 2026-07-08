"""Model capability tiers — warnings only, not hard blocks (Phase 3A stub)."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

DEFAULT_MODEL_TIER_MAP: dict[str, str] = {
    "fast": "llama3.2:3b",
    "balanced": "llama3.2:3b",
    "reasoning": "llama3.2:3b",
}


def normalize_tier_map(
    raw: Any,
    *,
    default_model: str = "llama3.2:3b",
) -> dict[str, str]:
    """Merge persisted tier map with defaults; always seed balanced from default_model."""
    merged = dict(DEFAULT_MODEL_TIER_MAP)
    if default_model:
        merged["balanced"] = default_model
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except json.JSONDecodeError:
            raw = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            tier = str(key).strip()
            model = str(value).strip()
            if tier and model:
                merged[tier] = model
    return merged


class ModelCapability(str, Enum):
    RECOMMENDED = "recommended"
    ALLOWED = "allowed"
    EXPERIMENTAL = "experimental"
    UNKNOWN = "unknown"


def classify_model(model_name: str) -> ModelCapability:
    """Infer tier from Ollama model tag (e.g. llama3.2:3b)."""
    lower = model_name.lower()
    if ":13b" in lower or "-13b" in lower or "13b" in lower:
        return ModelCapability.EXPERIMENTAL
    if ":7b" in lower or "-7b" in lower or "7b" in lower:
        return ModelCapability.ALLOWED
    if ":3b" in lower or "-3b" in lower or "3b" in lower:
        return ModelCapability.RECOMMENDED
    return ModelCapability.UNKNOWN


def model_warning(model_name: str) -> str | None:
    """User-facing warning for experimental models; None if no warning."""
    tier = classify_model(model_name)
    if tier == ModelCapability.EXPERIMENTAL:
        return (
            f"{model_name} is experimental on this device — expect slow responses "
            "and high memory use."
        )
    return None
