#!/usr/bin/env python3
"""Workspace OS Phase 4 gate — Action Architecture (v3.5 Part VI)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 4 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        ActionDispatcher,
        ActionResult,
        CallableTarget,
        CreateNote,
        LaunchApplication,
        OpenFile,
        OutputTarget,
        RunCommand,
        TextInsertion,
    )

    # 1. Standard action types exist, subclass ActionResult, and are frozen.
    sample = TextInsertion(text="hello")
    for action_cls in (TextInsertion, OpenFile, LaunchApplication, RunCommand, CreateNote):
        if not issubclass(action_cls, ActionResult):
            failures.append(f"{action_cls.__name__} must subclass ActionResult")
    if not isinstance(sample, ActionResult):
        failures.append("TextInsertion instance is not an ActionResult")
    try:
        sample.text = "tamper"  # type: ignore[misc]
        failures.append("ActionResult subclasses must be frozen")
    except dataclasses.FrozenInstanceError:
        pass

    # 2. OutputTarget.dispatch is an interface (NotImplementedError by default).
    try:
        OutputTarget().dispatch(sample)
        failures.append("OutputTarget.dispatch should raise NotImplementedError")
    except NotImplementedError:
        pass

    # 3. Dispatcher routes to the first accepting target (deterministic order).
    delivered: list[str] = []
    note_target = CallableTarget(
        CreateNote, lambda r: delivered.append("note") or True, name="ObsidianTarget"
    )
    text_target = CallableTarget(
        TextInsertion, lambda r: delivered.append("text") or True, name="SendInputTarget"
    )
    dispatcher = ActionDispatcher([note_target, text_target])

    outcome = dispatcher.dispatch(TextInsertion(text="hi"))
    if not (outcome.accepted and outcome.success and outcome.target == "SendInputTarget"):
        failures.append("dispatch should route TextInsertion to SendInputTarget")
    if delivered != ["text"]:
        failures.append("only the accepting target should run")

    # 4. No accepting target -> not accepted, no execution.
    none_outcome = dispatcher.dispatch(RunCommand(command="ls"))
    if none_outcome.accepted or none_outcome.success:
        failures.append("RunCommand has no target; should be unaccepted")

    # 5. A target raising is isolated and reported, not propagated.
    boom = ActionDispatcher(
        [CallableTarget(OpenFile, lambda r: (_ for _ in ()).throw(OSError("locked")))]
    )
    boom_outcome = boom.dispatch(OpenFile(path=Path("/tmp/x")))
    if not (boom_outcome.accepted and not boom_outcome.success and boom_outcome.error):
        failures.append("target failure should be isolated and recorded")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 4 — action architecture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
