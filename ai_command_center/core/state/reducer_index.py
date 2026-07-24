"""Topic → reducer index for slice-based AppState reduction.

Reducers that ignore a topic return the same state object (identity).
We index by:

1. String topic literals in bytecode consts (and nested collections)
2. Imported / module-level topic constants referenced via ``co_names``
3. One level of callee functions (wrapper reducers that delegate)
4. Identity probe with an empty payload (empty-payload no-ops still need 1–3)

Partial matches must not drop handlers that only reference topics via imports.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

from ai_command_center.core.event_bus import Event

Reducer = Callable[[Any, Event], Any]


def _topics_from_value(value: Any, topics: Sequence[str]) -> set[str]:
    found: set[str] = set()
    topic_set = topics if isinstance(topics, (set, frozenset)) else set(topics)
    if isinstance(value, str):
        if value in topic_set:
            found.add(value)
        return found
    if isinstance(value, (frozenset, set, tuple, list)):
        for item in value:
            if isinstance(item, str) and item in topic_set:
                found.add(item)
    return found


def _topics_from_callable(fn: Any, topics: Sequence[str], *, depth: int) -> set[str]:
    found: set[str] = set()
    code = getattr(fn, "__code__", None)
    if code is None:
        return found

    consts = code.co_consts if code.co_consts is not None else ()
    for const in consts:
        found |= _topics_from_value(const, topics)

    globs = getattr(fn, "__globals__", {}) or {}
    names = code.co_names if code.co_names is not None else ()
    for name in names:
        if name not in globs:
            continue
        value = globs[name]
        found |= _topics_from_value(value, topics)
        if depth > 0 and callable(value) and getattr(value, "__code__", None) is not None:
            found |= _topics_from_callable(value, topics, depth=depth - 1)

    # Nested functions defined inside the reducer.
    for const in consts:
        if getattr(const, "co_consts", None) is not None:
            # code object — resolve string literals only (no globals)
            for nested_const in const.co_consts or ():
                found |= _topics_from_value(nested_const, topics)

    return found


def build_topic_reducer_index(
    reducers: Sequence[Reducer],
    topics: Sequence[str],
    *,
    empty_state: Any,
) -> dict[str, tuple[Reducer, ...]]:
    """Return per-topic reducer tuples. Falls back to all reducers if empty."""
    index: dict[str, list[Reducer]] = defaultdict(list)
    reducer_topics: dict[Reducer, set[str]] = {}

    for reducer in reducers:
        reducer_topics[reducer] = _topics_from_callable(reducer, topics, depth=1)

    for topic in topics:
        for reducer in reducers:
            declared = reducer_topics.get(reducer) or set()
            if topic in declared:
                index[topic].append(reducer)
                continue
            # Identity probe: wrong-topic reducers return the same object.
            out = reducer(empty_state, Event(topic=topic, payload={}, source="reducer_index"))
            if out is not empty_state:
                index[topic].append(reducer)

    result: dict[str, tuple[Reducer, ...]] = {}
    all_reducers = tuple(reducers)
    for topic in topics:
        matched = tuple(index.get(topic) or ())
        result[topic] = matched if matched else all_reducers
    return result
