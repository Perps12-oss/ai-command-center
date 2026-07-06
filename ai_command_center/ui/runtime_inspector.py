"""Runtime Inspector 2.0 — read-only diagnostics for orchestration runs."""

from __future__ import annotations

import json
import webbrowser

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_PROVIDERS_READY,
    ORCHESTRATION_PROVIDER_HEALTH,
    ORCHESTRATION_RUN_SNAPSHOT,
)
from ai_command_center.domain.provider_health_snapshot import ProviderHealthSnapshot
from ai_command_center.orchestration.state.orchestration_snapshot import OrchestrationRunSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.ui_queue import UIQueue

_MCP_INSPECTOR_URL = "https://modelcontextprotocol.io/docs/tools/inspector"


class RuntimeInspector(ctk.CTkToplevel):
    """
    Read-only developer inspector with orchestration and capability views.

    Reads all diagnostics from AppStateStore; subscribes to EventBus for refresh
    signals only (no direct service or repository access).
    """

    WIDTH = 760
    HEIGHT = 620

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
        self._filter_request_id = ""
        self._unsubs: list = []

        self.title("Runtime Inspector (dev)")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.configure(fg_color=("#f0f0f0", "#141414"))
        self.resizable(True, True)

        header = ctk.CTkLabel(
            self,
            text="Runtime Inspector 2.0",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        )
        header.pack(pady=(12, 4))

        filter_row = ctk.CTkFrame(self, fg_color="transparent")
        filter_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(filter_row, text="request_id:", font=T.FONT_SMALL).pack(side="left")
        self._filter_entry = ctk.CTkEntry(filter_row, width=220)
        self._filter_entry.pack(side="left", padx=8)
        ctk.CTkButton(filter_row, text="Apply", width=60, command=self._apply_filter).pack(
            side="left"
        )
        ctk.CTkButton(filter_row, text="Clear", width=60, command=self._clear_filter).pack(
            side="left", padx=4
        )

        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=12, pady=4)
        self._text_boxes: dict[str, ctk.CTkTextbox] = {}
        for name in (
            "Conversation",
            "Intent Tree",
            "Timeline",
            "Providers",
            "Receipts",
            "Truth",
            "Response",
            "Capability Explorer",
        ):
            self._tabs.add(name)
            box = ctk.CTkTextbox(self._tabs.tab(name), font=("Consolas", 11))
            box.pack(fill="both", expand=True, padx=4, pady=4)
            self._text_boxes[name] = box

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 12))
        ctk.CTkButton(btn_row, text="Refresh", command=self._refresh).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row,
            text="Open MCP Inspector",
            command=self.open_mcp_inspector,
        ).pack(side="left", padx=4)

        self._unsub_state = self._state_store.subscribe(self._on_state)
        self._wire_events()
        self._refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.transient(master)
        self.focus_set()

    def _wire_events(self) -> None:
        """Subscribe to EventBus topics that affect inspector diagnostics."""
        for topic in (
            ORCHESTRATION_RUN_SNAPSHOT,
            ORCHESTRATION_PROVIDER_HEALTH,
            CAPABILITY_PROVIDERS_READY,
        ):
            self._unsubs.append(
                self._bus.subscribe(topic, lambda _event: self._schedule_refresh())
            )

    def _apply_filter(self) -> None:
        self._filter_request_id = self._filter_entry.get().strip()
        self._refresh()

    def _clear_filter(self) -> None:
        self._filter_request_id = ""
        self._filter_entry.delete(0, "end")
        self._refresh()

    def _on_state(self, _state) -> None:
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        if self._ui_queue is not None:
            self._ui_queue.enqueue(self._refresh)
        elif self.winfo_exists():
            self.after(0, self._refresh)

    def _run(self, snap: OrchestrationRunSnapshot) -> OrchestrationRunSnapshot:
        if not self._filter_request_id:
            return snap
        if snap.request_id == self._filter_request_id:
            return snap
        return OrchestrationRunSnapshot()

    def _set_text(self, name: str, content: str) -> None:
        widget = self._text_boxes[name]
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _refresh(self) -> None:
        state = self._state_store.snapshot
        run = self._run(state.orchestration_run)

        self._set_text(
            "Conversation",
            "\n".join(
                [
                    f"request_id: {run.request_id or '-'}",
                    f"query: {run.query or '-'}",
                    f"trace_id: {run.trace_id or '-'}",
                    f"span_id: {run.span_id or '-'}",
                ]
            ),
        )
        self._set_text(
            "Intent Tree",
            "\n".join(
                [
                    f"intent: {run.intent or '-'}",
                    f"provider_id: {run.provider_id or '-'}",
                    f"receipt_id: {run.receipt_id or '-'}",
                ]
            ),
        )

        timeline_lines = ["Execution runs (feed):"]
        for item in state.execution_runs:
            if self._filter_request_id and item.request_id != self._filter_request_id:
                continue
            timeline_lines.append(
                f"  [{item.source}] {item.request_id} — {item.summary}"
            )
        if run.request_id and run.trace_id:
            timeline_lines.extend(["", f"trace_id: {run.trace_id}"])
        self._set_text("Timeline", "\n".join(timeline_lines) or "-")

        self._set_text("Providers", self._format_provider_health(state.provider_health_map))
        self._set_text(
            "Receipts",
            json.dumps(
                {
                    "receipt_id": run.receipt_id,
                    "execution_success": run.execution_success,
                    "execution_facts": run.execution_facts,
                    "execution_error": run.execution_error,
                },
                indent=2,
            ),
        )
        self._set_text(
            "Truth",
            "\n".join(
                [
                    f"valid: {run.truth_valid}",
                    f"detail: {run.truth_detail or '-'}",
                    f"response_source: {run.response_source or '-'}",
                ]
            ),
        )
        self._set_text("Response", run.response_text or "-")
        self._set_text("Capability Explorer", self._format_capability_explorer(state))

    @staticmethod
    def _format_provider_health(health_map: tuple[ProviderHealthSnapshot, ...]) -> str:
        if not health_map:
            return "No provider health data yet."
        lines = []
        for snap in health_map:
            lines.append(
                f"{snap.provider_id} [{snap.source}] — {snap.status}: {snap.detail or '-'}"
            )
        return "\n".join(lines)

    def _format_capability_explorer(self, state) -> str:
        lines = ["Installed runtime providers:", ""]
        for provider in state.runtime_capability_providers:
            lines.append(f"• {provider.provider_id} ({provider.name}) v{provider.version}")
            lines.append(f"  capabilities: {', '.join(provider.capabilities) or '-'}")
            lines.append(f"  permissions: {', '.join(provider.permissions) or '-'}")
            lines.append(
                f"  health: {provider.health_state} — {provider.health_detail or '-'}"
            )
            lines.append("")
        lines.extend(
            [
                "Diagnostics:",
                f"  execution_runs in feed: {len(state.execution_runs)}",
                f"  provider_health entries: {len(state.provider_health_map)}",
                "",
                "MCP:",
                f"  External MCP Inspector: {_MCP_INSPECTOR_URL}",
                "  (opens in system browser — not embedded)",
            ]
        )
        return "\n".join(lines)

    def open_mcp_inspector(self) -> None:
        webbrowser.open(_MCP_INSPECTOR_URL)

    def _on_close(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsub_state()
        self.destroy()
