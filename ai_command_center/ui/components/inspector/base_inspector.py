"""Shared contract for inspector widgets."""

from __future__ import annotations

from abc import abstractmethod

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef


class BaseInspector(ctk.CTkFrame):
    """Base class for inspector widgets."""

    @abstractmethod
    def update(self, ref: InspectableRef) -> None:
        raise NotImplementedError


__all__ = ["BaseInspector"]
