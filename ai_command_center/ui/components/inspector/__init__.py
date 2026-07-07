"""Inspector UI primitives."""

from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.components.inspector.collapsible_section import CollapsibleSection
from ai_command_center.ui.components.inspector.execution_inspector import ExecutionInspector
from ai_command_center.ui.components.inspector.inspector_host import InspectorHost
from ai_command_center.ui.components.inspector.message_inspector import MessageInspector

__all__ = [
    "BaseInspector",
    "CollapsibleSection",
    "ExecutionInspector",
    "InspectorHost",
    "MessageInspector",
]
