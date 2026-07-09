"""PR 7 polish — artifact stream UI component tests."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.core.state.artifact_state import ArtifactCatalogItem
from ai_command_center.ui.components.artifact_list_view import ArtifactListView
from ai_command_center.ui.components.execution_badge import ExecutionBadge
from ai_command_center.ui.views.chat.message_block import AssistantMessageBlock


def test_artifact_list_view_renders_cards() -> None:
    root = tk.Tk()
    root.withdraw()
    actions: list[tuple[str, str]] = []
    try:
        view = ArtifactListView(
            root,
            on_action=lambda aid, act: actions.append((aid, act)),
        )
        view.pack(fill="both", expand=True)
        view.set_artifacts(
            (
                ArtifactCatalogItem(
                    artifact_id="art-1",
                    kind="code",
                    label="Snippet",
                    content="print('hello')",
                    size_bytes=14,
                    request_id="req-1",
                ),
            )
        )
        root.update_idletasks()
        assert view.artifact_count() == 1
        cards = [w for w in view.winfo_children()]
        assert len(cards) == 1
    finally:
        root.destroy()


def test_assistant_message_block_set_artifacts_updates_strip() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(
            root,
            on_artifact_action=lambda _a, _k: None,
        )
        block.pack(fill="both", expand=True)
        block.finalize("Done.", execution_id="req-9", artifact_count=0)
        block.set_artifacts(
            (
                ArtifactCatalogItem(
                    artifact_id="art-9",
                    kind="text",
                    label="Output",
                    content="result",
                    request_id="req-9",
                ),
            )
        )
        root.update_idletasks()
        assert block._artifact_list is not None
        assert block._artifact_list.artifact_count() == 1
        assert block._action_strip is not None
    finally:
        root.destroy()


def test_execution_badge_invokes_inspect_select() -> None:
    root = tk.Tk()
    root.withdraw()
    selected = []
    try:
        badge = ExecutionBadge(
            root,
            execution_id="exec-42",
            execution_index=2,
            on_inspect_select=selected.append,
        )
        badge.pack()
        root.update_idletasks()
        badge.invoke()
        assert len(selected) == 1
        assert selected[0].kind == "execution"
        assert selected[0].ref_id == "exec-42"
    finally:
        root.destroy()
