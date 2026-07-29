"""Brain / Situation panel — attention, reasoning, confidence, blockers."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.mission_control.modes import MissionMode, derive_mission_mode, mode_label
from ai_command_center.ui.views.surface_state import article18_empty


class BrainSituationPanel(GlassCard):
    """Tier-2 cognition panel — what the system is attending to and why."""

    _ROWS: tuple[str, ...] = (
        "Attention",
        "Reasoning",
        "Confidence",
        "Relevant Memories",
        "Prediction",
        "Blockers",
    )

    def __init__(self, master) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, border_color=T.REASONING_PURPLE)
        ctk.CTkLabel(
            self,
            text="Brain",
            font=T.FONT_HEADER,
            text_color=T.REASONING_PURPLE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._values: dict[str, ctk.CTkLabel] = {}
        for key in self._ROWS:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=T.PAD, pady=2)
            ctk.CTkLabel(
                row,
                text=key,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                width=130,
                anchor="w",
            ).pack(side="left")
            val = ctk.CTkLabel(
                row,
                text="—",
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            )
            val.pack(side="left", fill="x", expand=True)
            self._values[key] = val

        self._empty = ctk.CTkLabel(
            self,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=320,
        )
        self._empty.pack(fill="x", padx=T.PAD, pady=(4, T.PAD))

    def apply_state(self, snap: Any) -> None:
        if snap is None:
            for key in self._ROWS:
                self._values[key].configure(text="—")
            return

        mode = derive_mission_mode(snap)
        brain = getattr(snap, "brain_state", None)
        observations = list(getattr(brain, "recent_observations", ()) if brain else ())
        goals = list(getattr(brain, "recent_goals", ()) if brain else ())
        plan = getattr(brain, "last_plan", None) if brain else None
        actions = list(getattr(brain, "recent_runtime_actions", ()) if brain else ())

        attention = "Workspace"
        if goals:
            active = next(
                (g for g in goals if str(getattr(g, "status", "")) in {"active", "running", "queued"}),
                goals[0],
            )
            text = str(getattr(active, "text", "") or "")
            attention = text[:48] + ("…" if len(text) > 48 else "") if text else "Workspace"

        reasoning = {
            MissionMode.IDLE: "Standing by for the next mission",
            MissionMode.PLANNING: "Planning execution strategy",
            MissionMode.EXECUTING: "Supervising live execution",
            MissionMode.WAITING: "Awaiting approval or operator input",
            MissionMode.FAILURE: "Diagnosing failure and recovery options",
        }[mode]
        if plan and getattr(plan, "goal", ""):
            reasoning = f"{reasoning} · {getattr(plan, 'goal', '')}"[:72]

        confidences = [
            float(getattr(o, "confidence", 1.0) or 1.0) for o in observations
        ]
        if confidences:
            confidence = sum(confidences) / len(confidences)
            conf_pct = f"{int(confidence * 100)}%"
        else:
            conf_pct = "—"

        memory_count = len(observations)
        # Prefer notes/memory snapshot counts when present
        notes_mem = getattr(snap, "notes_memory", None) or getattr(snap, "memory_items", None)
        if notes_mem is not None:
            try:
                memory_count = len(notes_mem) if not isinstance(notes_mem, (str, bytes)) else memory_count
            except Exception:
                pass
        mem_snap = getattr(snap, "memory_library", None)
        if mem_snap is not None:
            items = getattr(mem_snap, "items", None) or getattr(mem_snap, "recent", None)
            if items is not None:
                memory_count = len(items)

        prediction = "—"
        execution_lib = getattr(snap, "execution_library", None)
        active = getattr(execution_lib, "active_plan", None) if execution_lib else None
        if active and getattr(active, "is_active", False):
            total = int(getattr(active, "total_steps", 0) or 0)
            done = len(getattr(active, "completed_steps", ()) or ())
            remaining = max(0, total - done)
            if total > 0:
                prediction = f"{done}/{total} steps complete · {remaining} remaining"
            else:
                prediction = "Execution in progress"
        elif mode == MissionMode.IDLE:
            prediction = "Ready for the next mission"
        elif mode == MissionMode.PLANNING:
            prediction = "Plan in progress"
        elif mode == MissionMode.WAITING:
            prediction = "Blocked on approval"
        elif mode == MissionMode.FAILURE:
            prediction = "Recovery required before resume"

        blockers = "None"
        permission = getattr(snap, "permission_snapshot", None)
        if permission and getattr(permission, "has_pending", False):
            pending = getattr(permission, "pending", None)
            summary = str(getattr(pending, "summary", "") or "Approval required")
            blockers = summary[:56]
        elif mode == MissionMode.FAILURE:
            err = str(getattr(active, "error", "") or "") if active else ""
            blockers = err[:56] if err else "Execution failure"

        self._values["Attention"].configure(text=attention)
        self._values["Reasoning"].configure(text=reasoning)
        self._values["Confidence"].configure(text=conf_pct)
        self._values["Relevant Memories"].configure(text=str(memory_count))
        self._values["Prediction"].configure(text=prediction)
        self._values["Blockers"].configure(
            text=blockers,
            text_color=T.STATUS_ERROR if blockers != "None" else T.TEXT_PRIMARY,
        )

        quiet = mode == MissionMode.IDLE and not goals and not actions and not observations
        if quiet:
            self._empty.configure(
                text=article18_empty(
                    why="Brain has no active attention target yet.",
                    creates="Attention, reasoning, and confidence appear when goals or observations arrive.",
                    next_action="Start a mission from the hero or open Chat.",
                )
            )
        else:
            self._empty.configure(text=f"Mode · {mode_label(mode)}")
