"""Layout compiler - validates design JSON and resolves page trees."""

from __future__ import annotations

from typing import Any

from ai_command_center.core.events.topics import NOTE_INDEX_COMPLETE
from ai_command_center.core.layout.spatial_config import (
    load_background_layer,
    load_layout_schema,
    load_motion_bindings,
    load_spatial_map,
    load_style_lock,
)

APPROVED_LAYOUTS = frozenset(
    {
        "SPATIAL_MAP",
        "HYBRID_SPATIAL_GRID",
        "HERO_STACK",
        "GRID_2x2",
        "SPLIT_2PANE",
        "SPLIT_3PANE",
        "STACKED_LIST",
    }
)

HERO_CYAN_ALLOWED = frozenset({"HeroPanel", "ActionRibbon"})
HYBRID_HOME_ZONES = frozenset({
    "action_ribbon",
    "metric_system",
    "metric_knowledge",
    "metric_usage",
    "metric_plugins",
    "activity_feed",
})


class LayoutValidationError(Exception):
    pass


class LayoutCompiler:
    def __init__(
        self,
        schema: dict[str, Any] | None = None,
        style_lock: dict[str, Any] | None = None,
        motion_bindings: dict[str, Any] | None = None,
    ) -> None:
        self._schema = schema or load_layout_schema()
        self._style = style_lock or load_style_lock()
        self._motion = motion_bindings or load_motion_bindings()
        self._registry = frozenset(self._schema.get("registry", []))

    def validate(self) -> list[str]:
        errors: list[str] = []
        errors.extend(self._validate_style_lock())
        errors.extend(self._validate_motion_bindings())
        errors.extend(self._validate_background_layer())
        errors.extend(self._validate_spatial_maps())
        errors.extend(self._validate_pages())
        return errors

    def get_page(self, page_id: str) -> dict[str, Any]:
        pages = self._schema.get("pages", {})
        if page_id not in pages:
            raise LayoutValidationError(f"unknown page: {page_id}")
        return pages[page_id]

    def _validate_style_lock(self) -> list[str]:
        errors: list[str] = []
        allowed = self._style.get("visual_hierarchy", {}).get(
            "hero_cyan_allowed_components", []
        )
        if not HERO_CYAN_ALLOWED.issubset(set(allowed)):
            errors.append(
                f"hero_cyan_allowed_components must include {sorted(HERO_CYAN_ALLOWED)}"
            )
        return errors

    def _validate_motion_bindings(self) -> list[str]:
        errors: list[str] = []
        allowed_sources = frozenset(self._motion.get("allowed_sources", []))
        bindings = self._motion.get("bindings", {})
        for name, spec in bindings.items():
            for topic in spec.get("required", []):
                base = topic.split(".")[0]
                if topic not in allowed_sources and base not in {
                    s.split(".")[0] for s in allowed_sources
                }:
                    if not any(topic.startswith(s.rstrip("*")) for s in allowed_sources):
                        if topic not in (
                            NOTE_INDEX_COMPLETE,
                            "plugin.catalog",
                            "activity_events.rate",
                        ):
                            pass
            if "fallback" not in spec:
                errors.append(f"motion binding {name} missing fallback")
        return errors

    def _validate_background_layer(self) -> list[str]:
        errors: list[str] = []
        try:
            bg = load_background_layer()
        except Exception as exc:
            return [f"BACKGROUND_LAYER.json: {exc}"]
        modes = frozenset(bg.get("approved_modes", []))
        pages_bg = bg.get("pages", {})
        if bg.get("version") != "1.3":
            errors.append("BACKGROUND_LAYER version must be 1.3")
        if "global_wallpaper" not in bg:
            errors.append("BACKGROUND_LAYER missing global_wallpaper")
        global_img = str(bg.get("global_wallpaper", {}).get("image", ""))
        if "command_center_bg" not in global_img:
            errors.append("global_wallpaper must use command_center_bg.jpg")
        for page_id, page_bg in pages_bg.items():
            if page_bg.get("inherit") != "global_wallpaper":
                errors.append(f"BACKGROUND_LAYER page {page_id} must inherit global_wallpaper")
            alt = page_bg.get("image", "")
            if alt and "command_center_bg" not in alt and page_bg.get("inherit") != "global_wallpaper":
                errors.append(f"page {page_id}: alternate background image forbidden")
        z = bg.get("layer_stack", {}).get("z_index", {})
        required_z = {"background", "depth", "motion", "ui", "modal"}
        if not required_z.issubset(z.keys()):
            errors.append(f"z_index missing keys: {required_z - z.keys()}")
        for page_id, page in self._schema.get("pages", {}).items():
            if page_id not in pages_bg:
                errors.append(f"BACKGROUND_LAYER missing page: {page_id}")
            schema_bg = page.get("background")
            if not schema_bg:
                errors.append(f"page {page_id}: missing background in LAYOUT_SCHEMA")
                continue
            if schema_bg.get("component") not in ("BackgroundCanvas", "ShellBackdrop"):
                errors.append(f"page {page_id}: background must be ShellBackdrop or BackgroundCanvas")
            inherit = schema_bg.get("inherit")
            if inherit and inherit != "global_wallpaper":
                errors.append(f"page {page_id}: background must inherit global_wallpaper")
            img = str(schema_bg.get("image", ""))
            if img and "command_center_bg" not in img:
                errors.append(f"page {page_id}: must use global command_center_bg.jpg")
            if schema_bg.get("z_index", 0) != z.get("background", 0):
                errors.append(f"page {page_id}: background z_index must be 0")
            mode = pages_bg.get(page_id, {}).get("mode") if page_id in pages_bg else None
            if mode and mode not in modes:
                errors.append(f"page {page_id}: unknown background mode {mode}")
        return errors

    def _validate_spatial_maps(self) -> list[str]:
        errors: list[str] = []
        try:
            spatial = load_spatial_map()
        except Exception as exc:
            return [f"SPATIAL_MAP.json: {exc}"]
        if spatial.get("version") != "1.1":
            errors.append("SPATIAL_MAP version must be 1.1")
        approved_roles = frozenset(spatial.get("approved_roles", []))
        maps = spatial.get("maps", {})
        for page_id, page in self._schema.get("pages", {}).items():
            layout = page.get("layout")
            if layout not in ("SPATIAL_MAP", "HYBRID_SPATIAL_GRID"):
                continue
            map_id = page.get("spatial_map", page_id)
            if map_id not in maps:
                errors.append(f"page {page_id}: spatial_map '{map_id}' not in SPATIAL_MAP.json")
                continue
            zone_ids = {z["id"] for z in maps[map_id].get("zones", [])}
            if layout == "HYBRID_SPATIAL_GRID" and not HYBRID_HOME_ZONES.issubset(zone_ids):
                missing = HYBRID_HOME_ZONES - zone_ids
                errors.append(f"home hybrid missing zones: {sorted(missing)}")
            for role in maps[map_id].get("zones", []):
                for r in role.get("role", []):
                    if r not in approved_roles:
                        errors.append(f"spatial {map_id}: unknown role {r}")
            for i, node in enumerate(page.get("children", [])):
                zone_id = node.get("props", {}).get("zone_id")
                if layout == "HYBRID_SPATIAL_GRID" and not zone_id:
                    errors.append(f"page {page_id}[{i}]: HYBRID_SPATIAL_GRID requires zone_id")
                elif layout == "SPATIAL_MAP" and not zone_id:
                    errors.append(f"page {page_id}[{i}]: SPATIAL_MAP requires zone_id")
                elif zone_id and zone_id not in zone_ids:
                    errors.append(f"page {page_id}[{i}]: unknown zone_id {zone_id}")
            for mod in maps[map_id].get("modules", []):
                zid = mod.get("zone_id")
                if zid and zid not in zone_ids:
                    errors.append(f"spatial module {mod.get('type')}: unknown zone {zid}")
            if layout == "HYBRID_SPATIAL_GRID":
                child_types = {n.get("component") for n in page.get("children", [])}
                if "ActionRibbon" not in child_types:
                    errors.append("home must include ActionRibbon")
                if "ActivityFeedPanel" not in child_types:
                    errors.append("home must include ActivityFeedPanel")
        return errors

    def _validate_pages(self) -> list[str]:
        errors: list[str] = []
        pages = self._schema.get("pages", {})
        for page_id, page in pages.items():
            layout = page.get("layout")
            if layout not in APPROVED_LAYOUTS:
                errors.append(f"page {page_id}: invalid layout {layout}")
            spatial = layout in ("SPATIAL_MAP", "HYBRID_SPATIAL_GRID")
            self._walk_tree(
                page.get("children", []),
                errors,
                path=page_id,
                spatial=spatial,
            )
        return errors

    def _walk_tree(
        self, nodes: list[dict[str, Any]], errors: list[str], *, path: str, spatial: bool = False
    ) -> None:
        for i, node in enumerate(nodes):
            comp = node.get("component", "")
            if comp not in self._registry:
                errors.append(f"{path}[{i}]: unknown component {comp}")
            props = node.get("props", {})
            if spatial and comp != "LayoutNode" and not props.get("zone_id"):
                errors.append(f"{path}[{i}]: missing zone_id for spatial component {comp}")
            layout = props.get("layout")
            if layout and layout not in APPROVED_LAYOUTS:
                errors.append(f"{path}[{i}]: invalid nested layout {layout}")
            if comp == "LayoutNode" and not layout:
                errors.append(f"{path}[{i}]: LayoutNode missing layout prop")
            if spatial and comp == "LayoutNode":
                errors.append(f"{path}[{i}]: LayoutNode forbidden in spatial page")
            children = node.get("children", [])
            if children:
                self._walk_tree(children, errors, path=f"{path}.{comp}", spatial=spatial)
