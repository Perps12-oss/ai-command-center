"""Topic → reducer index for slice-based AppState reduction.

Reducers that ignore a topic return the same state object (identity).
We index by probing that identity contract plus bytecode topic literals so
empty-payload handlers that still own a topic are retained.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

from ai_command_center.core.event_bus import Event

Reducer = Callable[[Any, Event], Any]


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
        found: set[str] = set()
        code = getattr(reducer, "__code__", None)
        consts = code.co_consts if code is not None else ()
        for topic in topics:
            if topic in consts:
                found.add(topic)
        # Also detect frozenset/tuple topic groups embedded as consts.
        for const in consts:
            if isinstance(const, (frozenset, set, tuple, list)):
                for item in const:
                    if isinstance(item, str) and item in topics:
                        found.add(item)
        reducer_topics[reducer] = found

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
