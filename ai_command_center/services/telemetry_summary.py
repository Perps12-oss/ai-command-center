"""Read-only derived metrics from telemetry_events (offline intelligence only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_STARTED,
    COMMAND_ROUTED,
    MEMORY_STORED,
    NOTE_CREATED,
    NOTE_ERROR,
    NOTE_SEARCH_RESULTS,
    TOOL_ERROR,
    TOOL_RESULT,
    UI_NAVIGATE,
    UI_COMMAND,
    UI_PALETTE_CLOSE,
    UI_PALETTE_OPEN,
)
from ai_command_center.domain.telemetry_event import TelemetryEvent

_HESITATION_WINDOW_S = 2.0
_RETRY_WINDOW_S = 30.0

_INTENT_OUTCOMES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "chat": (frozenset({CHAT_COMPLETE}), frozenset({CHAT_ERROR, CHAT_CANCELLED})),
    "shell": (frozenset({TOOL_RESULT}), frozenset({TOOL_ERROR})),
    "note_search": (frozenset({NOTE_SEARCH_RESULTS}), frozenset({NOTE_ERROR})),
    "note_new": (frozenset({NOTE_CREATED}), frozenset({NOTE_ERROR})),
    "memory_remember": (frozenset({MEMORY_STORED}), frozenset()),
    "memory_select": (frozenset({MEMORY_STORED}), frozenset()),
    "navigate": (frozenset({UI_NAVIGATE}), frozenset()),
}

_SESSION_EVENT_TOPICS = frozenset(
    {
        UI_COMMAND,
        COMMAND_ROUTED,
        CHAT_STARTED,
        CHAT_COMPLETE,
        CHAT_ERROR,
        CHAT_CANCELLED,
        TOOL_RESULT,
        TOOL_ERROR,
        NOTE_SEARCH_RESULTS,
        NOTE_CREATED,
        NOTE_ERROR,
        MEMORY_STORED,
    }
)


def _event_name(row: TelemetryEvent | dict[str, Any]) -> str:
    if isinstance(row, TelemetryEvent):
        return row.event_type
    return str(row.get("event", ""))


def _payload(row: TelemetryEvent | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, TelemetryEvent):
        return row.payload_dict()
    return row.get("payload") or {}


def _parse_ts(row: TelemetryEvent | dict[str, Any]) -> float:
    if isinstance(row, TelemetryEvent):
        return row.emitted_at.timestamp()
    raw = str(row.get("timestamp", ""))
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return 0.0


def _sorted_rows(rows: list[TelemetryEvent | dict[str, Any]]) -> list[TelemetryEvent | dict[str, Any]]:
    return sorted(rows, key=_parse_ts)


def _derive_commands(rows: list[TelemetryEvent | dict[str, Any]]) -> dict[str, Any]:
    """Offline command correlation from raw bus events."""
    total = 0
    success = 0
    fail = 0
    latencies: list[float] = []
    retries = 0
    last_fail_text = ""
    last_fail_at = 0.0

    ordered = _sorted_rows(rows)
    index = 0
    while index < len(ordered):
        row = ordered[index]
        if _event_name(row) != UI_COMMAND:
            index += 1
            continue

        text = str(_payload(row).get("text", "")).strip()
        if not text:
            index += 1
            continue

        invoked_at = _parse_ts(row)
        if last_fail_text and text == last_fail_text and (invoked_at - last_fail_at) <= _RETRY_WINDOW_S:
            retries += 1

        intent = ""
        request_id = ""
        j = index + 1
        outcome: str | None = None
        outcome_at = invoked_at

        while j < len(ordered):
            nxt = ordered[j]
            topic = _event_name(nxt)
            pl = _payload(nxt)

            if topic == UI_COMMAND:
                break

            if topic == COMMAND_ROUTED and pl.get("bus_source") == "command_router":
                if str(pl.get("status", "pending")) == "pending":
                    intent = str(pl.get("intent", ""))
                    if intent == "navigate":
                        outcome = "success"
                        outcome_at = _parse_ts(nxt)
                        break

            if topic == CHAT_STARTED:
                request_id = str(pl.get("request_id", ""))

            if intent:
                ok_topics, fail_topics = _INTENT_OUTCOMES.get(intent, (frozenset(), frozenset()))
                if topic in ok_topics:
                    if intent == "chat" and request_id:
                        if str(pl.get("request_id", "")) not in ("", request_id):
                            j += 1
                            continue
                    outcome = "success"
                    outcome_at = _parse_ts(nxt)
                    break
                if topic in fail_topics:
                    outcome = "fail"
                    outcome_at = _parse_ts(nxt)
                    break

            j += 1

        total += 1
        if outcome == "success":
            success += 1
            latencies.append(max(0.0, (outcome_at - invoked_at) * 1000.0))
        elif outcome == "fail":
            fail += 1
            last_fail_text = text
            last_fail_at = outcome_at
        else:
            fail += 1

        index += 1

    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
    return {
        "total": total,
        "success": success,
        "fail": fail,
        "avg_latency_ms": avg_latency,
        "retries": retries,
    }


def _derive_hesitation(rows: list[TelemetryEvent | dict[str, Any]]) -> tuple[int, int, float]:
    """Palette open -> close within window without ui.command."""
    palette_opens = 0
    cancellations = 0
    hesitations = 0

    ordered = _sorted_rows(rows)
    open_at: float | None = None
    saw_command = False

    for row in ordered:
        topic = _event_name(row)
        ts = _parse_ts(row)

        if topic == UI_PALETTE_OPEN:
            palette_opens += 1
            open_at = ts
            saw_command = False
        elif topic == UI_COMMAND and open_at is not None:
            saw_command = True
        elif topic == UI_PALETTE_CLOSE and open_at is not None:
            cancellations += 1
            elapsed = ts - open_at
            if elapsed <= _HESITATION_WINDOW_S and not saw_command:
                hesitations += 1
            open_at = None
            saw_command = False

    rate = round((hesitations / palette_opens) * 100, 1) if palette_opens else 0.0
    return palette_opens, cancellations, rate


def _derive_ollama_latencies(rows: list[TelemetryEvent | dict[str, Any]]) -> list[float]:
    started: dict[str, float] = {}
    latencies: list[float] = []
    for row in _sorted_rows(rows):
        topic = _event_name(row)
        pl = _payload(row)
        rid = str(pl.get("request_id", ""))
        if not rid:
            continue
        if topic == CHAT_STARTED:
            started[rid] = _parse_ts(row)
        elif topic == CHAT_COMPLETE and rid in started:
            latencies.append(max(0.0, (_parse_ts(row) - started.pop(rid)) * 1000.0))
    return latencies


def _derive_scope_ratio(rows: list[TelemetryEvent | dict[str, Any]]) -> dict[str, Any]:
    scoped = 0
    total = 0
    for row in rows:
        if _event_name(row) not in _SESSION_EVENT_TOPICS:
            continue
        total += 1
        payload = _payload(row)
        if str(payload.get("workspace_id", "")).strip() or str(
            payload.get("entity_id", "")
        ).strip():
            scoped += 1
    ratio = round((scoped / total) * 100, 1) if total else 0.0
    return {"total": total, "scoped": scoped, "ratio_pct": ratio}


def compute_session_summary(rows: list[TelemetryEvent | dict[str, Any]]) -> dict[str, Any]:
    """Aggregate raw telemetry rows into a daily-driver session summary."""
    commands = _derive_commands(rows)
    palette_opens, cancellations, hesitation_rate = _derive_hesitation(rows)

    over_budget = sum(1 for r in rows if _event_name(r) == "context.over_budget")
    token_samples: list[int] = []
    for row in rows:
        if _event_name(row) != "context.snapshot_created":
            continue
        tokens = _payload(row).get("context_size_tokens")
        if isinstance(tokens, int):
            token_samples.append(tokens)

    avg_tokens = round(sum(token_samples) / len(token_samples), 1) if token_samples else 0.0
    ollama_latencies = _derive_ollama_latencies(rows)
    workspace_scope = _derive_scope_ratio(rows)
    if ollama_latencies and commands["avg_latency_ms"] == 0.0:
        commands = {
            **commands,
            "avg_latency_ms": round(sum(ollama_latencies) / len(ollama_latencies), 1),
        }

    friction_score = _friction_score(
        retries=commands["retries"],
        cancellations=cancellations,
        palette_opens=palette_opens,
        avg_latency_ms=commands["avg_latency_ms"],
        fail_rate=(commands["fail"] / commands["total"]) if commands["total"] else 0.0,
    )

    return {
        "commands": {
            "total": commands["total"],
            "success": commands["success"],
            "fail": commands["fail"],
            "avg_latency_ms": commands["avg_latency_ms"],
            "retries": commands["retries"],
        },
        "ux": {
            "palette_opens": palette_opens,
            "cancellations": cancellations,
            "hesitation_rate_pct": hesitation_rate,
        },
        "context": {
            "over_budget": over_budget,
            "avg_tokens": avg_tokens,
        },
        "workspace_scope": workspace_scope,
        "friction_score": friction_score,
    }


def _friction_score(
    *,
    retries: int,
    cancellations: int,
    palette_opens: int,
    avg_latency_ms: float,
    fail_rate: float,
) -> str:
    score = 0.0
    if palette_opens:
        score += (cancellations / palette_opens) * 2.0
    score += retries * 0.5
    if avg_latency_ms > 8000:
        score += 2.0
    elif avg_latency_ms > 4000:
        score += 1.0
    score += fail_rate * 3.0

    if score < 1.0:
        return "LOW"
    if score < 2.5:
        return "MEDIUM"
    return "HIGH"


def format_session_summary(summary: dict[str, Any], *, session_id: str = "") -> str:
    commands = summary.get("commands", {})
    ux = summary.get("ux", {})
    context = summary.get("context", {})
    workspace_scope = summary.get("workspace_scope", {})
    header = "SESSION SUMMARY"
    if session_id:
        header += f" ({session_id})"

    lines = [
        header,
        "",
        "Commands:",
        f"- total: {commands.get('total', 0)}",
        f"- success: {commands.get('success', 0)}",
        f"- fail: {commands.get('fail', 0)}",
        f"- avg latency: {commands.get('avg_latency_ms', 0)} ms",
        f"- retries (derived): {commands.get('retries', 0)}",
        "",
        "UX:",
        f"- palette opens: {ux.get('palette_opens', 0)}",
        f"- cancellations: {ux.get('cancellations', 0)}",
        f"- hesitation rate: {ux.get('hesitation_rate_pct', 0)}%",
        "",
        "Context:",
        f"- over budget: {context.get('over_budget', 0)}",
        f"- avg tokens: {context.get('avg_tokens', 0)}",
        "",
        "Workspace scope:",
        f"- scoped session events: {workspace_scope.get('scoped', 0)} / {workspace_scope.get('total', 0)}",
        f"- scoped ratio: {workspace_scope.get('ratio_pct', 0)}%",
        "",
        "Friction Score:",
        f"- {summary.get('friction_score', 'LOW')}",
    ]
    return "\n".join(lines)
