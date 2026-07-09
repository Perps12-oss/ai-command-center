"""Service factory — owns all repository and service wiring.

Adding a new service requires only editing this file, not ``application.py``.
The factory returns a ``ServiceManager`` with all services registered and
the shared singletons (ollama, workspace_os) that callers may need.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ai_command_center.core.action.action_registry import ActionRegistry
from ai_command_center.core.ai.capability_registry_service import (
    AICapabilityRegistryService,
)
from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.feature.feature import Feature
from ai_command_center.core.feature.feature_registry import FeatureRegistry
from ai_command_center.core.observability.observability_service import (
    ObservabilityService,
)
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.core.relationship.relationship_repository import (
    RelationshipRepository,
)
from ai_command_center.core.relationship.relationship_service import RelationshipService
from ai_command_center.core.search.command_palette_service import CommandPaletteService
from ai_command_center.core.search.search_provider import FTSSearchProvider
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.core.snapshot.snapshot_service import SnapshotService
from ai_command_center.core.timeline.timeline_repository import TimelineRepository
from ai_command_center.core.timeline.timeline_service import TimelineService
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.core.workspace_os_service import WorkspaceOsService
from ai_command_center.repositories.conversation_repository import ConversationRepository
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.repositories.note_repository import NoteRepository
from ai_command_center.repositories.plugin_manifest_repository import (
    PluginManifestRepository,
)
from ai_command_center.repositories.runtime_provider_manifest_repository import (
    RuntimeProviderManifestRepository,
)
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository
from ai_command_center.repositories.workflow_run_repository import WorkflowRunRepository
from ai_command_center.runtime.provider_registry import RuntimeProviderRegistry
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.services.agent_runtime_service import AgentRuntimeService
from ai_command_center.services.artifact_service import ArtifactService
from ai_command_center.services.execution_event_service import ExecutionEventService
from ai_command_center.services.runtime_capability_router_service import RuntimeCapabilityRouterService
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.capability_lifecycle_manager import CapabilityLifecycleManager
from ai_command_center.services.capability_prompt_catalog_service import (
    CapabilityPromptCatalogService,
)
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.external_capability_bridge_service import (
    ExternalCapabilityBridgeService,
)
from ai_command_center.services.planner_service import PlannerService
from ai_command_center.services.chat_export_service import ChatExportService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.memory_graph_service import MemoryGraphService
from ai_command_center.services.model_router_service import ModelRouterService
from ai_command_center.providers.provider_registry import ProviderRegistry, build_default_registry
from ai_command_center.services.obsidian_service import ObsidianService
from ai_command_center.services.ollama_http_service import OllamaHttpService
from ai_command_center.services.openai_http_service import OpenAIHttpService
from ai_command_center.services.plugin_registry_service import PluginRegistryService
from ai_command_center.services.qwenpaw_sidecar_service import QwenPawSidecarService
from ai_command_center.services.runtime_provider_registry_service import (
    RuntimeProviderRegistryService,
)
from ai_command_center.services.session_service import SessionService
from ai_command_center.core.settings.settings_service import SettingsService as CoreSettingsService
from ai_command_center.services.settings_service import SettingsService
from ai_command_center.services.shell_tool_service import ShellToolService
from ai_command_center.services.system_monitor_service import SystemMonitorService
from ai_command_center.services.telemetry_service import TelemetryService
from ai_command_center.services.execution_run_service import ExecutionRunService
from ai_command_center.services.execution_query_service import ExecutionQueryService
from ai_command_center.telemetry.tracing_service import TracingService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.services.tool_registry_service import ToolRegistryService
from ai_command_center.services.workflow_engine_service import WorkflowEngineService
from ai_command_center.services.workflow_persistence_service import WorkflowPersistenceService
from ai_command_center.tools.tool_registry import ToolRegistry


@dataclass
class WiredServices:
    """Output of ``build_services`` — exposes the manager and shared singletons."""

    services: ServiceManager
    ollama: OllamaHttpService
    provider_registry: ProviderRegistry = field(default_factory=build_default_registry)
    workspace_os: WorkspaceOsService | None = field(default=None)


def build_services(
    db: sqlite3.Connection,
    bus: EventBus,
    *,
    workspace_os_enabled: bool = True,
) -> WiredServices:
    """Instantiate all repositories and services; register them with a new
    ``ServiceManager``.  Returns a ``WiredServices`` dataclass so callers
    can access shared singletons without reaching into the manager by name.
    """
    services = ServiceManager(bus)

    # ── repositories ──────────────────────────────────────────────────────────
    settings_repo = SettingsRepository(db)
    core_settings = CoreSettingsService(repo=settings_repo)
    settings_snapshot = core_settings.get_snapshot()
    note_repo = NoteRepository(db)
    memory_repo = MemoryRepository(db)
    conv_repo = ConversationRepository(db)
    plugin_repo = PluginManifestRepository(db)
    runtime_provider_repo = RuntimeProviderManifestRepository(db)

    # ── shared singletons ─────────────────────────────────────────────────────
    context_manager = ContextManager()
    shared_tool_registry = ToolRegistry()
    provider_registry = build_default_registry()
    ollama = OllamaHttpService(bus)
    openai = OpenAIHttpService(bus)

    # ── core services ─────────────────────────────────────────────────────────
    permission_service = PermissionService(bus)
    permission_service.wire_bus_handlers()
    ai_capability_registry_service = AICapabilityRegistryService(permission_service)

    tool_registry = ToolRegistryService(bus, registry=shared_tool_registry)
    tool_executor = ToolExecutorService(
        bus, shared_tool_registry, permission_service=permission_service
    )
    obsidian = ObsidianService(bus, note_repo)
    context_assembler = CapabilityContextAssembler(bus, context_manager, obsidian=obsidian)
    memory_graph = MemoryGraphService(bus, memory_repo)
    session = SessionService(bus, conv_repo)
    plugins = PluginRegistryService(bus, repo=plugin_repo)
    telemetry = TelemetryService(bus, TelemetryRepository(db))
    tracing = TracingService(
        bus,
        enabled=settings_snapshot.otel_enabled,
        otel_endpoint=settings_snapshot.otel_endpoint,
    )
    capability_lifecycle = CapabilityLifecycleManager(bus)
    capability_prompt_catalog = CapabilityPromptCatalogService(
        bus,
        tool_registry=shared_tool_registry,
        ai_capability_registry=ai_capability_registry_service,
    )
    planner = PlannerService(bus, context_manager=context_manager)
    execution_orchestrator = ExecutionOrchestratorService(bus)
    external_capability_bridge = ExternalCapabilityBridgeService(bus)
    execution_run = ExecutionRunService(bus, repo=ExecutionRunRepository(db))
    execution_event_repo = ExecutionEventRepository(db)
    execution_query = ExecutionQueryService(
        bus,
        run_repo=ExecutionRunRepository(db),
        event_repo=execution_event_repo,
    )
    workflow_persistence = WorkflowPersistenceService(bus, repo=WorkflowRunRepository(db))
    artifact = ArtifactService(bus, repo=ArtifactRepository(db))
    execution_event = ExecutionEventService(bus, repo=execution_event_repo)
    system_monitor = SystemMonitorService(bus)
    chat_export = ChatExportService(bus)

    model_router = ModelRouterService(bus, provider_registry)
    agent_runtime = AgentRuntimeService(bus)
    workflow_engine = WorkflowEngineService(bus)
    qwenpaw_health = QwenPawSidecarHealthState()
    runtime_registry = RuntimeProviderRegistry()
    runtime_provider_registry = RuntimeProviderRegistryService(
        bus,
        registry=runtime_registry,
        repo=runtime_provider_repo,
        qwenpaw_health=qwenpaw_health,
    )
    capability_router = RuntimeCapabilityRouterService(
        bus,
        provider_registry=runtime_registry,
        context_manager=context_manager,
        context_assembler=context_assembler,
    )
    orchestration = OrchestrationService(bus)
    qwenpaw_sidecar = QwenPawSidecarService(bus, health_state=qwenpaw_health)
    # PermissionService wired above with tool_executor.

    for svc in (
        telemetry,
        tracing,
        capability_lifecycle,
        capability_prompt_catalog,
        planner,
        execution_orchestrator,
        external_capability_bridge,
        execution_run,
        execution_query,
        workflow_persistence,
        artifact,
        execution_event,
        chat_export,
        system_monitor,
        SettingsService(bus, settings_repo),
        CommandRouterService(bus),
        orchestration,
        runtime_provider_registry,
        capability_router,
        qwenpaw_sidecar,
        model_router,
        tool_registry,
        tool_executor,
        workflow_engine,
        ShellToolService(bus),
        plugins,
        ollama,
        openai,
        obsidian,
        memory_graph,
        session,
        agent_runtime,
        ChatHandlerService(bus, context_manager, obsidian, context_assembler=context_assembler),
    ):
        services.register(svc)

    # ── Workspace OS (optional) ───────────────────────────────────────────────
    workspace_os: WorkspaceOsService | None = None
    if workspace_os_enabled:
        entity_repo = EntityRepository(db)
        relationship_repo = RelationshipRepository(db)
        timeline_repo = TimelineRepository(db)

        entity_service = EntityService(entity_repo, bus)
        relationship_service = RelationshipService(relationship_repo, bus)
        workspace_service = WorkspaceService(entity_service, bus)
        action_registry = ActionRegistry(bus)
        timeline_service = TimelineService(timeline_repo, bus)
        observability_service = ObservabilityService(bus)
        snapshot_service = SnapshotService(db, bus)
        feature_registry = FeatureRegistry()
        FeatureRegistry.set_instance(feature_registry)
        feature_registry.enable(Feature.FEATURE_DOCKING)
        command_palette_service = CommandPaletteService(bus)
        search_provider = FTSSearchProvider(entity_service)

        register_entity_bus_handlers(
            bus,
            entity_service=entity_service,
            relationship_service=relationship_service,
            workspace_service=workspace_service,
            timeline_service=timeline_service,
            action_registry=action_registry,
        )

        workspace_os = WorkspaceOsService(
            bus=bus,
            entity_service=entity_service,
            relationship_service=relationship_service,
            workspace_service=workspace_service,
            action_registry=action_registry,
            timeline_service=timeline_service,
            permission_service=permission_service,
            observability_service=observability_service,
            snapshot_service=snapshot_service,
            feature_registry=feature_registry,
            ai_capability_registry_service=ai_capability_registry_service,
            command_palette_service=command_palette_service,
            search_provider=search_provider,
        )
        services.register(workspace_os)

    return WiredServices(
        services=services,
        ollama=ollama,
        provider_registry=provider_registry,
        workspace_os=workspace_os,
    )

