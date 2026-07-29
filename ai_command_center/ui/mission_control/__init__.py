"""Mission Control dashboard primitives — AppState projections only.

Ownership: UI renderer layer. Reads AppState snapshots; never touches
services, repositories, or storage. Commands flow via callbacks → EventBus.
"""

from __future__ import annotations

from ai_command_center.ui.mission_control.activity_timeline import ActivityTimeline
from ai_command_center.ui.mission_control.action_chips import ActionChips
from ai_command_center.ui.mission_control.brain_panel import BrainSituationPanel
from ai_command_center.ui.mission_control.kpi_card import StateAwareKpiCard
from ai_command_center.ui.mission_control.layout_prefs import LayoutPrefs, Density
from ai_command_center.ui.mission_control.mission_hero import MissionHeroPanel
from ai_command_center.ui.mission_control.modes import MissionMode, derive_mission_mode
from ai_command_center.ui.mission_control.status_strip import GroupedStatusStrip
from ai_command_center.ui.mission_control.world_widget import WorldModelWidget

__all__ = [
    "ActivityTimeline",
    "ActionChips",
    "BrainSituationPanel",
    "Density",
    "GroupedStatusStrip",
    "LayoutPrefs",
    "MissionHeroPanel",
    "MissionMode",
    "StateAwareKpiCard",
    "WorldModelWidget",
    "derive_mission_mode",
]
