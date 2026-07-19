#!/usr/bin/env python3
"""State Authority Verification Audit — live event-chain capture for six probes."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_AUTHORITY_DECISION,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    GOAL_SUBMIT_REQUEST,
    LLM_STEP_REQUEST,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
    PLAN_GENERATED,
    PLAN_REQUEST,
    RUNTIME_ACTION_REQUEST,
    STATE_CONTEXT_BUILT,
    TOOL_INVOKE,
    TOOL_RESULT,
    UI_COMMAND,
    UI_NAVIGATE,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.orchestration.state_capability_tools import bind_state_capability_tools
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.brain_runtime_service import BrainRuntimeService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.planner_service import PlannerService
from ai_command_center.services.state_authority_service import StateAuthorityService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry

WATCH = (
    STATE_CONTEXT_BUILT,
    EXECUTION_AUTHORITY_DECISION,
    GOAL_SUBMIT_REQUEST,
    PLAN_REQUEST,
    PLAN_GENERATED,
    EXECUTION_RUN_REQUEST,
    TOOL_INVOKE,
    TOOL_RESULT,
    LLM_STEP_REQUEST,
    UI_NAVIGATE,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
    RUNTIME_ACTION_REQUEST,
)


class _Notes:
    def create_note(self, body: str) -> tuple[bool, str, str]:
        path = "Inbox/Quick-audit.md"
        return True, f"created note {path}", path

    def search_notes(self, query: str) -> tuple[bool, str, list[dict[str, str]]]:
        return True, "found 0 notes", []


class _Memory:
    def store_memory(
        self, body: str, *, workspace_id: str = "", entity_id: str = ""
    ) -> tuple[bool, str, dict[str, Any]]:
        label = body.split("|", 1)[0].strip() if "|" in body else body.split(" ", 1)[0]
        return True, f"stored memory {label}", {
            "id": "mem-1",
            "label": label,
            "content": body,
            "workspace_id": workspace_id,
        }

    def query_memory(
        self, query: str, *, workspace_id: str = "", entity_id: str = ""
    ) -> tuple[bool, str, list[dict[str, Any]]]:
        return True, "found 0", []

    def lookup_for_state(self, query: str, *, workspace_id: str = "") -> list[dict]:
        return []


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


def _wire(bus: EventBus) -> WorldModel:
    registry = ToolRegistry()
    notes = _Notes()
    memory = _Memory()
    bind_state_capability_tools(registry, bus=bus, notes=notes, memory=memory)
    registry.register_tool(
        ToolSpec(
            name="launch_application",
            description="launch",
            handler=lambda args: ToolResult(
                success=str(args.get("application")) == "calculator",
                output=(
                    f"Opened {args.get('application')}."
                    if str(args.get("application")) == "calculator"
                    else ""
                ),
                error=(
                    None
                    if str(args.get("application")) == "calculator"
                    else f"unsupported application: {args.get('application')}"
                ),
            ),
        )
    )
    ToolExecutorService(bus, registry).start()
    wm = WorldModel(SQLiteWorldModelRepository(_conn()))
    BrainRuntimeService(bus, wm).start()
    StateAuthority = StateAuthorityService(
        bus, wm, memory_lookup=memory.lookup_for_state
    )
    StateAuthority.start()
    SingleGoalScheduler(bus, GoalRepository(_conn())).start()
    PlannerService(bus, context_manager=ContextManager()).start()
    ExecutionOrchestratorService(bus).start()
    OrchestrationService(bus).start()
    ExecutionAuthorityService(bus, state_authority=StateAuthority).start()
    ChatHandlerService(bus, ContextManager()).start()
    return wm


def _summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"event_chain": [e["topic"] for e in events]}
    for e in events:
        t = e["topic"]
        p = e["payload"]
        if t == STATE_CONTEXT_BUILT:
            out["state_context"] = {
                "summary": p.get("summary"),
                "entity_count": len(p.get("entities") or []),
                "memory_count": len(p.get("memories") or []),
                "goal_count": len(p.get("goals") or []),
                "query_text": p.get("query_text"),
                "workspace_id": p.get("workspace_id"),
            }
            out["world_model_queries"] = {
                "mechanism": "StateAuthorityService.project → WorldModel.iter_cached_nodes + get_edges + optional memory_lookup/goal_lookup",
                "entities_returned": len(p.get("entities") or []),
                "relationships_returned": len(p.get("relationships") or []),
            }
        elif t == EXECUTION_AUTHORITY_DECISION:
            out["authority_decision"] = {
                "kind": p.get("kind"),
                "capability": p.get("capability"),
                "reason": p.get("reason"),
                "skip_planner": p.get("skip_planner"),
                "args": p.get("args"),
            }
        elif t == GOAL_SUBMIT_REQUEST:
            plan = p.get("plan")
            out["goal_submit"] = {
                "planner_mode": p.get("planner_mode"),
                "has_plan": isinstance(plan, dict) and bool(plan.get("steps")),
                "workspace_snippets_count": len(p.get("workspace_snippets") or []),
            }
            if isinstance(plan, dict):
                out["execution_plan"] = plan
        elif t == PLAN_GENERATED:
            out["execution_plan"] = p.get("plan")
            out["planner_mode"] = p.get("planner_mode")
        elif t == EXECUTION_RUN_REQUEST:
            out["execution_run"] = {
                "run_id": p.get("run_id"),
                "request_id": p.get("request_id"),
                "plan_steps": [
                    s.get("capability")
                    for s in (p.get("plan") or {}).get("steps") or []
                    if isinstance(s, dict)
                ],
            }
        elif t == TOOL_INVOKE:
            out.setdefault("tool_invokes", []).append(
                {"tool": p.get("tool"), "args": p.get("args"), "source": e.get("source")}
            )
        elif t == LLM_STEP_REQUEST:
            out["llm_step"] = {
                "capability": p.get("capability"),
                "prompt": (p.get("args") or {}).get("prompt"),
            }
        elif t == UI_NAVIGATE:
            out["ui_navigate"] = p
        elif t == ORCHESTRATION_RECEIPT:
            out["receipt"] = {
                "receipt_id": p.get("receipt_id"),
                "success": p.get("success"),
                "intent": p.get("intent"),
                "provider_id": p.get("provider_id"),
                "error": p.get("error"),
            }
        elif t == ORCHESTRATION_TRUTH_VALIDATED:
            out["truth_validation"] = {
                "valid": p.get("valid"),
                "detail": p.get("detail"),
                "response_source": p.get("response_source"),
            }
        elif t == RUNTIME_ACTION_REQUEST:
            mut = p.get("mutation") or {}
            node = (mut.get("payload") or {}).get("node") or {}
            out.setdefault("world_model_mutations", []).append(
                {
                    "mutation_type": mut.get("type"),
                    "node_id": node.get("id"),
                    "node_type": node.get("type"),
                    "attributes": node.get("attributes"),
                }
            )
        elif t in (EXECUTION_RUN_COMPLETE, EXECUTION_RUN_FAILED):
            out["run_terminal"] = {"topic": t, "success": p.get("success"), "error": p.get("error")}
    return out


def main() -> int:
    probes = [
        "note: project alpha starts monday",
        "remember: preferred_editor | VS Code",  # canonical prefix form of "remember my preferred editor..."
        "remember my preferred editor is VS Code",  # natural-language probe (may classify as llm/memory)
        "navigate dashboard",  # natural language — may not match go/alias
        "go dashboard",  # canonical navigate (dashboard may alias to home)
        "open chrome",
        "what is recursion",
        "prepare for tomorrow's customer meeting",
    ]
    # User's exact six + note on NL variants after
    user_probes = [
        "note: project alpha starts monday",
        "remember: preferred_editor | VS Code",
        "go home",  # closest canonical to navigate dashboard
        "open chrome",
        "what is recursion",
        "prepare for tomorrow's customer meeting",
    ]
    # Also run exact user strings for honesty
    exact = [
        "note: project alpha starts monday",
        "remember my preferred editor is VS Code",
        "navigate dashboard",
        "open chrome",
        "what is recursion",
        "prepare for tomorrow's customer meeting",
    ]

    results: dict[str, Any] = {"exact_user_strings": [], "canonical_equivalents": []}

    for label, probeset in (
        ("exact_user_strings", exact),
        ("canonical_equivalents", user_probes),
    ):
        bus = EventBus()
        _wire(bus)
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-audit", "title": "Audit"}, source="audit")
        for text in probeset:
            captured: list[dict[str, Any]] = []

            def make_cap(bucket: list[dict[str, Any]]):
                def _cap(event) -> None:
                    if event.topic in WATCH:
                        bucket.append(
                            {
                                "topic": event.topic,
                                "source": event.source,
                                "payload": dict(event.payload),
                            }
                        )

                return _cap

            unsubs = [bus.subscribe(t, make_cap(captured)) for t in WATCH]
            bus.publish(
                UI_COMMAND,
                {"text": text, "workspace_id": "ws-audit"},
                source="ui",
            )
            for u in unsubs:
                u()
            results[label].append({"text": text, **_summarize(captured)})

    out_path = Path("/tmp/state_authority_verification_audit.json")
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(out_path)
    # Compact stdout summary
    for item in results["exact_user_strings"]:
        print("---")
        print("TEXT:", item["text"])
        print("CHAIN:", " → ".join(item["event_chain"]))
        print("DECISION:", item.get("authority_decision"))
        print("PLAN:", (item.get("execution_plan") or {}).get("steps") if isinstance(item.get("execution_plan"), dict) else item.get("execution_plan"))
        print("RECEIPT:", item.get("receipt"))
        print("TRUTH:", item.get("truth_validation"))
        print("MUTATIONS:", item.get("world_model_mutations"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
