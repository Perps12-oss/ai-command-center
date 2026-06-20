"""System — Reality Feed (floating glass cards on wallpaper)."""



from __future__ import annotations



from ai_command_center.ui.components.floating_ui import FLOAT_GAP, FLOAT_PAD, pack_floating

from ai_command_center.ui.components.glass_card import GlassCard

from ai_command_center.ui.components.footer_bar import FooterBar

from ai_command_center.ui.components.motion_widgets import (

    ActivityPulseField,

    EventStreamRibbon,

    StatusFluxBarGrid,

    SystemHeartbeat,

)

from ai_command_center.ui.components.page_header import PageHeader

from ai_command_center.ui.layer.layer_stack import PageLayerStack

from ai_command_center.ui.theme import tokens as T





class SystemView(PageLayerStack):

    def __init__(self, master, **kwargs) -> None:

        super().__init__(master, "system", **kwargs)



        header_card = GlassCard(self.ui_layer)

        pack_floating(header_card, first=True)

        PageHeader(

            header_card,

            title="System",

            subtitle="Reality feed — live operational state",

        ).pack(fill="x", padx=T.PAD, pady=T.PAD)



        self._heartbeat = SystemHeartbeat(self.ui_layer)

        pack_floating(self._heartbeat)



        self._flux_grid = StatusFluxBarGrid(self.ui_layer)

        pack_floating(self._flux_grid)



        self._ribbon = EventStreamRibbon(self.ui_layer)

        pack_floating(self._ribbon)



        self._pulse_field = ActivityPulseField(self.ui_layer)

        pack_floating(self._pulse_field)



        footer_card = GlassCard(self.ui_layer)

        footer_card.pack(fill="x", padx=FLOAT_PAD, pady=(0, FLOAT_GAP))

        self._footer = FooterBar(footer_card)

        self._footer.pack(fill="x", padx=T.PAD, pady=T.PAD)



    def apply_system_snapshot(self, payload: dict) -> None:

        cpu = float(payload.get("cpu_percent", 0))

        self._heartbeat.set_rate(cpu / 100.0)

        self._flux_grid.update_values(payload)



    def apply_system_event(self, payload: dict) -> None:

        detail = str(payload.get("detail", payload.get("kind", "")))

        if detail:

            self._ribbon.push_event(detail)



    def apply_motion(self, primitive_id: str, intensity: float) -> None:

        if primitive_id == "ActivityPulseField":

            self._pulse_field.set_density(intensity)

        elif primitive_id == "SystemHeartbeat":

            self._heartbeat.set_rate(intensity)



    def apply_footer(self, *, ollama_url: str, vault_path: str, online: bool) -> None:

        self._footer.update_info(

            ollama_url=ollama_url,

            vault_path=vault_path,

            online=online,

        )

