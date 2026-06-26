#!/usr/bin/env python3
"""Workspace OS Phase 9 gate — AI Reasoning Subsystem (v3.5 Part X)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 9 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        CallableReasoningEngine,
        ReasoningEngine,
        ReasoningRequest,
        ReasoningResponse,
        ReasoningTask,
        Suggestion,
        TelemetrySnapshot,
        TextInsertion,
        WorkspaceContext,
    )

    # 1. Bounded responsibilities are enumerated (and only those).
    tasks = {t.value for t in ReasoningTask}
    expected = {
        "summarization",
        "classification",
        "transformation",
        "planning",
        "context_expansion",
    }
    if tasks != expected:
        failures.append(f"ReasoningTask should be exactly {expected}, got {tasks}")

    ctx = WorkspaceContext(
        workspace_id="ws-1",
        title="t",
        inferred_task="summarize",
        active_snapshot=TelemetrySnapshot.empty(now=0.0),
    )

    # 2. Inputs are WorkspaceContext + Intent + Retrieved Knowledge (no state ownership).
    request = ReasoningRequest(
        context=ctx,
        intent="summarize_clipboard",
        task=ReasoningTask.SUMMARIZATION,
        retrieved_knowledge=("doc-a", "doc-b"),
    )
    if request.context is not ctx or request.retrieved_knowledge != ("doc-a", "doc-b"):
        failures.append("ReasoningRequest should carry context + intent + knowledge")

    # 3. Engine is an injectable boundary; base raises (no built-in model).
    try:
        ReasoningEngine().reason(request)
        failures.append("ReasoningEngine.reason should be an interface (NotImplementedError)")
    except NotImplementedError:
        pass

    # 4. Outputs are limited to ActionResults / structured responses / suggestions.
    def handler(req: ReasoningRequest) -> ReasoningResponse:
        return ReasoningResponse(
            structured_response="summary text",
            action_results=(TextInsertion(text="summary text"),),
            suggestions=(Suggestion("Save Snippet", "save_snippet", 0.6),),
        )

    engine = CallableReasoningEngine(handler)
    resp = engine.reason(request)
    if resp.structured_response != "summary text":
        failures.append("engine should return a structured response")
    if not (resp.action_results and isinstance(resp.action_results[0], TextInsertion)):
        failures.append("engine output should include ActionResults")
    if not resp.suggestions:
        failures.append("engine output may include suggestions")

    # 5. Boundary: ReasoningResponse exposes no execution/persistence/routing surface.
    forbidden = {"execute", "dispatch", "persist", "save", "route"}
    leaked = forbidden.intersection(dir(resp))
    if leaked:
        failures.append(f"reasoning output must not own execution/persistence: {leaked}")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 9 — AI reasoning subsystem")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
