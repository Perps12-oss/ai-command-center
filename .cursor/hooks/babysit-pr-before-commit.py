#!/usr/bin/env python3
"""Cursor hook: remind agents that babysit-PR is the default before commit/push."""

from __future__ import annotations

import json
import re
import sys

_BABYSIT_REMINDER = (
    "Default PR workflow (mandatory): babysit until merge-ready. "
    "Before commit: if this branch has an open PR, triage unresolved comments "
    "and latest CI. After push: follow ~/.cursor/skills-cursor/babysit/SKILL.md — "
    "resolve comments, merge conflicts, fix in-scope CI failures, re-watch until "
    "mergeable + green. Local and Cloud agents both default to this; Cloud may use "
    "a background Cloud subagent for long CI loops without waiting for user request."
)

_GIT_COMMIT = re.compile(r"\bgit\s+commit\b")
_GIT_PUSH = re.compile(r"\bgit\s+push\b")
_GH_PR = re.compile(r"\bgh\s+pr\s+(create|edit|ready|merge)\b")


def allow(message: str = "") -> None:
    payload: dict[str, str] = {"permission": "allow"}
    if message:
        payload["agent_message"] = message
    print(json.dumps(payload))
    raise SystemExit(0)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        allow()

    command = str(data.get("command", ""))
    if not (_GIT_COMMIT.search(command) or _GIT_PUSH.search(command) or _GH_PR.search(command)):
        allow()

    allow(_BABYSIT_REMINDER)


if __name__ == "__main__":
    main()
