"""Goal Dashboard workspace panels (Phase 11F / Article 16)."""

from __future__ import annotations

from ai_command_center.ui.views.goal_dashboard.goal_detail_panel import GoalDetailPanel
from ai_command_center.ui.views.goal_dashboard.goal_history_panel import GoalHistoryPanel
from ai_command_center.ui.views.goal_dashboard.goal_list_panel import GoalListPanel
from ai_command_center.ui.views.goal_dashboard.goal_progress_panel import GoalProgressPanel
from ai_command_center.ui.views.goal_dashboard.plan_preview_panel import PlanPreviewPanel

__all__ = [
    "GoalDetailPanel",
    "GoalHistoryPanel",
    "GoalListPanel",
    "GoalProgressPanel",
    "PlanPreviewPanel",
]
