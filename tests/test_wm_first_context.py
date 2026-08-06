"""WM-first context assembly (ADR-020 M2)."""

from __future__ import annotations

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.wm_first_context import (
    build_wm_first_context,
    build_wm_first_snippets,
)
from ai_command_center.domain.state_context import StateContext


def test_wm_snippets_precede_chat_history_in_prompt() -> None:
    cm = ContextManager(max_context_tokens=4000)
    state = StateContext(
        workspace_id="ws",
        summary="disk nearly full",
        entities=({"id": "n1", "type": "resource", "label": "logs"},),
    )
    bundle = build_wm_first_context(
        cm,
        "free space",
        state_context=state,
        observations=[
            {
                "step_id": "s1",
                "capability": "shell",
                "success": False,
                "error": "df failed",
            }
        ],
        conversation_history=[("user", "hello"), ("assistant", "hi there")],
    )
    assert "[world_model]" in bundle.prompt
    assert "disk nearly full" in bundle.prompt
    assert "[execution_observation]" in bundle.prompt
    # WM section should appear before truncated chat content markers
    wm_idx = bundle.prompt.find("[world_model]")
    hist_idx = bundle.prompt.find("hello")
    assert wm_idx != -1
    if hist_idx != -1:
        assert wm_idx < hist_idx


def test_build_wm_first_snippets_dedupes() -> None:
    state = StateContext(summary="same")
    snippets = build_wm_first_snippets(
        state_context=state,
        extra=["[world_model]\nsame", "extra"],
    )
    assert snippets.count("[world_model]\nsame") == 1
    assert "extra" in snippets
