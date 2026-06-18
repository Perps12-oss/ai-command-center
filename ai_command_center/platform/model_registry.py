"""Model capability tiers — warnings only, not hard blocks (Phase 3A stub)."""

from __future__ import annotations

from enum import Enum


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
