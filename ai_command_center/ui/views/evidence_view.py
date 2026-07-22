"""Evidence Workspace — claims, truth status, receipts, and traces (PR-UI-E10).

Architecture contract:
- Pure renderer. Reads AppState.orchestration_run via apply_state only.
- Reuses Execution Center truth helpers (truth_state_for_entry / resolve).
- Selection intents via callbacks → UI_EVIDENCE_* / inspect (shell).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.domain.orchestration_run_snapshot import (
    OrchestrationRunEntry,
    OrchestrationRunSnapshot,
)
from ai_command_center.ui.components.evidence import ClaimCard, ReceiptChain
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.execution_center.receipt_viewer_panel import (
    ReceiptViewerPanel,
    resolve_orchestration_entry,
)
from ai_command_center.ui.views.execution_center.truth_validation_panel import (
    TruthValidationPanel,
    truth_state_for_entry,
)
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)
from ai_command_center.ui.widget_utils import clear_children


def list_evidence_claims(
    orch: OrchestrationRunSnapshot,
) -> list[OrchestrationRunSnapshot | OrchestrationRunEntry]:
    """Current run (if any) plus history, newest-first, de-duplicated by request_id."""
    claims: list[OrchestrationRunSnapshot | OrchestrationRunEntry] = []
    seen: set[str] = set()
    if orch.request_id or orch.receipt_id or orch.query:
        claims.append(orch)
        if orch.request_id:
            seen.add(orch.request_id)
    for entry in reversed(orch.run_history):
        rid = entry.request_id
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        claims.append(entry)
    return claims


def claim_label(entry: Any) -> str:
    return str(
        getattr(entry, "query", "")
        or getattr(entry, "intent", "")
        or getattr(entry, "request_id", "")
        or "Untitled claim"
    )


class EvidenceView(ctk.CTkFrame):
    """Evidence list + truth/receipt/trace detail for orchestration claims."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select = on_select
        self._on_inspect_select = on_inspect_select
        self._on_navigate = on_navigate
        self._selected_request_id = ""
        self._last_snap: AppState | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.EXECUTION_BLUE)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Evidence Workspace",
            font=T.FONT_TITLE,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0 claims",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        self._hint = ctk.CTkLabel(
            self._hero,
            text="Claims project from orchestration_run history.",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hint.pack(fill="x", padx=T.PAD, pady=(8, 4))

        if self._on_navigate is not None:
            ctk.CTkButton(
                self._hero,
                text="Open Execution Center",
                width=170,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.EXECUTION_BLUE,
                hover_color=T.ACCENT_HOVER,
                text_color=T.TEXT_PRIMARY,
                command=lambda: self._on_navigate("executions"),
            ).pack(anchor="e", padx=T.PAD, pady=(0, 8))

        self._surface_state = ctk.CTkLabel(
            self._hero,
            text="Loading…",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._surface_state.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        list_host = ctk.CTkFrame(
            body,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        list_host.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            list_host,
            text="Claims",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._claims_scroll = ctk.CTkScrollableFrame(
            list_host, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._claims_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        detail = ctk.CTkFrame(body, fg_color="transparent")
        detail.grid(row=0, column=1, sticky="nsew")
        detail.grid_rowconfigure(0, weight=1)
        detail.grid_rowconfigure(1, weight=1)
        detail.grid_rowconfigure(2, weight=2)
        detail.grid_columnconfigure(0, weight=1)

        self._truth = TruthValidationPanel(detail)
        self._truth.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._receipt = ReceiptViewerPanel(detail)
        self._receipt.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        self._chain = ReceiptChain(detail)
        self._chain.grid(row=2, column=0, sticky="nsew")

    def apply_state(self, snapshot: AppState | None) -> None:
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Evidence Workspace",
                    what="orchestration_run claims, truth, and receipts",
                    next_action="Wait for AppState refresh; then select a claim.",
                ),
            )
            return
        if not isinstance(snapshot, AppState):
            return
        self._last_snap = snapshot
        orch = snapshot.orchestration_run
        claims = list_evidence_claims(orch)
        self._metrics.configure(text=f"{len(claims)} claims")

        err = domain_error_from_snap(
            snapshot, topic_prefixes=("orchestration.", "execution.", "truth.")
        )
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif not claims:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="No orchestration claims are projected yet.",
                    creates="Claims appear when orchestration runs record truth/receipts.",
                    next_action="Run a chat/orchestration request, then return here.",
                ),
            )
            self._hint.configure(text="No claims in orchestration_run yet.")
        else:
            set_surface_state(self._surface_state, kind="data")
            self._hint.configure(
                text=f"Selected: {self._selected_request_id or claims[0].request_id or 'first claim'}"
            )

        if not self._selected_request_id and claims:
            self._selected_request_id = str(getattr(claims[0], "request_id", "") or "")

        self._render_claims(claims)
        selected = self._selected_request_id
        self._truth.apply_snapshot(snapshot, selected_request_id=selected)
        self._receipt.apply_snapshot(snapshot, selected_request_id=selected)
        entry = resolve_orchestration_entry(orch, selected_request_id=selected)
        self._chain.apply_entry(entry)

    def _render_claims(
        self, claims: list[OrchestrationRunSnapshot | OrchestrationRunEntry]
    ) -> None:
        clear_children(self._claims_scroll)
        if not claims:
            ctk.CTkLabel(
                self._claims_scroll,
                text="No claims yet.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=12)
            return
        for entry in claims:
            rid = str(getattr(entry, "request_id", "") or "")
            ClaimCard(
                self._claims_scroll,
                request_id=rid,
                claim_text=claim_label(entry),
                truth_state=truth_state_for_entry(entry),
                receipt_id=str(getattr(entry, "receipt_id", "") or ""),
                selected=bool(rid and rid == self._selected_request_id),
                on_select=self._select,
            ).pack(fill="x", pady=3)

    def _select(self, request_id: str) -> None:
        rid = str(request_id).strip()
        self._selected_request_id = rid
        if self._on_select is not None:
            self._on_select(rid)
        entry = None
        if self._last_snap is not None:
            entry = resolve_orchestration_entry(
                self._last_snap.orchestration_run, selected_request_id=rid
            )
            self.apply_state(self._last_snap)
        if self._on_inspect_select is not None:
            payload = (
                ("request_id", rid),
                ("claim", claim_label(entry) if entry else rid),
                ("truth", truth_state_for_entry(entry) if entry else ""),
                ("receipt_id", str(getattr(entry, "receipt_id", "") or "")),
                ("trace_id", str(getattr(entry, "trace_id", "") or "")),
                ("span_id", str(getattr(entry, "span_id", "") or "")),
            )
            self._on_inspect_select(
                InspectableRef(
                    kind="evidence",
                    ref_id=rid or "evidence",
                    label=claim_label(entry) if entry else rid,
                    payload=payload,
                )
            )


__all__ = ["EvidenceView", "list_evidence_claims", "claim_label"]
