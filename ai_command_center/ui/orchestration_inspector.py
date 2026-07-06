"""Developer-only orchestration runtime inspector."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.ui_queue import UIQueue


class OrchestrationInspector(ctk.CTkToplevel):
    """Read-only developer inspector for truth-bound orchestration runs."""

    WIDTH = 640
    HEIGHT = 520

    def __init__(
        self,
        master: ctk.CTk,
        bus: EventBus,
        state_store: AppStateStore,
        *,
        ui_queue: UIQueue | None = None,
    ) -> None:
        super().__init__(master)
        self._bus = bus
        self._state_store = state_store
        self._ui_queue = ui_queue
        self._unsubs: list = []

        self.title("Orchestration Inspector (dev)")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.configure(fg_color=("#f0f0f0", "#141414"))
        self.resizable(True, True)

        header = ctk.CTkLabel(
            self,
            text="Truth-Bound Orchestration",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        )
        header.pack(pady=(12, 4))

        ctk.CTkLabel(
            self,
            text="Developer only — last orchestration run (read-only)",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack()

        self._text = ctk.CTkTextbox(self, font=("Consolas", 12))
        self._text.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkButton(self, text="Refresh", command=self._refresh).pack(pady=(0, 12))

        self._unsub_state = self._state_store.subscribe(self._on_state)
        self._refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.transient(master)
        self.focus_set()

    def _on_state(self, _state) -> None:
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        if self._ui_queue is not None:
            self._ui_queue.enqueue(self._refresh)
        elif self.winfo_exists():
            self.after(0, self._refresh)

    def _refresh(self) -> None:
        run = self._state_store.snapshot.orchestration_run
        lines = [
            f"Intent: {run.intent or '-'}",
            f"Provider: {run.provider_id or '-'}",
            f"Request ID: {run.request_id or '-'}",
            f"Query: {run.query or '-'}",
            "",
            "Receipt:",
            f"  id: {run.receipt_id or '-'}",
            "",
            "Execution Result:",
            f"  success: {run.execution_success}",
            f"  facts: {run.execution_facts}",
            f"  error: {run.execution_error or '-'}",
            "",
            "Truth Validation:",
            f"  valid: {run.truth_valid}",
            f"  detail: {run.truth_detail or '-'}",
            "",
            "Response Source:",
            f"  {run.response_source or '-'}",
            "",
            "Response:",
            run.response_text or "-",
        ]
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", "\n".join(lines))
        self._text.configure(state="disabled")

    def _on_close(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsub_state()
        self.destroy()
