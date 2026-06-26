"""Suggestion Engine (Reference Architecture v3.5, Part VII).

Suggestions minimize interaction cost and are produced **before AI reasoning** —
purely deterministic, rule-based matching over acquired context. Goal: reduce typing,
reduce routing friction, and avoid unnecessary AI invocation.

Example: clipboard context contains a Python traceback ->
    Explain Error / Create Issue / Search Notes / Save Snippet
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from ai_command_center.workspace.context_acquisition import AcquiredContext


@dataclass(frozen=True, slots=True)
class Suggestion:
    """A pre-AI proposed action shown to the user."""

    label: str
    command: str
    score: float
    source: str = "rule"


@dataclass(frozen=True, slots=True)
class SuggestionRule:
    """Deterministic rule: when ``matches`` holds, emit ``suggestions``."""

    name: str
    matches: Callable[[AcquiredContext], bool]
    suggestions: tuple[Suggestion, ...]


def _clipboard_text(context: AcquiredContext) -> str:
    value = context.value("clipboard")
    if value is None:
        for fragment in context.fragments:
            if isinstance(fragment.value, str):
                value = fragment.value
                break
    return value if isinstance(value, str) else ""


def _is_python_traceback(context: AcquiredContext) -> bool:
    text = _clipboard_text(context)
    return "Traceback (most recent call last)" in text


PYTHON_TRACEBACK_RULE = SuggestionRule(
    name="python_traceback",
    matches=_is_python_traceback,
    suggestions=(
        Suggestion("Explain Error", "explain_error", 0.95),
        Suggestion("Create Issue", "create_issue", 0.80),
        Suggestion("Search Notes", "search_notes", 0.70),
        Suggestion("Save Snippet", "save_snippet", 0.60),
    ),
)

DEFAULT_RULES: tuple[SuggestionRule, ...] = (PYTHON_TRACEBACK_RULE,)


class SuggestionEngine:
    """Generates ranked suggestions from context using deterministic rules.

    No AI, no side effects. Ordering is deterministic: by descending score, then
    label, then originating rule, so the same context always yields the same list.
    """

    def __init__(self, rules: Iterable[SuggestionRule] = DEFAULT_RULES) -> None:
        self._rules: list[SuggestionRule] = list(rules)

    def add_rule(self, rule: SuggestionRule) -> None:
        self._rules.append(rule)

    def suggest(self, context: AcquiredContext) -> tuple[Suggestion, ...]:
        collected: list[tuple[Suggestion, str]] = []
        for rule in self._rules:
            try:
                fired = rule.matches(context)
            except Exception:  # noqa: BLE001 - a bad rule must not break the engine
                continue
            if not fired:
                continue
            for suggestion in rule.suggestions:
                collected.append((suggestion, rule.name))
        collected.sort(key=lambda pair: (-pair[0].score, pair[0].label, pair[1]))
        return tuple(item[0] for item in collected)
