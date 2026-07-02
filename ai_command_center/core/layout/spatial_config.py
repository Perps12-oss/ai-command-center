"""Spatial layout JSON loaders — repository access belongs in core, not UI."""

from __future__ import annotations

from typing import Any

from ai_command_center.repositories.spatial_repository import SpatialRepository


def load_style_lock(repo: SpatialRepository | None = None) -> dict[str, Any]:
    return (repo or SpatialRepository()).load_style_lock()


def load_layout_schema(repo: SpatialRepository | None = None) -> dict[str, Any]:
    return (repo or SpatialRepository()).load_layout_schema()


def load_motion_bindings(repo: SpatialRepository | None = None) -> dict[str, Any]:
    return (repo or SpatialRepository()).load_motion_bindings()


def load_background_layer(repo: SpatialRepository | None = None) -> dict[str, Any]:
    return (repo or SpatialRepository()).load_background_layer()


def load_spatial_map(repo: SpatialRepository | None = None) -> dict[str, Any]:
    return (repo or SpatialRepository()).load_spatial_map()
