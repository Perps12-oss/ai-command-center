"""CapabilitySelector — filter catalog by StateContext before planner sees it."""

from __future__ import annotations

import re
from typing import Any

from ai_command_center.capabilities.definition import CapabilityDefinition
from ai_command_center.capabilities.registry import CapabilityRegistry
from ai_command_center.domain.state_context import StateContext

_TOKEN_RE = re.compile(r"[a-z0-9_.]{2,}", re.IGNORECASE)

# Always include these so free-text goals never see an empty catalog.
_ALWAYS: frozenset[str] = frozenset(
    {
        "llm.chat",
        "llm.generate",
        "notes.create",
        "notes.search",
        "memory.store",
        "memory.query",
        "goals.plan",
        "navigate",
    }
)

_HINT_DOMAINS: list[tuple[re.Pattern[str], frozenset[str]]] = [
    (re.compile(r"\b(note|notes|vault|obsidian)\b", re.I), frozenset({"notes"})),
    (re.compile(r"\b(remember|memory|preference)\b", re.I), frozenset({"memory"})),
    (re.compile(r"\b(open|launch|start|app|application|chrome|calc)\b", re.I), frozenset({"applications"})),
    (re.compile(r"\b(goal|prepare|plan|organize)\b", re.I), frozenset({"goals", "tasks", "reasoning"})),
    (re.compile(r"\b(calendar|meeting|schedule|availability)\b", re.I), frozenset({"calendar"})),
    (re.compile(r"\b(file|folder|spreadsheet|document)\b", re.I), frozenset({"files", "search"})),
    (re.compile(r"\b(workflow|automat)\b", re.I), frozenset({"workflow", "automation"})),
    (re.compile(r"\b(agent|research|delegate)\b", re.I), frozenset({"agent", "knowledge"})),
    (re.compile(r"\b(navigate|go to|dashboard|settings)\b", re.I), frozenset({"system"})),
]


class CapabilitySelector:
    """Projects a relevant capability subset from StateContext + goal text."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def select(
        self,
        *,
        goal: str = "",
        state_context: StateContext | None = None,
        max_capabilities: int = 16,
    ) -> list[CapabilityDefinition]:
        visible = self._registry.list_planner_visible()
        by_id = {c.id: c for c in visible}
        selected: dict[str, CapabilityDefinition] = {}

        for cap_id in _ALWAYS:
            if cap_id in by_id:
                selected[cap_id] = by_id[cap_id]

        domains: set[str] = set()
        text = goal or (state_context.query_text if state_context else "")
        for pattern, domain_set in _HINT_DOMAINS:
            if pattern.search(text):
                domains.update(domain_set)

        if state_context:
            for entity in state_context.entities:
                etype = str(entity.get("type") or "").lower()
                if etype in {"note", "memory", "goal", "task", "application", "workspace"}:
                    domains.add("notes" if etype == "note" else etype if etype != "application" else "applications")
                    if etype == "goal":
                        domains.add("goals")
                    if etype == "task":
                        domains.add("tasks")

        for cap in visible:
            if cap.domain in domains or cap.id in selected:
                selected[cap.id] = cap

        # Ensure launch alias when applications domain hinted.
        if "applications" in domains and "launch_application" in by_id:
            selected["launch_application"] = by_id["launch_application"]
            if "applications.launch" in by_id:
                selected["applications.launch"] = by_id["applications.launch"]

        result = list(selected.values())
        if len(result) > max_capabilities:
            # Prefer always-set, then domain matches.
            always = [c for c in result if c.id in _ALWAYS]
            rest = [c for c in result if c.id not in _ALWAYS]
            result = (always + rest)[:max_capabilities]
        if not result:
            # Hard fallback — never return empty for planner.
            result = [by_id[i] for i in ("llm.chat", "llm.generate") if i in by_id]
        return result

    def to_prompt_specs(
        self,
        *,
        goal: str = "",
        state_context: StateContext | None = None,
        max_capabilities: int = 16,
    ) -> list[dict[str, Any]]:
        return [
            c.to_prompt_spec()
            for c in self.select(
                goal=goal,
                state_context=state_context,
                max_capabilities=max_capabilities,
            )
        ]
