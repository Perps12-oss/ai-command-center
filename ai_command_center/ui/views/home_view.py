"""Home - Hybrid spatial grid (ribbon / metrics / activity feed)."""



from __future__ import annotations



from typing import TYPE_CHECKING



from ai_command_center.core.event_bus import EventBus

from ai_command_center.ui.components.action_ribbon import ActionRibbon

from ai_command_center.ui.components.activity_feed_panel import ActivityFeedPanel

from ai_command_center.ui.components.metric_card_v2 import MetricCardV2

from ai_command_center.ui.layer.layer_stack import PageLayerStack



if TYPE_CHECKING:

    from ai_command_center.ui.layer.content_backdrop import ShellBackdrop





class HomeView(PageLayerStack):

    """Logic controller for home; visual surface is ShellBackdrop overlay zones."""



    def __init__(self, master, *, shell: ShellBackdrop, bus: EventBus | None = None, **kwargs) -> None:

        super().__init__(master, "home", **kwargs)

        self._shell = shell

        self.place_forget()

        self.background_canvas.place_forget()



        ribbon_host = shell.get_zone_host("action_ribbon")

        feed_host = shell.get_zone_host("activity_feed")



        self._ribbon = ActionRibbon(ribbon_host)

        self._ribbon.pack(fill="both", expand=True)



        self._cards: dict[str, MetricCardV2] = {}

        card_specs = (

            ("SystemStatus", "System Status", "ring", "metric_system"),

            ("Knowledge", "Knowledge Base", "default", "metric_knowledge"),

            ("UsageOverview", "Usage Overview", "sparkline", "metric_usage"),

            ("Plugins", "Plugins", "default", "metric_plugins"),

        )

        for card_id, title, viz, zone_id in card_specs:

            host = shell.get_zone_host(zone_id)

            card = MetricCardV2(host, card_id, title, viz=viz)

            card.pack(fill="both", expand=True, padx=4, pady=4)

            self._cards[card_id] = card



        self._feed = ActivityFeedPanel(feed_host, bus=bus)

        self._feed.pack(fill="both", expand=True)



        shell.after_idle(shell.refresh)



    def mount_bus(self, bus: EventBus) -> None:

        self._feed.mount_bus(bus)



    def apply_system_snapshot(self, payload: dict) -> None:

        cpu = float(payload.get("cpu_percent", 0))

        ram = float(payload.get("ram_percent", 0))

        health = str(payload.get("health", "unknown"))



        badge_state = "ready" if health == "healthy" else "busy" if health == "stressed" else "offline"

        self._cards["SystemStatus"].update_metrics(

            value=f"{cpu:.0f}% CPU",

            badge_text=health.title(),

            badge_state=badge_state,

            delta=float(payload.get("cpu_delta")) if payload.get("cpu_delta") is not None else None,

            percent=cpu,

            subtitle=f"ram {ram:.0f}%",

        )



    def apply_command_history(self, payload: dict) -> None:

        commands = payload.get("commands") or []

        total = int(payload.get("total", len(commands)))

        self._cards["UsageOverview"].update_metrics(

            value=str(total),

            badge_text="Commands",

            badge_state="ready",

            percent=min(100.0, total * 5),

            subtitle=f"{len(commands)} recent",

        )

        for item in commands[-5:]:

            detail = str(item.get("detail", item.get("text", "")))

            if detail:

                self._feed.push_command(detail)



    def apply_note_index(self, payload: dict) -> None:

        indexed = int(payload.get("indexed_files", 0))

        vault_files = int(payload.get("vault_files", 0))

        label = f"{indexed // 1000}k" if indexed >= 1000 else str(indexed)

        docs = f"{indexed:,} Documents" if indexed else "0 Documents"

        self._cards["Knowledge"].update_metrics(

            value=label,

            badge_text="Indexed",

            badge_state="ready",

            percent=(indexed / vault_files * 100) if vault_files else 0,

            subtitle=docs,

            history=[f"vault {vault_files} files"],

        )



    def apply_plugin_catalog(self, payload: dict) -> None:

        plugins = payload.get("plugins") or []

        enabled = sum(1 for p in plugins if p.get("enabled"))

        names = [str(p.get("name", ""))[:12] for p in plugins[:3]]

        self._cards["Plugins"].update_metrics(

            value=f"{enabled} Active",

            badge_text=f"{len(plugins)} total",

            badge_state="ready",

            subtitle=", ".join(names) if names else "No plugins",

            history=names,

        )



    def apply_activity_event(self, payload: dict) -> None:

        event = str(payload.get("event", payload.get("kind", "event")))

        self._feed.append_line(event, tag="success")



    def apply_footer(self, *, ollama_url: str, vault_path: str, online: bool) -> None:

        pass



    def apply_motion(self, primitive_id: str, intensity: float, payload: dict) -> None:

        if primitive_id in ("HeroPanel", "ActionRibbon"):

            glow = float(payload.get("glow_intensity", intensity))

            cpu = float(payload.get("cpu_percent", 30))

            self._ribbon.set_live(cpu, cpu * 0.8, cpu * 0.5, glow=glow)


