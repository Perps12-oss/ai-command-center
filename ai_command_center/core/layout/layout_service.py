"""
Layout Service Contract - FROZEN ARCHITECTURE SPECIFICATION

Minimal contract for saving and loading UI layout configuration.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LayoutService(ABC):
    """
    Minimal layout service contract.
    
    Purpose:
    - Persist panel sizes, visibility, and positions
    - Restore layout on startup
    
    Scope intentionally minimal. No docking framework, no complex layout engine.
    Those can be added later without breaking this contract.
    """

    @abstractmethod
    def save(self, layout_id: str, config: dict[str, Any]) -> None:
        """Save layout configuration for a given layout ID."""
        pass

    @abstractmethod
    def load(self, layout_id: str) -> dict[str, Any] | None:
        """Load layout configuration for a given layout ID."""
        pass
