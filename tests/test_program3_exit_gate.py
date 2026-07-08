"""Program 3 exit gate — WII proof, grep audits, and pillar closure."""

from __future__ import annotations

import ast
import re
import sqlite3
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ai_command_center.application import create_application
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD, ENTITY_TYPE_WORKSPACE
from ai_command_center.core.event_bus import (
    EVENT_WORKSPACE_ACTIVATED,
    EVENT_WORKSPACE_CREATED,
    EVENT_WORKSPACE_DEACTIVATED,
    EVENT_WORKSPACE_LAYOUT_CHANGED,
    EventBus,
)
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    MEMORY_STORED,
    TIMELINE_RECORD_REQUEST,
    TOOL_INVOKE,
    UI_COMMAND,
    UI_SELECT_ENTITY,
    WORKSPACE_ACTIVATED,
    WORKSPACE_CREATED,
    WORKSPACE_DEACTIVATED,
    WORKSPACE_LAYOUT_CHANGED,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.events.topics import UI_OPEN_CHAT
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.conversation_repository import (
    DEFAULT_CONVERSATION_ID,
    ConversationRepository,
    entity_conversation_id,
)
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.session_service import SessionService
from ai_command_center.services.telemetry_service import TelemetryService
from ai_command_center.services.telemetry_summary import compute_session_summary
from ai_command_center.ui.controller import UIController

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PKG_ROOT = _REPO_ROOT / "ai_command_center"


def _drain_bus(bus: EventBus, timeout: float = 20.0) -> None:
    """Wait for async dispatch queue to finish (R4b tool.invoke cascade)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bus.dispatch_queue_depth == 0:
            time.sleep(0.08)
            if bus.dispatch_queue_depth == 0:
                return
        time.sleep(0.02)
    raise TimeoutError(f"EventBus dispatch queue not drained after {timeout}s")

# Production ui.command publishers — must merge workspace scope (not bypass UIController helper).
_UI_COMMAND_PUBLISH_ALLOWLIST = frozenset(
    {
        _PKG_ROOT / "ui" / "controller.py",
        _PKG_ROOT / "services" / "agent_runtime_service.py",
    }
)

# TOOL_INVOKE without workspace_context — documented opt-out (see contracts.py).
_TOOL_INVOKE_OPT_OUT = frozenset(
    {
        _REPO_ROOT / "tests",
        _REPO_ROOT / "scripts",
    }
)


def _find_ui_command_publish_sites() -> list[tuple[Path, int]]:
    pattern = re.compile(r"""\.publish\s*\(\s*(?:UI_COMMAND|"ui\.command")""")
    hits: list[tuple[Path, int]] = []
    for path in _PKG_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append((path, line_no))
    return hits


def _find_tool_invoke_without_workspace_context() -> list[tuple[Path, int]]:
    hits: list[tuple[Path, int]] = []
    for path in _PKG_ROOT.rglob("*.py"):
        if any(str(path).startswith(str(opt)) for opt in _TOOL_INVOKE_OPT_OUT):
            continue
        text = path.read_text(encoding="utf-8")
        if "TOOL_INVOKE" not in text and '"tool.invoke"' not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "publish"
                and isinstance(func.value, ast.Name)
            ):
                continue
            if not node.args:
                continue
            topic = node.args[0]
            topic_name = None
            if isinstance(topic, ast.Constant) and topic.value in ("tool.invoke",):
                topic_name = topic.value
            elif isinstance(topic, ast.Name) and topic.id == "TOOL_INVOKE":
                topic_name = "TOOL_INVOKE"
            if topic_name is None:
                continue
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Dict):
                continue
            keys = {
                k.value
                for k in node.args[1].keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            }
            if "workspace_context" not in keys:
                hits.append((path, node.lineno))
    return hits


def _compute_structural_wii(rows: list[dict]) -> float:
    """Pillar-weighted WII from integration session telemetry rows."""

    def _pct(scoped: int, total: int) -> float:
        return (scoped / total * 100.0) if total else 0.0

    cmd_total = cmd_scoped = 0
    mem_total = mem_scoped = 0
    ctx_total = ctx_scoped = 0
    tool_total = tool_scoped = 0
    session_non_default = 0
    session_total = 0

    for row in rows:
        event = row.get("event", "")
        payload = row.get("payload") or {}
        ws = str(payload.get("workspace_id", "")).strip()
        ent = str(
            payload.get("entity_id", "") or payload.get("workspace_entity_id", "")
        ).strip()
        scoped = bool(ws or ent)

        if event == COMMAND_ROUTED:
            cmd_total += 1
            if scoped:
                cmd_scoped += 1
        elif event == MEMORY_STORED:
            mem_total += 1
            if ws:
                mem_scoped += 1
        elif event in ("memory.lookup.request", "session.history.request"):
            ctx_total += 1
            if ws:
                ctx_scoped += 1
        elif event == TOOL_INVOKE:
            tool_total += 1
            ctx_raw = payload.get("workspace_context")
            if isinstance(ctx_raw, dict) and str(ctx_raw.get("workspace_id", "")).strip():
                tool_scoped += 1
        elif event == UI_COMMAND:
            session_total += 1
            cid = str(payload.get("conversation_id", "")).strip()
            if cid and cid != DEFAULT_CONVERSATION_ID:
                session_non_default += 1

    cmd_score = _pct(cmd_scoped, cmd_total)
    mem_score = _pct(mem_scoped, mem_total) if mem_total else 100.0
    ctx_score = _pct(ctx_scoped, ctx_total) if ctx_total else 100.0
    tool_score = _pct(tool_scoped, tool_total) if tool_total else 100.0
    sess_score = _pct(session_non_default, session_total) if session_total else 100.0

    return round(
        0.25 * cmd_score
        + 0.15 * mem_score
        + 0.20 * sess_score
        + 0.25 * ctx_score
        + 0.15 * tool_score,
        1,
    )


class ExitGateGrepAuditTests(unittest.TestCase):
    def test_ui_command_publish_sites_use_scope_allowlist(self) -> None:
        violations = [
            (path, line)
            for path, line in _find_ui_command_publish_sites()
            if path.resolve() not in {p.resolve() for p in _UI_COMMAND_PUBLISH_ALLOWLIST}
        ]
        self.assertEqual(
            [],
            violations,
            f"ui.command publish bypassing scope allowlist: {violations}",
        )

    def test_legacy_event_workspace_aliases_match_topics(self) -> None:
        self.assertEqual(EVENT_WORKSPACE_CREATED, WORKSPACE_CREATED)
        self.assertEqual(EVENT_WORKSPACE_ACTIVATED, WORKSPACE_ACTIVATED)
        self.assertEqual(EVENT_WORKSPACE_DEACTIVATED, WORKSPACE_DEACTIVATED)
        self.assertEqual(EVENT_WORKSPACE_LAYOUT_CHANGED, WORKSPACE_LAYOUT_CHANGED)

    def test_tool_invoke_without_workspace_context_limited_to_opt_out(self) -> None:
        prod_violations = _find_tool_invoke_without_workspace_context()
        self.assertEqual(
            [],
            prod_violations,
            f"TOOL_INVOKE missing workspace_context in production: {prod_violations}",
        )


class ExitGateSessionScopeTests(unittest.TestCase):
    def test_open_chat_without_entity_uses_workspace_not_default(self) -> None:
        bus = EventBus()
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        DatabaseBootstrapRepository().apply(conn)
        repo = ConversationRepository(conn)
        service = SessionService(bus, repo)
        service.load()
        try:
            ws_id = "ws-exit-gate"
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "Exit"},
                source="tests",
            )
            bus.publish(UI_OPEN_CHAT, {"entity_id": ""}, source="tests")
            expected = entity_conversation_id("workspace", ws_id)
            self.assertEqual(expected, service._active_conversation_id)
            self.assertNotEqual(DEFAULT_CONVERSATION_ID, service._active_conversation_id)
        finally:
            service.unload()
            conn.close()

    def test_resolve_conversation_id_prefers_active_workspace(self) -> None:
        bus = EventBus()
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        DatabaseBootstrapRepository().apply(conn)
        service = SessionService(bus, ConversationRepository(conn))
        service.load()
        try:
            ws_id = "ws-session-exit"
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "S"},
                source="tests",
            )
            cid = service._resolve_conversation_id({})
            self.assertEqual(entity_conversation_id("workspace", ws_id), cid)
            self.assertNotEqual(DEFAULT_CONVERSATION_ID, cid)
        finally:
            service.unload()
            conn.close()


class ExitGateCommandBoxEntityTests(unittest.TestCase):
    def test_publish_command_includes_selected_entity_scope(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        published: list[dict] = []
        bus.subscribe(UI_COMMAND, lambda e: published.append(dict(e.payload)))

        ws_id = "ws-cmdbox"
        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": ws_id, "title": "Cmd"},
            source="tests",
        )
        bus.publish(
            UI_SELECT_ENTITY,
            {
                "entity_id": "card-exit",
                "entity_type": ENTITY_TYPE_CARD,
                "title": "Selected",
                "workspace_id": ws_id,
            },
            source="tests",
        )
        controller.publish_command("summarize selection")

        self.assertEqual(1, len(published))
        payload = published[0]
        self.assertEqual(ws_id, payload.get("workspace_id"))
        self.assertEqual("card-exit", payload.get("workspace_entity_id"))
        self.assertEqual(ENTITY_TYPE_CARD, payload.get("workspace_entity_type"))


class ExitGateIntegrationTests(unittest.TestCase):
    def test_headless_round_trip_wii_meets_exit_gate(self) -> None:
        db_path = Path(":memory:")
        db = init_database(connect(db_path))
        app = create_application(debug_mode=False, workspace_os_enabled=True, db=db)
        app.startup()
        telemetry = app.services.get("telemetry")
        assert isinstance(telemetry, TelemetryService)
        repo = TelemetryRepository(db)
        try:
            ws = app.workspace_os.entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="Exit Gate",
            )
            card = app.workspace_os.entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Pillar Card",
            )
            active_id = str(ws.id)
            card_id = str(card.id)
            bus = app.bus

            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": active_id, "title": ws.title},
                source="tests",
            )
            bus.publish(
                UI_OPEN_CHAT,
                {
                    "entity_id": card_id,
                    "entity_type": ENTITY_TYPE_CARD,
                    "title": card.title,
                    "workspace_id": active_id,
                },
                source="tests",
            )

            commands = [
                {
                    "text": "hello workspace chat",
                    "workspace_id": active_id,
                    "workspace_entity_id": card_id,
                    "workspace_entity_type": ENTITY_TYPE_CARD,
                },
                {"text": "remember: exit | gate proof", "workspace_id": active_id},
                {
                    "text": "> echo exit-gate",
                    "workspace_id": active_id,
                    "workspace_entity_id": card_id,
                    "workspace_entity_type": ENTITY_TYPE_CARD,
                },
                {"text": "status check", "workspace_id": active_id},
            ]
            timeline_hits: list[dict] = []
            bus.subscribe(
                TIMELINE_RECORD_REQUEST,
                lambda e: timeline_hits.append(dict(e.payload)),
            )
            for cmd in commands:
                bus.publish(UI_COMMAND, cmd, source="tests")
            _drain_bus(bus)

            rows = repo.fetch_session(telemetry.session_id)
            row_dicts = [
                {
                    "event": row.event_type,
                    "timestamp": row.timestamp,
                    "payload": row.payload_dict(),
                }
                for row in rows
            ]
            summary = compute_session_summary(row_dicts)
            ratio = summary["workspace_scope"]["ratio_pct"]
            structural = _compute_structural_wii(row_dicts)

            self.assertGreaterEqual(ratio, 60.0, msg=f"telemetry ratio {ratio}")
            self.assertGreaterEqual(
                structural,
                60.0,
                msg=f"structural WII {structural}",
            )

            routed = [
                r.payload_dict()
                for r in rows
                if r.event_type == COMMAND_ROUTED
            ]
            self.assertTrue(routed)
            scoped_routed = sum(
                1
                for p in routed
                if str(p.get("workspace_id", "")).strip()
            )
            self.assertGreaterEqual(scoped_routed / len(routed), 0.6)

            mem_rows = db.execute("SELECT workspace_id FROM memory_nodes").fetchall()
            self.assertTrue(mem_rows)
            scoped_mem = sum(1 for r in mem_rows if str(r[0] or "").strip())
            self.assertGreaterEqual(scoped_mem / len(mem_rows), 0.6)

            tool_invokes = [r for r in rows if r.event_type == TOOL_INVOKE]
            if tool_invokes:
                self.assertTrue(
                    timeline_hits,
                    "tool.invoke with workspace scope should record timeline",
                )
        finally:
            app.shutdown()


class ExitGateToolTimelineTests(unittest.TestCase):
    def test_shell_tool_timeline_on_headless_invoke(self) -> None:
        db = init_database(connect(Path(":memory:")))
        app = create_application(debug_mode=False, workspace_os_enabled=True, db=db)
        app.startup()
        telemetry = app.services.get("telemetry")
        repo = TelemetryRepository(db)
        timeline_hits: list[dict] = []
        app.bus.subscribe(
            TIMELINE_RECORD_REQUEST,
            lambda e: timeline_hits.append(dict(e.payload)),
        )
        try:
            ws = app.workspace_os.entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="Tool WS",
            )
            active_id = str(ws.id)
            app.bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": active_id, "title": ws.title},
                source="tests",
            )
            app.bus.publish(
                UI_COMMAND,
                {
                    "text": "> echo timeline-proof",
                    "workspace_id": active_id,
                },
                source="tests",
            )
            _drain_bus(app.bus)
            rows = repo.fetch_session(telemetry.session_id)
            invokes = [r for r in rows if r.event_type == TOOL_INVOKE]
            self.assertTrue(invokes)
            ctx = invokes[0].payload_dict().get("workspace_context") or {}
            self.assertEqual(active_id, ctx.get("workspace_id"))
            self.assertTrue(timeline_hits)
            inner = (timeline_hits[0].get("payload") or {})
            self.assertEqual(active_id, inner.get("workspace_id"))
        finally:
            app.shutdown()


if __name__ == "__main__":
    unittest.main()
