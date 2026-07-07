"""Inspector UI primitives."""

from ai_command_center.ui.components.inspector.artifact_inspector import ArtifactInspector
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.components.inspector.collapsible_section import CollapsibleSection
from ai_command_center.ui.components.inspector.execution_inspector import ExecutionInspector
from ai_command_center.ui.components.inspector.inspect_gestures import bind_inspect_gestures
from ai_command_center.ui.components.inspector.inspector_host import InspectorHost
from ai_command_center.ui.components.inspector.message_inspector import MessageInspector
from ai_command_center.ui.components.inspector.provider_inspector import ProviderInspector

__all__ = [
    "ArtifactInspector",
    "BaseInspector",
    "CollapsibleSection",
    "ExecutionInspector",
    "bind_inspect_gestures",
    "InspectorHost",
    "MessageInspector",
    "ProviderInspector",
]
