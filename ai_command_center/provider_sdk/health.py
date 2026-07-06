"""Health helpers for provider SDK."""

from __future__ import annotations


def normalize_health_status(healthy: bool, detail: str = "") -> str:
    if healthy:
        return "healthy"
    if detail and "degraded" in detail.lower():
        return "degraded"
    return "offline"
