"""Agent Monitor workspace panels (Phase 11D / Article 14)."""

from __future__ import annotations

from ai_command_center.ui.views.agent_monitor.active_agents_panel import ActiveAgentsPanel
from ai_command_center.ui.views.agent_monitor.agent_state_panel import AgentStatePanel
from ai_command_center.ui.views.agent_monitor.execution_history_panel import (
    ExecutionHistoryPanel,
)
from ai_command_center.ui.views.agent_monitor.pipeline_progress_panel import (
    PipelineProgressPanel,
)
from ai_command_center.ui.views.agent_monitor.task_assignment_panel import (
    TaskAssignmentPanel,
)

__all__ = [
    "ActiveAgentsPanel",
    "AgentStatePanel",
    "ExecutionHistoryPanel",
    "PipelineProgressPanel",
    "TaskAssignmentPanel",
]
