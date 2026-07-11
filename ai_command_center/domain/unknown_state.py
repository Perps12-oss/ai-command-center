"""Canonical unknown state for unhandled execution results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnknownState:
    """Immutable record of an unrecognized execution state.

    Used when an orchestration provider returns a result that cannot be
    mapped to a known domain state.
    """

    source: str
    reason: str
    raw_value: str = ""
