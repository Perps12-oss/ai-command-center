"""WM-first context assembly helpers (ADR-020 M2).

Callers supply World Model / receipt / observation snippets; ContextManager
remains a budget adapter and never accesses storage.
"""

from __future__ import annotations

from typing import Any, Sequence

from ai_command_center.core.context_manager import ContextBundle, ContextManager
from ai_command_center.domain.state_context import StateContext


def observation_snippets(observations: Sequence[Any], *, limit: int = 8) -> list[str]:
    snippets: list[str] = []
    for item in list(observations)[-limit:]:
        if not isinstance(item, dict):
            continue
        snippets.append(
            "[execution_observation] "
            f"step={item.get('step_id')} cap={item.get('capability')} "
            f"ok={item.get('success')} err={item.get('error', '')}"
        )
    return snippets


def receipt_snippets(receipts: Sequence[Any], *, limit: int = 5) -> list[str]:
    snippets: list[str] = []
    for item in list(receipts)[-limit:]:
        if not isinstance(item, dict):
            continue
        snippets.append(
            "[receipt] "
            f"intent={item.get('intent')} ok={item.get('success')} "
            f"id={item.get('receipt_id', '')}"
        )
    return snippets


def build_wm_first_snippets(
    *,
    state_context: StateContext | None = None,
    observations: Sequence[Any] = (),
    receipts: Sequence[Any] = (),
    extra: Sequence[str] = (),
) -> list[str]:
    """Prefer WM projection + execution facts over chat narrative."""
    snippets: list[str] = []
    if state_context is not None:
        snippets.extend(state_context.to_planner_snippets())
    snippets.extend(observation_snippets(observations))
    snippets.extend(receipt_snippets(receipts))
    for item in extra:
        text = str(item).strip()
        if text:
            snippets.append(text)
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for snip in snippets:
        if snip not in seen:
            seen.add(snip)
            out.append(snip)
    return out


def build_wm_first_context(
    context_manager: ContextManager,
    query: str,
    *,
    state_context: StateContext | None = None,
    observations: Sequence[Any] = (),
    receipts: Sequence[Any] = (),
    conversation_history: list[tuple[str, str]] | None = None,
    extra_snippets: Sequence[str] = (),
) -> ContextBundle:
    """Assemble context with WM/receipts first; chat history is secondary."""
    workspace_snippets = build_wm_first_snippets(
        state_context=state_context,
        observations=observations,
        receipts=receipts,
        extra=extra_snippets,
    )
    return context_manager.build_context(
        query,
        workspace_snippets=workspace_snippets or None,
        conversation_history=conversation_history,
    )


__all__ = [
    "observation_snippets",
    "receipt_snippets",
    "build_wm_first_snippets",
    "build_wm_first_context",
]
