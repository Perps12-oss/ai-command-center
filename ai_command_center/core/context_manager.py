"""Context budget manager — every AI request must pass through here first.

NO Ollama calls in this module. NO embeddings. NO vectors.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.core.contracts import (
    COMMAND_DEFERRED_VERSION,
    CONTEXT_BUNDLE_VERSION,
    OLLAMA_SERVICE_API_VERSION,
    SUPPORTED_VERSIONS,
)

# Locked contract surface (UCGS); anchors imports used by assembly boundaries.
_CONTEXT_MANAGER_CONTRACT = (
    COMMAND_DEFERRED_VERSION,
    CONTEXT_BUNDLE_VERSION,
    OLLAMA_SERVICE_API_VERSION,
    *SUPPORTED_VERSIONS,
)

MAX_CONTEXT_FILL_RATIO = 0.70


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Assembled prompt ready for OllamaService (contract v1.2)."""

    prompt: str
    sources: tuple[str, ...]
    token_estimate: int
    version: str = CONTEXT_BUNDLE_VERSION


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _compress_history(
    history: list[tuple[str, str]], budget_tokens: int
) -> tuple[list[tuple[str, str]], str | None]:
    if not history:
        return history, None
    lines = [f"{role}: {content}" for role, content in history]
    full = "\n".join(lines)
    if estimate_tokens(full) <= budget_tokens:
        return history, None

    keep = history[-4:] if len(history) > 4 else history[-2:]
    dropped = history[: -len(keep)]
    parts = [f"{r}: {c[:60]}" for r, c in dropped[-10:]]
    summary = "Earlier conversation summary: " + " | ".join(parts)
    if len(dropped) > 10:
        summary += f" … (+{len(dropped) - 10} earlier turns)"
    return keep, summary[:800]


class ContextManager:
    """Builds prompts from explicit, caller-supplied context only."""

    def __init__(
        self,
        max_context_tokens: int = 4000,
        fill_ratio: float = MAX_CONTEXT_FILL_RATIO,
    ) -> None:
        self._max_context_tokens = max_context_tokens
        self._fill_ratio = fill_ratio

    @property
    def context_budget_tokens(self) -> int:
        return int(self._max_context_tokens * self._fill_ratio)

    def build_context(
        self,
        query: str,
        *,
        clipboard: str | None = None,
        notes: list[str] | None = None,
        graph_snippets: list[str] | None = None,
        workspace_snippets: list[str] | None = None,
        conversation_history: list[tuple[str, str]] | None = None,
        clipboard_intent: bool = False,
        token_budget: int | None = None,
    ) -> ContextBundle:
        query = query.strip()
        if not query:
            return ContextBundle(prompt="", sources=(), token_estimate=0)

        budget = int(token_budget) if token_budget is not None else self.context_budget_tokens
        budget = max(1, budget)
        sources: list[str] = []
        sections: list[tuple[int, str, str]] = []

        working_history: list[tuple[str, str]] = []
        summary: str | None = None
        if conversation_history and not (clipboard_intent and clipboard):
            history_budget = max(200, budget // 3)
            working_history = list(conversation_history)
            working_history, summary = _compress_history(working_history, history_budget)

        if summary:
            sections.append((0, "conversation_summary", summary))

        if working_history:
            lines = [f"{role}: {content}" for role, content in working_history]
            body = "\n".join(lines)
            if body.strip():
                sections.append((1, "conversation_history", body))

        if workspace_snippets:
            for i, snippet in enumerate(workspace_snippets):
                body = snippet.strip()
                if body:
                    label = "workspace_state" if i == 0 else f"workspace_state_{i}"
                    sections.append((1, label, body))

        if graph_snippets:
            for i, snippet in enumerate(graph_snippets):
                body = snippet.strip()
                if body:
                    sections.append((2, f"memory_graph_{i}", body))

        if notes:
            for i, note in enumerate(notes):
                body = note.strip()
                if body:
                    sections.append((3, f"note_{i}", body))

        if clipboard:
            body = clipboard.strip()
            if body:
                clip_prio = 1 if clipboard_intent else 4
                sections.append((clip_prio, "clipboard", body))

        sections.append((5, "user_query", query))

        included: list[tuple[str, str]] = []
        total_tokens = 0

        for _prio, label, body in sorted(sections, key=lambda s: s[0]):
            block = f"[{label}]\n{body}"
            block_tokens = estimate_tokens(block)
            if total_tokens + block_tokens > budget and label != "user_query":
                continue
            if total_tokens + block_tokens > budget and label == "user_query":
                remaining = budget - total_tokens
                if remaining > 50:
                    char_limit = remaining * 4
                    body = body[:char_limit] + "…"
                    block = f"[{label}]\n{body}"
                    block_tokens = estimate_tokens(block)
                else:
                    block = f"[{label}]\n{body[:200]}"
                    block_tokens = estimate_tokens(block)
            included.append((label, block))
            sources.append(label)
            total_tokens += block_tokens

        prompt = "\n\n".join(block for _, block in included)
        return ContextBundle(
            prompt=prompt,
            sources=tuple(sources),
            token_estimate=total_tokens,
            version=CONTEXT_BUNDLE_VERSION,
        )
