"""Canonical service state contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceStateSnapshot:
    service_name: str
    state: str
    detail: str = ""
