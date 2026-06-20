#!/usr/bin/env python3

"""Validate UI design schema + layout compiler."""



from __future__ import annotations



import inspect

import sys

from pathlib import Path



PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))





def main() -> int:

    print("=== UI Schema Compiler Gate ===")

    failures: list[str] = []



    from ai_command_center.ui.layer import PageLayerStack, BackgroundCanvas, BackgroundController

    from ai_command_center.ui.layer.background_spec import load_background_layer, global_wallpaper_image

    from ai_command_center.ui.layout.compiler import LayoutCompiler, load_spatial_map

    from ai_command_center.ui.spatial import SpatialLayoutEngine, ZoneMotionOverlay

    from ai_command_center.ui.theme import tokens as T



    compiler = LayoutCompiler()

    errors = compiler.validate()

    if errors:

        failures.extend(errors)



    bg = load_background_layer()

    if bg.get("version") != "1.3":

        failures.append("BACKGROUND_LAYER version must be 1.3")

    if "global_wallpaper" not in bg:

        failures.append("BACKGROUND_LAYER missing global_wallpaper")

    if "command_center_bg" not in global_wallpaper_image():

        failures.append("global wallpaper must be command_center_bg.jpg")



    spatial = load_spatial_map()

    if spatial.get("version") != "1.1":

        failures.append("SPATIAL_MAP version must be 1.1")

    home_map = spatial.get("maps", {}).get("home", {})

    home_zones = {z["id"] for z in home_map.get("zones", [])}

    for zid in (
        "action_ribbon",
        "metric_system",
        "metric_knowledge",
        "metric_usage",
        "metric_plugins",
        "activity_feed",
    ):

        if zid not in home_zones:

            failures.append(f"SPATIAL_MAP home missing zone {zid}")



    home = compiler.get_page("home")

    if home.get("layout") != "HYBRID_SPATIAL_GRID":

        failures.append("home layout must be HYBRID_SPATIAL_GRID")



    for page in ("home", "system", "chat", "notes", "plugins", "settings"):

        spec = compiler.get_page(page)

        if "background" not in spec:

            failures.append(f"{page} missing background in schema")

        bg_spec = spec.get("background", {})

        if bg_spec.get("inherit") != "global_wallpaper":

            failures.append(f"{page} background must inherit global_wallpaper")

        img = str(bg_spec.get("image", ""))

        if "command_center_bg" not in img:

            failures.append(f"{page} must use command_center_bg.jpg")



    if PageLayerStack is None or BackgroundCanvas is None:

        failures.append("layer stack import failed")



    style = compiler._style

    if style.get("version") != "1.3":

        failures.append("STYLE_LOCK version must be 1.3")

    palette = style.get("palette", {})

    for key in ("glass_bg", "glass_border", "light_glass", "text_shadow"):

        if key not in palette:

            failures.append(f"STYLE_LOCK missing palette.{key}")

    if palette.get("bg_deep") != "#0B0C15":

        failures.append("STYLE_LOCK bg_deep mismatch")



    for tok in ("GLASS_BG", "GLASS_BORDER", "LIGHT_GLASS", "TEXT_SHADOW"):

        if not hasattr(T, tok):

            failures.append(f"tokens.py missing {tok}")



    from ai_command_center.ui.components.activity_feed_panel import ActivityFeedPanel



    src = inspect.getsource(ActivityFeedPanel.mount_bus)

    if "telemetry_events" not in src:

        failures.append("ActivityFeedPanel must subscribe to telemetry_events bus")



    motion = compiler._motion

    if "ActionRibbon" not in motion.get("bindings", {}) and "HeroPanel" not in motion.get("bindings", {}):

        failures.append("MOTION_BINDINGS missing ActionRibbon or HeroPanel")



    from ai_command_center.ui.motion.scheduler import MotionScheduler

    from ai_command_center.core.event_bus import EventBus



    bus = EventBus()

    sched = MotionScheduler(bus)

    sched.start()

    sched.stop()



    from ai_command_center.services.system_monitor_service import SystemMonitorService



    if SystemMonitorService.name != "system_monitor":

        failures.append("system_monitor name wrong")



    if failures:

        print("FAIL:")

        for item in failures:

            print(f"  - {item}")

        return 1



    print("PASS: UI schema compiler — layout, style, motion bindings valid")

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

