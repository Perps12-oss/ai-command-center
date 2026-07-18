"""UI Constitution hardening gate for Phase 11A + 11B.

Checks that the frontend is fully wired, uses the canonical status-token system,
has no placeholder screens, exposes the required hero/ops/top-bar contracts,
and that the World Model workspace satisfies Article 12.

Exit codes:
  0 = PASS
  1 = FAIL
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UI_ROOT = REPO / "ai_command_center" / "ui"

PHASE_11A_FILES: tuple[Path, ...] = (
    UI_ROOT / "design_system" / "status_tokens.py",
    UI_ROOT / "components" / "status_pill.py",
    UI_ROOT / "components" / "top_bar.py",
    UI_ROOT / "components" / "sidebar.py",
    UI_ROOT / "views" / "command_center_view.py",
    UI_ROOT / "views" / "goal_view.py",
    UI_ROOT / "views" / "approvals_view.py",
    UI_ROOT / "views" / "agents_view.py",
    UI_ROOT / "views" / "workflow_graph_view.py",
    UI_ROOT / "components" / "graph_canvas.py",
    UI_ROOT / "shell" / "view_manager.py",
    UI_ROOT / "shell" / "state_applier.py",
    UI_ROOT / "shell" / "application_shell.py",
    UI_ROOT / "shell" / "event_coordinator.py",
    UI_ROOT / "app.py",
    UI_ROOT / "controller.py",
)

PHASE_11B_FILES: tuple[Path, ...] = (
    UI_ROOT / "views" / "world_explorer_view.py",
    UI_ROOT / "views" / "world_model" / "knowledge_graph_panel.py",
    UI_ROOT / "views" / "world_model" / "entity_explorer_panel.py",
    UI_ROOT / "views" / "world_model" / "selection_inspector_panel.py",
    UI_ROOT / "views" / "world_model" / "relationship_explorer_panel.py",
    UI_ROOT / "views" / "world_model" / "mutation_journal_panel.py",
)

PHASE_11C_FILES: tuple[Path, ...] = (
    UI_ROOT / "views" / "executions_view.py",
    UI_ROOT / "views" / "execution_center" / "execution_list_panel.py",
    UI_ROOT / "views" / "execution_center" / "execution_timeline_panel.py",
    UI_ROOT / "views" / "execution_center" / "execution_detail_panel.py",
    UI_ROOT / "views" / "execution_center" / "receipt_viewer_panel.py",
    UI_ROOT / "views" / "execution_center" / "truth_validation_panel.py",
)

PHASE_11D_FILES: tuple[Path, ...] = (
    UI_ROOT / "views" / "agents_view.py",
    UI_ROOT / "views" / "agent_monitor" / "active_agents_panel.py",
    UI_ROOT / "views" / "agent_monitor" / "agent_state_panel.py",
    UI_ROOT / "views" / "agent_monitor" / "pipeline_progress_panel.py",
    UI_ROOT / "views" / "agent_monitor" / "task_assignment_panel.py",
    UI_ROOT / "views" / "agent_monitor" / "execution_history_panel.py",
)

PHASE_11E_FILES: tuple[Path, ...] = (
    UI_ROOT / "views" / "approvals_view.py",
    UI_ROOT / "views" / "approval_center" / "pending_queue_panel.py",
    UI_ROOT / "views" / "approval_center" / "risk_classification_panel.py",
    UI_ROOT / "views" / "approval_center" / "decision_history_panel.py",
    UI_ROOT / "views" / "approval_center" / "approval_statistics_panel.py",
)

PHASE_11F_FILES: tuple[Path, ...] = (
    UI_ROOT / "views" / "goal_view.py",
    UI_ROOT / "views" / "goal_dashboard" / "goal_list_panel.py",
    UI_ROOT / "views" / "goal_dashboard" / "goal_detail_panel.py",
    UI_ROOT / "views" / "goal_dashboard" / "plan_preview_panel.py",
    UI_ROOT / "views" / "goal_dashboard" / "goal_progress_panel.py",
    UI_ROOT / "views" / "goal_dashboard" / "goal_history_panel.py",
)

PHASE_11_WORKSPACE_FILES: tuple[Path, ...] = (
    *PHASE_11A_FILES,
    *PHASE_11B_FILES,
    *PHASE_11C_FILES,
    *PHASE_11D_FILES,
    *PHASE_11E_FILES,
    *PHASE_11F_FILES,
    UI_ROOT / "views" / "surface_state.py",
    UI_ROOT / "views" / "command_center_view.py",
    UI_ROOT / "views" / "executions_view.py",
)

STATUS_TOKEN_CONSUMERS: tuple[Path, ...] = (
    UI_ROOT / "components" / "timeline_renderer.py",
    UI_ROOT / "components" / "trace_tree.py",
    UI_ROOT / "views" / "dependency_inspector_view.py",
    UI_ROOT / "views" / "chat" / "chat_header.py",
    UI_ROOT / "views" / "chat" / "tool_execution_card.py",
    UI_ROOT / "views" / "chat" / "inspector" / "inspector_provider_tab.py",
    UI_ROOT / "views" / "providers" / "provider_live_monitor.py",
)


class Violation:
    """Collects a single constitutional violation."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)

    def report(self) -> None:
        for err in self.errors:
            print(f"FAIL: {err}")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _find_local_function(text: str, name: str) -> bool:
    """Return True if a top-level function with the given name exists."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return True
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return True
    return False


def _check_no_local_status_maps(v: Violation) -> None:
    """Ensure status color logic is not duplicated in view code."""
    command_center = UI_ROOT / "views" / "command_center_view.py"
    top_bar = UI_ROOT / "components" / "top_bar.py"

    for path, names in (
        (command_center, ("_status_color", "status_color")),
        (top_bar, ("_kernel_state_to_pill", "kernel_state_to_pill")),
    ):
        text = _read(path)
        for name in names:
            if _find_local_function(text, name):
                v.add(f"{path.name} contains local status-color function {name}()")


def _check_status_tokens_usage(v: Violation) -> None:
    """Verify Phase 11A UI components import and consume status_tokens."""
    expected = UI_ROOT / "design_system" / "status_tokens.py"
    if not expected.exists():
        v.add(f"Missing {expected.relative_to(REPO)}")
        return

    for path in PHASE_11A_FILES:
        text = _read(path)
        if path.name in ("status_tokens.py", "theme_v2.py"):
            continue
        if "status_tokens" not in text and "status_badge" not in text and "status_color" not in text:
            continue
        if "status_tokens" not in text:
            v.add(f"{path.name} uses status-token helpers but does not import status_tokens")


def _check_top_bar_pills(v: Violation) -> None:
    """Verify Article 17 required pills are present in TopBar."""
    text = _read(UI_ROOT / "components" / "top_bar.py")
    required = (
        "_active_goal_btn",
        "_kernel_pill",
        "_agents_pill",
        "_approvals_pill",
        "_model_pill",
        "_provider_pill",
        "_time_label",
    )
    for name in required:
        if name not in text:
            v.add(f"TopBar missing required pill/widget: {name}")


def _check_hero_action(v: Violation) -> None:
    """Verify the Command Center hero exposes a primary action button."""
    text = _read(UI_ROOT / "views" / "command_center_view.py")
    if "_action_button" not in text:
        v.add("CommandCenterView missing hero action button (_action_button)")
    if "_resolve_hero_action" not in text:
        v.add("CommandCenterView does not dynamically resolve hero action")


def _check_ops_cards_timestamp(v: Violation) -> None:
    """Verify every operational card displays a timestamp."""
    text = _read(UI_ROOT / "views" / "command_center_view.py")
    if "_updated" not in text:
        v.add("CommandCenterView ops cards missing timestamp label")
    if "_format_relative" not in text:
        v.add("CommandCenterView ops cards missing relative-time formatter")


def _check_view_registry(v: Violation) -> None:
    """Verify every VIEW_ID is registered and no critical view is a placeholder."""
    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")

    view_ids_match = re.search(r"VIEW_IDS\s*\:\s*tuple\[str,\s*\.\.\.\]\s*=\s*\((.*?)\)", view_manager, re.S)
    if not view_ids_match:
        v.add("Could not locate VIEW_IDS in view_manager.py")
        return

    raw = view_ids_match.group(1)
    view_ids = [m.strip('"\'') for m in re.findall(r'"([^"]+)"', raw)]

    for vid in view_ids:
        if f'self._view_registry["{vid}"]' not in view_manager:
            v.add(f"View '{vid}' is in VIEW_IDS but has no registered factory")

    for vid in ("command_center", "goals", "agents", "approvals"):
        if f'self._view_registry["{vid}"] = lambda: PlaceholderView' in view_manager:
            v.add(f"View '{vid}' is still registered as PlaceholderView")


def _check_no_placeholders(v: Violation) -> None:
    """Fail if prohibited markers remain in any Phase 11 workspace source."""
    markers = ("TODO", "FIXME", "COMING_SOON", "PLACEHOLDER", "TEMP", "MOCK", "DUMMY", "STUB")
    seen: set[Path] = set()
    for path in PHASE_11_WORKSPACE_FILES:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        text = _read(path)
        for marker in markers:
            if re.search(rf"\b{re.escape(marker)}\b", text):
                v.add(f"{path.relative_to(REPO)} contains placeholder marker '{marker}'")
        if re.search(r"coming\s+soon", text, re.IGNORECASE):
            v.add(f"{path.relative_to(REPO)} contains 'coming soon' language")

    placeholder_file = UI_ROOT / "views" / "placeholder.py"
    if placeholder_file.exists() and "class PlaceholderView" in _read(placeholder_file):
        v.add(f"PlaceholderView still defined in {placeholder_file.relative_to(REPO)}")

    view_manager = UI_ROOT / "shell" / "view_manager.py"
    if "PlaceholderView" in _read(view_manager):
        v.add("view_manager.py still references PlaceholderView")

    gallery = UI_ROOT / "views" / "component_gallery_view.py"
    if gallery.exists():
        v.add("Orphan ComponentGalleryView file remains; remove or register it")


def _check_status_token_consolidation(v: Violation) -> None:
    """Require listed consumers to import status_tokens; ban local status color dicts."""
    for path in STATUS_TOKEN_CONSUMERS:
        if not path.exists():
            v.add(f"Missing status-token consumer: {path.relative_to(REPO)}")
            continue
        text = _read(path)
        if "status_tokens" not in text:
            v.add(f"{path.relative_to(REPO)} must import ai_command_center.ui.design_system.status_tokens")
        if re.search(r"_STATUS_COLORS\s*=", text) or re.search(r"_GOAL_STATUS_COLORS\s*=", text):
            v.add(f"{path.relative_to(REPO)} still defines a local status color map")
        if re.search(r"_MUTATION_COLORS\s*=", text):
            v.add(f"{path.relative_to(REPO)} still defines a local mutation color map")


def _check_command_center_naming(v: Violation) -> None:
    """Canonical workspace name is Command Center (not AI Command Center)."""
    shell = _read(UI_ROOT / "views" / "command_center_view.py")
    if 'text="AI Command Center"' in shell:
        v.add("Command Center hero title must be 'Command Center' (canonical)")
    if 'text="Command Center"' not in shell:
        v.add("Command Center hero title 'Command Center' missing")
    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    if '("command_center", "Command Center")' not in sidebar:
        v.add("Sidebar label for command_center is not 'Command Center'")
    constitution = _read(REPO / "docs" / "UI_CONSTITUTION.md")
    for token in ("GOAL_AMBER", "WORLD_TEAL", "EXECUTION_BLUE", "AGENT_PURPLE", "APPROVAL_ORANGE"):
        if token not in constitution:
            v.add(f"UI_CONSTITUTION.md missing workspace token {token}")
    theme = _read(UI_ROOT / "design_system" / "theme_v2.py")
    for token in ("GOAL_AMBER", "WORLD_TEAL", "EXECUTION_BLUE", "AGENT_PURPLE", "APPROVAL_ORANGE"):
        if token not in theme:
            v.add(f"theme_v2.py missing workspace token {token}")


def _check_route_reachability(v: Violation) -> None:
    """Ensure sidebar routes and command aliases cover the registered views."""
    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")
    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    router = _read(REPO / "ai_command_center" / "services" / "command_router_service.py")

    view_ids_match = re.search(r"VIEW_IDS\s*\:\s*tuple\[str,\s*\.\.\.\]\s*=\s*\((.*?)\)", view_manager, re.S)
    if not view_ids_match:
        v.add("Could not locate VIEW_IDS for route reachability")
        return
    view_ids = [m.strip('"\'') for m in re.findall(r'"([^"]+)"', view_ids_match.group(1))]

    for vid in view_ids:
        if vid in ("timeline", "workflow", "relationships", "dependencies", "world_explorer"):
            continue
        if vid not in sidebar:
            v.add(f"Sidebar does not expose route for '{vid}'")
        if f'"{vid}"' not in router:
            v.add(f"CommandRouter _VIEW_ALIASES does not cover '{vid}'")


def _check_theme_tokens(v: Violation) -> None:
    """Ensure Phase 11A UI views use theme tokens rather than ad-hoc hex literals."""
    theme_path = UI_ROOT / "design_system" / "theme_v2.py"
    theme_text = _read(theme_path)
    allowed_hex = set(re.findall(r"#[0-9A-Fa-f]{6}", theme_text))

    for path in PHASE_11A_FILES:
        if path.name in ("theme_v2.py", "verify_ui_constitution.py"):
            continue
        text = _read(path)
        for hex_color in re.findall(r"#[0-9A-Fa-f]{6}", text):
            if hex_color not in allowed_hex:
                v.add(f"{path.relative_to(REPO)} uses unapproved color {hex_color}")


def _check_world_model_workspace(v: Violation) -> None:
    """Verify Phase 11B / Article 12 World Model workspace contracts."""
    for path in PHASE_11B_FILES:
        if not path.exists():
            v.add(f"Missing World Model file: {path.relative_to(REPO)}")

    shell = UI_ROOT / "views" / "world_explorer_view.py"
    if not shell.exists():
        return
    text = _read(shell)

    required_symbols = (
        ("Hero", "_hero"),
        ("Knowledge Graph", "KnowledgeGraphPanel"),
        ("Entity Explorer", "EntityExplorerPanel"),
        ("Selection Inspector", "SelectionInspectorPanel"),
        ("Relationship Explorer", "RelationshipExplorerPanel"),
        ("Mutation Journal", "MutationJournalPanel"),
        ("WORLD_TEAL accent", "WORLD_TEAL"),
        ("New Entity action", "_new_entity_btn"),
        ("apply_state projection", "def apply_state"),
    )
    for label, symbol in required_symbols:
        if symbol not in text:
            v.add(f"World Model workspace missing {label} ({symbol})")

    if "from ai_command_center.core.state.world_model_state" in text:
        v.add("world_explorer_view.py must not import WorldModelState")
    if "add_listener" in text:
        v.add("world_explorer_view.py must not subscribe to mutable state listeners")
    if "WORLD_MODEL_MUTATION_APPLIED" in text:
        v.add("world_explorer_view.py must not publish WORLD_MODEL_MUTATION_APPLIED")

    # Forbidden layer access across 11B panels
    forbidden_patterns = (
        "ai_command_center.repositories",
        "ai_command_center.services",
        "from ai_command_center.core.state.world_model_state",
        "WORLD_MODEL_MUTATION_APPLIED",
    )
    for path in PHASE_11B_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        for forbidden in forbidden_patterns:
            if forbidden in panel_text:
                v.add(f"{path.relative_to(REPO)} contains forbidden symbol {forbidden}")

    # Wiring: route preserved, AppState-driven apply, create/select publishes
    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")
    if 'self._view_registry["world_explorer"]' not in view_manager:
        v.add("view_manager missing world_explorer factory")
    if "WorldModelState(self._bus)" in view_manager and "WorldExplorerView" in view_manager:
        # Factory must not inject WorldModelState into WorldExplorerView
        factory_block = re.search(
            r'self\._view_registry\["world_explorer"\]\s*=\s*lambda:.*?WorldExplorerView\((.*?)\)',
            view_manager,
            re.S,
        )
        if factory_block and "state=" in factory_block.group(1):
            v.add("WorldExplorerView factory still injects WorldModelState")

    state_applier = _read(UI_ROOT / "shell" / "state_applier.py")
    if 'current_view == "world_explorer"' not in state_applier:
        v.add("state_applier does not drive world_explorer via apply_state")

    controller = _read(UI_ROOT / "controller.py")
    if "publish_world_model_node_selected" not in controller:
        v.add("UIController missing publish_world_model_node_selected")
    if "publish_entity_create_request" not in controller:
        v.add("UIController missing publish_entity_create_request")
    if "ENTITY_CREATE_REQUEST" not in controller:
        v.add("UIController does not publish ENTITY_CREATE_REQUEST")

    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    if '("world_explorer", "World Model")' not in sidebar:
        v.add("Sidebar label for world_explorer is not 'World Model'")

    for path in PHASE_11B_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        if "WORLD_TEAL" not in panel_text and path.name != "__init__.py":
            v.add(f"{path.relative_to(REPO)} does not use WORLD_TEAL token")


def _check_execution_center_workspace(v: Violation) -> None:
    """Verify Phase 11C / Article 13 Execution Center workspace contracts."""
    for path in PHASE_11C_FILES:
        if not path.exists():
            v.add(f"Missing Execution Center file: {path.relative_to(REPO)}")

    theme = _read(UI_ROOT / "design_system" / "theme_v2.py")
    if "EXECUTION_BLUE" not in theme:
        v.add("theme_v2.py missing EXECUTION_BLUE token")

    constitution = _read(REPO / "docs" / "UI_CONSTITUTION.md")
    if "EXECUTION_BLUE" not in constitution:
        v.add("UI_CONSTITUTION.md missing EXECUTION_BLUE token reference")

    shell = UI_ROOT / "views" / "executions_view.py"
    if not shell.exists():
        return
    text = _read(shell)
    required_symbols = (
        ("Hero", "_hero"),
        ("Execution List", "ExecutionListPanel"),
        ("Timeline", "ExecutionTimelinePanel"),
        ("Detail", "ExecutionDetailPanel"),
        ("Receipt Viewer", "ReceiptViewerPanel"),
        ("Truth Validation", "TruthValidationPanel"),
        ("EXECUTION_BLUE accent", "EXECUTION_BLUE"),
        ("apply_state projection", "def apply_state"),
        ("Hero action", "_hero_action"),
    )
    for label, symbol in required_symbols:
        if symbol not in text:
            v.add(f"Execution Center workspace missing {label} ({symbol})")

    forbidden_patterns = (
        "ai_command_center.repositories",
        "ai_command_center.services",
        "WORLD_MODEL_MUTATION_APPLIED",
    )
    for path in PHASE_11C_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        for forbidden in forbidden_patterns:
            if forbidden in panel_text:
                v.add(f"{path.relative_to(REPO)} contains forbidden symbol {forbidden}")
        if path.name != "__init__.py" and "EXECUTION_BLUE" not in panel_text:
            v.add(f"{path.relative_to(REPO)} does not use EXECUTION_BLUE token")

    # Receipt/Truth must project orchestration_run, not invent models
    receipt = _read(UI_ROOT / "views" / "execution_center" / "receipt_viewer_panel.py")
    truth = _read(UI_ROOT / "views" / "execution_center" / "truth_validation_panel.py")
    if "orchestration_run" not in receipt:
        v.add("Receipt Viewer must project orchestration_run")
    if "orchestration_run" not in truth:
        v.add("Truth Validation must project orchestration_run")
    if "class Receipt" in receipt and "OrchestrationRun" not in receipt:
        v.add("Receipt Viewer must not introduce a separate receipt data model")

    status_tokens = _read(UI_ROOT / "design_system" / "status_tokens.py")
    if "def truth_validation_color" not in status_tokens:
        v.add("status_tokens.py missing truth_validation_color helper")
    if "truth_validation_color" not in truth:
        v.add("Truth Validation must use centralized truth_validation_color")

    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")
    if 'self._view_registry["executions"]' not in view_manager:
        v.add("view_manager missing executions factory")

    state_applier = _read(UI_ROOT / "shell" / "state_applier.py")
    if 'current_view == "executions"' not in state_applier:
        v.add("state_applier does not gate executions apply_state on current_view")
    if "executions.apply_state(list(snap.execution_runs))" in state_applier:
        v.add("state_applier still feeds only execution_runs list to Execution Center")

    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    if '("executions", "Execution Center")' not in sidebar:
        v.add("Sidebar label for executions is not 'Execution Center'")


def _check_agent_monitor_workspace(v: Violation) -> None:
    """Verify Phase 11D / Article 14 Agent Monitor workspace contracts."""
    for path in PHASE_11D_FILES:
        if not path.exists():
            v.add(f"Missing Agent Monitor file: {path.relative_to(REPO)}")

    theme = _read(UI_ROOT / "design_system" / "theme_v2.py")
    if "AGENT_PURPLE" not in theme:
        v.add("theme_v2.py missing AGENT_PURPLE token")

    constitution = _read(REPO / "docs" / "UI_CONSTITUTION.md")
    if "AGENT_PURPLE" not in constitution:
        v.add("UI_CONSTITUTION.md missing AGENT_PURPLE token reference")

    shell = UI_ROOT / "views" / "agents_view.py"
    if not shell.exists():
        return
    text = _read(shell)
    required_symbols = (
        ("Hero", "_hero"),
        ("Active Agents", "ActiveAgentsPanel"),
        ("Agent State", "AgentStatePanel"),
        ("Pipeline Progress", "PipelineProgressPanel"),
        ("Task Assignment", "TaskAssignmentPanel"),
        ("Execution History", "ExecutionHistoryPanel"),
        ("AGENT_PURPLE accent", "AGENT_PURPLE"),
        ("apply_state projection", "def apply_state"),
        ("Hero cancel action", "_hero_action"),
        ("Contextual cancel", "_cancel_agent_id"),
    )
    for label, symbol in required_symbols:
        if symbol not in text:
            v.add(f"Agent Monitor workspace missing {label} ({symbol})")

    if "agent_pipeline" not in text:
        v.add("agents_view.py must project AppState.agent_pipeline")

    forbidden_patterns = (
        "ai_command_center.repositories",
        "ai_command_center.services",
        "add_listener",
    )
    for path in PHASE_11D_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        for forbidden in forbidden_patterns:
            if forbidden in panel_text:
                v.add(f"{path.relative_to(REPO)} contains forbidden symbol {forbidden}")
        if path.name != "__init__.py" and "AGENT_PURPLE" not in panel_text:
            v.add(f"{path.relative_to(REPO)} does not use AGENT_PURPLE token")

    # No AppState field additions from Agent Monitor UI modules
    for path in PHASE_11D_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        if "dataclass" in panel_text and "AppState" in panel_text and "replace(" in panel_text:
            v.add(f"{path.relative_to(REPO)} must not mutate AppState")

    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")
    if 'self._view_registry["agents"]' not in view_manager:
        v.add("view_manager missing agents factory")
    if "publish_agent_cancel_request" not in view_manager and "_on_agent_cancel" not in view_manager:
        v.add("view_manager missing agent cancel wiring")

    state_applier = _read(UI_ROOT / "shell" / "state_applier.py")
    if 'current_view == "agents"' not in state_applier:
        v.add("state_applier does not gate agents apply_state on current_view")

    controller = _read(UI_ROOT / "controller.py")
    if "publish_agent_cancel_request" not in controller:
        v.add("UIController missing publish_agent_cancel_request")
    if "AGENT_CANCEL_REQUEST" not in controller:
        v.add("UIController does not publish AGENT_CANCEL_REQUEST")

    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    if '("agents", "Agent Monitor")' not in sidebar:
        v.add("Sidebar label for agents is not 'Agent Monitor'")


def _check_approval_center_workspace(v: Violation) -> None:
    """Verify Phase 11E / Article 15 Approval Center workspace contracts."""
    for path in PHASE_11E_FILES:
        if not path.exists():
            v.add(f"Missing Approval Center file: {path.relative_to(REPO)}")

    theme = _read(UI_ROOT / "design_system" / "theme_v2.py")
    if "APPROVAL_ORANGE" not in theme:
        v.add("theme_v2.py missing APPROVAL_ORANGE token")

    constitution = _read(REPO / "docs" / "UI_CONSTITUTION.md")
    if "APPROVAL_ORANGE" not in constitution:
        v.add("UI_CONSTITUTION.md missing APPROVAL_ORANGE token reference")

    shell = UI_ROOT / "views" / "approvals_view.py"
    if not shell.exists():
        return
    text = _read(shell)
    required_symbols = (
        ("Hero", "_hero"),
        ("Pending Queue", "PendingQueuePanel"),
        ("Risk Classification", "RiskClassificationPanel"),
        ("Decision History", "DecisionHistoryPanel"),
        ("Approval Statistics", "ApprovalStatisticsPanel"),
        ("APPROVAL_ORANGE accent", "APPROVAL_ORANGE"),
        ("apply_state projection", "def apply_state"),
        ("Review Next action", "_hero_action"),
        ("permission_snapshot", "permission_snapshot"),
    )
    for label, symbol in required_symbols:
        if symbol not in text:
            v.add(f"Approval Center workspace missing {label} ({symbol})")

    forbidden_patterns = (
        "ai_command_center.repositories",
        "ai_command_center.services",
        "add_listener",
    )
    for path in PHASE_11E_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        for forbidden in forbidden_patterns:
            if forbidden in panel_text:
                v.add(f"{path.relative_to(REPO)} contains forbidden symbol {forbidden}")
        if path.name != "__init__.py" and "APPROVAL_ORANGE" not in panel_text:
            v.add(f"{path.relative_to(REPO)} does not use APPROVAL_ORANGE token")

    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")
    if 'self._view_registry["approvals"]' not in view_manager:
        v.add("view_manager missing approvals factory")
    if "publish_permission_result" not in view_manager and "_on_approval_decide" not in view_manager:
        v.add("view_manager missing approval decide wiring")

    state_applier = _read(UI_ROOT / "shell" / "state_applier.py")
    if 'current_view == "approvals"' not in state_applier:
        v.add("state_applier does not gate approvals apply_state on current_view")

    controller = _read(UI_ROOT / "controller.py")
    if "publish_permission_result" not in controller:
        v.add("UIController missing publish_permission_result")
    if "PERMISSION_CHECK_RESULT" not in controller:
        v.add("UIController does not publish PERMISSION_CHECK_RESULT")

    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    if '("approvals", "Approval Center")' not in sidebar:
        v.add("Sidebar label for approvals is not 'Approval Center'")


def _check_goal_dashboard_workspace(v: Violation) -> None:
    """Verify Phase 11F / Article 16 Goal Dashboard workspace contracts."""
    for path in PHASE_11F_FILES:
        if not path.exists():
            v.add(f"Missing Goal Dashboard file: {path.relative_to(REPO)}")

    theme = _read(UI_ROOT / "design_system" / "theme_v2.py")
    if "GOAL_AMBER" not in theme:
        v.add("theme_v2.py missing GOAL_AMBER token")

    constitution = _read(REPO / "docs" / "UI_CONSTITUTION.md")
    if "GOAL_AMBER" not in constitution:
        v.add("UI_CONSTITUTION.md missing GOAL_AMBER token reference")

    shell = UI_ROOT / "views" / "goal_view.py"
    if not shell.exists():
        return
    text = _read(shell)
    required_symbols = (
        ("Hero", "_hero"),
        ("Goal List", "GoalListPanel"),
        ("Goal Detail", "GoalDetailPanel"),
        ("Plan Preview", "PlanPreviewPanel"),
        ("Goal Progress", "GoalProgressPanel"),
        ("Goal History", "GoalHistoryPanel"),
        ("GOAL_AMBER accent", "GOAL_AMBER"),
        ("apply_state projection", "def apply_state"),
        ("New Goal action", "_hero_action"),
        ("brain_state projection", "brain_state"),
        ("surface state banner", "_surface_state"),
    )
    for label, symbol in required_symbols:
        if symbol not in text:
            v.add(f"Goal Dashboard workspace missing {label} ({symbol})")

    if "GOAL_ACTIVATED" in text or "GOAL_PAUSED" in text or "GOAL_CANCELLED" in text:
        v.add("goal_view.py must not publish lifecycle fact topics")

    forbidden_patterns = (
        "ai_command_center.repositories",
        "ai_command_center.services",
        "add_listener",
    )
    for path in PHASE_11F_FILES:
        if not path.exists():
            continue
        panel_text = _read(path)
        for forbidden in forbidden_patterns:
            if forbidden in panel_text:
                v.add(f"{path.relative_to(REPO)} contains forbidden symbol {forbidden}")
        if path.name not in {"__init__.py", "goal_sorting.py"} and "GOAL_AMBER" not in panel_text:
            v.add(f"{path.relative_to(REPO)} does not use GOAL_AMBER token")

    view_manager = _read(UI_ROOT / "shell" / "view_manager.py")
    if 'self._view_registry["goals"]' not in view_manager:
        v.add("view_manager missing goals factory")
    if "_on_goal_new" not in view_manager and "publish_goal_submit_request" not in view_manager:
        v.add("view_manager missing goal New Goal wiring")

    state_applier = _read(UI_ROOT / "shell" / "state_applier.py")
    if 'current_view == "goals"' not in state_applier:
        v.add("state_applier does not gate goals apply_state on current_view")

    controller = _read(UI_ROOT / "controller.py")
    if "publish_goal_submit_request" not in controller:
        v.add("UIController missing publish_goal_submit_request")
    if "GOAL_SUBMIT_REQUEST" not in controller:
        v.add("UIController does not publish GOAL_SUBMIT_REQUEST")

    sidebar = _read(UI_ROOT / "components" / "sidebar.py")
    if '("goals", "Goal Dashboard")' not in sidebar:
        v.add("Sidebar label for goals is not 'Goal Dashboard'")


def main() -> int:
    v = Violation()
    _check_no_local_status_maps(v)
    _check_status_tokens_usage(v)
    _check_status_token_consolidation(v)
    _check_top_bar_pills(v)
    _check_hero_action(v)
    _check_ops_cards_timestamp(v)
    _check_view_registry(v)
    _check_no_placeholders(v)
    _check_command_center_naming(v)
    _check_route_reachability(v)
    _check_theme_tokens(v)
    _check_world_model_workspace(v)
    _check_execution_center_workspace(v)
    _check_agent_monitor_workspace(v)
    _check_approval_center_workspace(v)
    _check_goal_dashboard_workspace(v)

    if v.errors:
        v.report()
        print(f"\nUI Constitution gate failed with {len(v.errors)} violation(s).")
        return 1

    print("UI Constitution gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
