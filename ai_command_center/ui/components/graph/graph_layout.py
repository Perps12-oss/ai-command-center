"""Shared layout helpers for graph canvases (domain-agnostic)."""

from __future__ import annotations

import math
from collections.abc import Sequence


def circular_layout(
    node_ids: Sequence[str],
    *,
    width: float,
    height: float,
    node_radius: float = 22.0,
    padding: float = 12.0,
) -> dict[str, tuple[float, float]]:
    """Place nodes evenly on a circle centered in the viewport."""
    ids = list(node_ids)
    if not ids:
        return {}
    cx, cy = width / 2.0, height / 2.0
    if len(ids) == 1:
        return {ids[0]: (cx, cy)}
    radius = min(width, height) / 2.0 - node_radius - padding
    radius = max(radius, 40.0)
    positions: dict[str, tuple[float, float]] = {}
    n = len(ids)
    for i, node_id in enumerate(ids):
        angle = (2 * math.pi * i / n) - (math.pi / 2)
        positions[node_id] = (
            cx + radius * math.cos(angle),
            cy + radius * math.sin(angle),
        )
    return positions


def radial_layout(
    center_id: str,
    peer_ids: Sequence[str],
    *,
    width: float,
    height: float,
    min_radius: float = 60.0,
    max_radius: float = 100.0,
    radius_per_peer: float = 30.0,
) -> dict[str, tuple[float, float]]:
    """Place a center node with peers on a surrounding ring."""
    cx, cy = width / 2.0, height / 2.0
    positions: dict[str, tuple[float, float]] = {center_id: (cx, cy)}
    peers = list(peer_ids)
    n = len(peers)
    if n == 0:
        return positions
    radius = min(max_radius, max(min_radius, radius_per_peer * n))
    for i, peer_id in enumerate(peers):
        angle = (2 * math.pi * i / n) if n > 0 else 0.0
        positions[peer_id] = (
            cx + radius * math.cos(angle),
            cy + radius * math.sin(angle),
        )
    return positions


__all__ = ["circular_layout", "radial_layout"]
