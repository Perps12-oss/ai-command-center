"""Pre-commit verification suite for P0 inspector + artifact migration fixes."""

from __future__ import annotations

import re
import sqlite3
import tempfile
from pathlib import Path

import pytest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATED,
    CHAT_COMPLETE,
    UI_INSPECT_SELECT,
)
from ai_command_center.domain.artifact import Artifact
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
    _MIGRATIONS,
)
from ai_command_center.services.artifact_service import ArtifactService

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)


@pytest.fixture(scope="module")
def tk_root():
    """Single Tk root for the module — Windows Tcl cannot handle rapid create/destroy."""
    try:
        root = tk.Tk()
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"tkinter display unavailable: {exc}")
    root.withdraw()
    yield root
    root.destroy()


from ai_command_center.ui.components.inspector import InspectorHost
from ai_command_center.ui.components.inspector.chat_inspector import ChatInspector
from ai_command_center.ui.ui_queue import UIQueue

_EXPECTED_ARTIFACT_COLUMNS = frozenset(
    {
        "artifact_id",
        "kind",
        "label",
        "content",
        "size_bytes",
        "mime_type",
        "request_id",
        "workspace_id",
        "entity_id",
        "source",
        "created_at",
        "updated_at",
    }
)

_INSPECTOR_SCAN_ROOTS = (
    Path("ai_command_center/ui/components/inspector"),
    Path("ai_command_center/ui/views/chat"),
    Path("ai_command_center/ui/shell/state_applier.py"),
)

_BAD_PAYLOAD_PATTERNS = (
    re.compile(r"\bref\.payload\.get\("),
    re.compile(r"\binspect_ref\.payload\.get\("),
    re.compile(r"\bref\.payload\["),
    re.compile(r"\binspect_ref\.payload\["),
)


def _bootstrap_to_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
    )
    for v, fn in sorted(_MIGRATIONS, key=lambda item: item[0]):
        if v > version:
            break
        fn(conn)
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (v,)
        )
    conn.commit()


def _artifact_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(artifacts)").fetchall()
    return {str(row[1]) for row in rows}


@pytest.mark.parametrize("start_version", [5, 6, 7])
def test_migration_upgrade_from_v5_v6_v7_has_full_artifacts_schema(
    start_version: int,
) -> None:
    """Check 1: upgrade legacy DBs at v5/v6/v7 to current schema."""
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(Path(tmp) / f"v{start_version}.db")
        try:
            _bootstrap_to_version(conn, start_version)
            if start_version < 7:
                assert conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='artifacts'"
                ).fetchone() is None

            DatabaseBootstrapRepository().apply(conn)
            cols = _artifact_columns(conn)
            assert _EXPECTED_ARTIFACT_COLUMNS <= cols

            version_row = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()
            assert version_row is not None
            assert int(version_row[0]) == max(v for v, _ in _MIGRATIONS)
        finally:
            conn.close()


def test_migration_v7_legacy_artifacts_table_gains_content_column() -> None:
    """Check 1 extension: v7 DB with pre-v7 artifacts table missing content."""
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(Path(tmp) / "legacy_v7.db")
        try:
            _bootstrap_to_version(conn, 7)
            conn.execute("DROP TABLE IF EXISTS artifacts")
            conn.execute(
                """
                CREATE TABLE artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    label TEXT NOT NULL
                )
                """
            )
            conn.commit()

            DatabaseBootstrapRepository().apply(conn)
            cols = _artifact_columns(conn)
            assert "content" in cols
            assert _EXPECTED_ARTIFACT_COLUMNS <= cols
        finally:
            conn.close()


def test_inspector_ref_get_contract_for_all_selection_kinds() -> None:
    """Check 2 (headless): InspectableRef.get() for user/assistant/artifact/tool."""
    cases: tuple[tuple[str, dict], ...] = (
        (
            "user_message",
            {
                "kind": "message",
                "ref_id": "msg-user",
                "label": "User",
                "payload": {"role": "user", "content": "Hello", "index": "0"},
            },
        ),
        (
            "assistant_message",
            {
                "kind": "message",
                "ref_id": "msg-asst",
                "label": "Assistant",
                "payload": {
                    "role": "assistant",
                    "content": "# Answer\nDone.",
                    "index": "1",
                },
            },
        ),
        (
            "artifact",
            {
                "kind": "artifact",
                "ref_id": "art-1",
                "label": "Chat artifact",
                "payload": {
                    "artifact_id": "art-1",
                    "kind": "markdown",
                    "content": "Artifact body",
                    "request_id": "req-1",
                },
            },
        ),
        (
            "tool_execution",
            {
                "kind": "execution",
                "ref_id": "exec-1",
                "label": "shell",
                "payload": {
                    "execution_id": "exec-1",
                    "tool_name": "shell",
                    "status": "success",
                    "output": "echo hello",
                },
            },
        ),
    )

    for label, payload in cases:
        ref = InspectableRef.from_payload(payload)
        assert ref.kind == payload["kind"]
        assert isinstance(ref.payload, tuple)
        assert ref.as_dict()
        if label in {"user_message", "assistant_message", "artifact"}:
            assert ref.get("content")
        else:
            assert ref.get("tool_name") == "shell"
            assert ref.get("output") == "echo hello"


def test_inspector_widgets_update_for_all_selection_kinds(tk_root: tk.Tk) -> None:
    """Check 2 (UI): InspectorHost + ChatInspector accept every selection kind."""
    cases: tuple[dict, ...] = (
        {
            "kind": "message",
            "ref_id": "msg-user",
            "label": "User",
            "payload": {"role": "user", "content": "Hello", "index": "0"},
        },
        {
            "kind": "message",
            "ref_id": "msg-asst",
            "label": "Assistant",
            "payload": {
                "role": "assistant",
                "content": "# Answer\nDone.",
                "index": "1",
            },
        },
        {
            "kind": "artifact",
            "ref_id": "art-1",
            "label": "Chat artifact",
            "payload": {
                "artifact_id": "art-1",
                "kind": "markdown",
                "content": "Artifact body",
                "request_id": "req-1",
            },
        },
        {
            "kind": "execution",
            "ref_id": "exec-1",
            "label": "shell",
            "payload": {
                "execution_id": "exec-1",
                "tool_name": "shell",
                "status": "success",
                "output": "echo hello",
            },
        },
    )

    root = tk_root
    host = InspectorHost(root)
    host.pack(fill="both", expand=True)
    chat_inspector = ChatInspector(root)
    chat_inspector.pack(fill="both", expand=True)

    for payload in cases:
        ref = InspectableRef.from_payload(payload)
        host.show(ref)
        chat_inspector.update_selected_message(ref)
        root.update_idletasks()


def test_inspector_source_files_avoid_tuple_payload_dict_access() -> None:
    """Check 2 guard: no direct .payload.get / .payload[...] in inspector paths."""
    repo_root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for rel in _INSPECTOR_SCAN_ROOTS:
        path = repo_root / rel
        files = [path] if path.is_file() else sorted(path.rglob("*.py"))
        for file_path in files:
            text = file_path.read_text(encoding="utf-8")
            for pattern in _BAD_PAYLOAD_PATTERNS:
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    violations.append(f"{file_path.relative_to(repo_root)}:{line}")
    assert not violations, "tuple payload misuse:\n" + "\n".join(violations)


def test_ui_queue_survives_rapid_inspector_callbacks(
    event_bus: EventBus, tk_root: tk.Tk
) -> None:
    """Check 3: rapid inspector selection + queue drain must not raise."""
    store = AppStateStore(event_bus)
    root = tk_root
    ui_queue = UIQueue(root)
    chat_inspector = ChatInspector(root)

    def apply_inspector() -> None:
        snap = store.snapshot
        selected = snap.inspector.selected
        if selected is not None:
            chat_inspector.update_selected_message(selected)
            _ = selected.get("content")

    selections = [
        {
            "kind": "message",
            "ref_id": f"msg-{i}",
            "label": f"Message {i}",
            "payload": {"role": "assistant", "content": f"Body {i}", "index": str(i)},
        }
        for i in range(20)
    ] + [
        {
            "kind": "artifact",
            "ref_id": "art-churn",
            "label": "Artifact",
            "payload": {"artifact_id": "art-churn", "content": "artifact body"},
        },
        {
            "kind": "execution",
            "ref_id": "exec-churn",
            "label": "shell",
            "payload": {"tool_name": "shell", "output": "done"},
        },
    ]
    for payload in selections:
        event_bus.publish(UI_INSPECT_SELECT, payload, source="tests")
        ui_queue.enqueue(apply_inspector)

    root.update_idletasks()
    root.update()


def test_chat_complete_artifact_persist_and_inspect_select(
    event_bus: EventBus, tk_root: tk.Tk
) -> None:
    """Check 4: CHAT_COMPLETE -> persisted artifact -> inspector selection."""
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(Path(tmp) / "e2e.db")
        conn.row_factory = sqlite3.Row
        DatabaseBootstrapRepository().apply(conn)
        repo = ArtifactRepository(conn)
        service = ArtifactService(event_bus, repo=repo)
        store = AppStateStore(event_bus)

        created: list[dict] = []
        event_bus.subscribe(ARTIFACT_CREATED, lambda e: created.append(dict(e.payload)))

        try:
            service.start()
            event_bus.publish(
                CHAT_COMPLETE,
                {"request_id": "req-e2e", "text": "# Answer\nPersisted."},
                source="test",
            )
            service.stop()

            assert created
            artifact_id = str(created[0]["artifact_id"])
            loaded = repo.get(artifact_id)
            assert loaded is not None
            assert loaded.content

            event_bus.publish(
                UI_INSPECT_SELECT,
                {
                    "kind": "artifact",
                    "ref_id": artifact_id,
                    "label": loaded.label,
                    "payload": {
                        "artifact_id": artifact_id,
                        "kind": loaded.kind,
                        "content": loaded.content,
                        "request_id": loaded.request_id,
                    },
                },
                source="tests",
            )
            ref = store.snapshot.inspector.selected
            assert ref is not None
            assert ref.get("content") == loaded.content

            inspector = ChatInspector(tk_root)
            inspector.update_selected_message(ref)
            host = InspectorHost(tk_root)
            host.show(ref)
            tk_root.update_idletasks()
        finally:
            conn.close()
