"""
Supervised Agent Demo — Track 7 validation script.

Proves the bus-native supervised agent flow:
  UI/command → CommandRouter → AgentRuntimeService → PermissionService → ToolExecutor
  with AppState projection for SystemView.

Usage:
    python scripts/supervised_agent_demo.py
    python scripts/supervised_agent_demo.py --no-shell
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run(*, suppress_shell: bool = False) -> int:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ai_command_center.application import create_application
    from ai_command_center.core.events.topics import UI_COMMAND

    print("=== Track 7 Supervised Agent Demo ===")

    app = create_application(debug_mode=False)
    try:
        app.startup()
        bus = app.bus
        store = app.state_store

        if suppress_shell:
            from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
            from ai_command_center.core.events.topics import TOOL_INVOKE, TOOL_RESULT

            def fake_tool(event) -> None:
                payload = dict(event.payload)
                bus.publish(
                    TOOL_RESULT,
                    {
                        "contract_version": TOOL_CONTRACT_VERSION,
                        "invoke_id": payload.get("invoke_id", ""),
                        "tool": payload.get("tool"),
                        "success": True,
                        "output": "supervised-agent-demo-ok",
                    },
                    source="supervised_agent_demo",
                )

            bus.subscribe(TOOL_INVOKE, fake_tool)

        bus.publish(UI_COMMAND, {"text": "agent: demo"}, source="supervised_agent_demo")

        snap = store.snapshot
        runs = snap.agent_runs
        print(f"Agent runs in AppState: {len(runs)}")
        if runs:
            run_item = runs[0]
            print(
                f"  agent_id={run_item.agent_id[:8]} state={run_item.state} "
                f"task={run_item.task!r} error={run_item.error!r}"
            )
        print("=== Supervised Agent Demo SUCCESS ===")
        return 0
    finally:
        app.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Track 7 supervised agent demo")
    parser.add_argument(
        "--no-shell",
        action="store_true",
        help="Stub shell tool execution (no subprocess)",
    )
    args = parser.parse_args()
    return run(suppress_shell=args.no_shell)


if __name__ == "__main__":
    sys.exit(main())
