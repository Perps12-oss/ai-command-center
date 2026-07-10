"""World State Model — structures for planner perception of the world.

This module defines the state structures through which the Planner perceives
the world. Per ACC Planner Constitution Phase C0:
- 02_WORLD_STATE_MODEL.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MemoryInfo:
    """Memory usage information."""

    total_mb: int = 0
    available_mb: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalMb": self.total_mb,
            "availableMb": self.available_mb,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryInfo:
        return cls(
            total_mb=int(data.get("totalMb", 0)),
            available_mb=int(data.get("availableMb", 0)),
        )


@dataclass(frozen=True, slots=True)
class CpuInfo:
    """CPU usage information."""

    cores: int = 0
    usage_percent: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cores": self.cores,
            "usagePercent": self.usage_percent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CpuInfo:
        return cls(
            cores=int(data.get("cores", 0)),
            usage_percent=float(data.get("usagePercent", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class NetworkInfo:
    """Network connectivity information."""

    connected: bool = False
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "latencyMs": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NetworkInfo:
        return cls(
            connected=bool(data.get("connected", False)),
            latency_ms=int(data.get("latencyMs", 0)),
        )


@dataclass(frozen=True, slots=True)
class EnvironmentState:
    """System-level state for the planner."""

    hostname: str = ""
    platform: str = ""  # windows, mac, linux
    os_version: str = ""
    architecture: str = ""  # arm64, x86_64
    memory: MemoryInfo = field(default_factory=MemoryInfo)
    cpu: CpuInfo = field(default_factory=CpuInfo)
    network: NetworkInfo = field(default_factory=NetworkInfo)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "platform": self.platform,
            "osVersion": self.os_version,
            "architecture": self.architecture,
            "memory": self.memory.to_dict(),
            "cpu": self.cpu.to_dict(),
            "network": self.network.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvironmentState:
        return cls(
            hostname=str(data.get("hostname", "")),
            platform=str(data.get("platform", "")),
            os_version=str(data.get("osVersion", "")),
            architecture=str(data.get("architecture", "")),
            memory=MemoryInfo.from_dict(data.get("memory") or {}),
            cpu=CpuInfo.from_dict(data.get("cpu") or {}),
            network=NetworkInfo.from_dict(data.get("network") or {}),
        )


@dataclass(frozen=True, slots=True)
class EntityInfo:
    """Information about a workspace entity."""

    entity_id: str
    entity_type: str  # file, directory, module, package
    name: str
    path: str
    last_modified: str = ""  # ISO8601
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.entity_id,
            "type": self.entity_type,
            "name": self.name,
            "path": self.path,
            "lastModified": self.last_modified,
            "sizeBytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityInfo:
        return cls(
            entity_id=str(data["id"]),
            entity_type=str(data["type"]),
            name=str(data["name"]),
            path=str(data["path"]),
            last_modified=str(data.get("lastModified", "")),
            size_bytes=int(data.get("sizeBytes", 0)),
        )


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    """Information about a project in the workspace."""

    project_id: str
    name: str
    path: str
    project_type: str = ""  # python, javascript, rust, etc.
    entities: tuple[EntityInfo, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    config_files: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.project_id,
            "name": self.name,
            "path": self.path,
            "type": self.project_type,
            "entities": [e.to_dict() for e in self.entities],
            "dependencies": list(self.dependencies),
            "configFiles": list(self.config_files),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectInfo:
        return cls(
            project_id=str(data["id"]),
            name=str(data["name"]),
            path=str(data["path"]),
            project_type=str(data.get("type", "")),
            entities=tuple(EntityInfo.from_dict(e) for e in data.get("entities") or []),
            dependencies=tuple(str(d) for d in data.get("dependencies") or []),
            config_files=tuple(str(c) for c in data.get("configFiles") or []),
        )


@dataclass(frozen=True, slots=True)
class FileInfo:
    """Information about a file."""

    file_id: str
    path: str
    file_type: str = ""  # source, config, data, doc
    format_type: str = ""  # json, yaml, toml, etc.
    size_bytes: int = 0
    last_modified: str = ""  # ISO8601
    language: str = ""  # python, javascript, etc.
    imports: tuple[str, ...] = field(default_factory=tuple)
    exports: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.file_id,
            "path": self.path,
            "type": self.file_type,
            "format": self.format_type,
            "sizeBytes": self.size_bytes,
            "lastModified": self.last_modified,
            "language": self.language,
            "imports": list(self.imports),
            "exports": list(self.exports),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileInfo:
        return cls(
            file_id=str(data["id"]),
            path=str(data["path"]),
            file_type=str(data.get("type", "")),
            format_type=str(data.get("format", "")),
            size_bytes=int(data.get("sizeBytes", 0)),
            last_modified=str(data.get("lastModified", "")),
            language=str(data.get("language", "")),
            imports=tuple(str(i) for i in data.get("imports") or []),
            exports=tuple(str(e) for e in data.get("exports") or []),
        )


@dataclass(frozen=True, slots=True)
class SecretInfo:
    """Information about a known secret (without exposing the value)."""

    secret_id: str
    name: str
    secret_type: str = ""  # api_key, token, credential
    has_value: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.secret_id,
            "name": self.name,
            "type": self.secret_type,
            "hasValue": self.has_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SecretInfo:
        return cls(
            secret_id=str(data["id"]),
            name=str(data["name"]),
            secret_type=str(data.get("type", "")),
            has_value=bool(data.get("hasValue", True)),
        )


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """Information about a running process."""

    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpuPercent": self.cpu_percent,
            "memoryMb": self.memory_mb,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessInfo:
        return cls(
            pid=int(data["pid"]),
            name=str(data["name"]),
            cpu_percent=float(data.get("cpuPercent", 0.0)),
            memory_mb=int(data.get("memoryMb", 0)),
        )


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    """Workspace-level state for the planner."""

    workspace_root: str = ""
    projects: tuple[ProjectInfo, ...] = field(default_factory=tuple)
    files: tuple[FileInfo, ...] = field(default_factory=tuple)
    secrets: tuple[SecretInfo, ...] = field(default_factory=tuple)
    active_processes: tuple[ProcessInfo, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspaceRoot": self.workspace_root,
            "projects": [p.to_dict() for p in self.projects],
            "files": [f.to_dict() for f in self.files],
            "secrets": [s.to_dict() for s in self.secrets],
            "activeProcesses": [p.to_dict() for p in self.active_processes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceState:
        return cls(
            workspace_root=str(data.get("workspaceRoot", "")),
            projects=tuple(ProjectInfo.from_dict(p) for p in data.get("projects") or []),
            files=tuple(FileInfo.from_dict(f) for f in data.get("files") or []),
            secrets=tuple(SecretInfo.from_dict(s) for s in data.get("secrets") or []),
            active_processes=tuple(
                ProcessInfo.from_dict(p) for p in data.get("activeProcesses") or []
            ),
        )


@dataclass(frozen=True, slots=True)
class UserPreference:
    """User preference information."""

    style: str = "normal"  # concise, detailed
    confirmation_level: str = "normal"  # minimal, normal, strict
    timezone: str = "UTC"

    def to_dict(self) -> dict[str, Any]:
        return {
            "style": self.style,
            "confirmationLevel": self.confirmation_level,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPreference:
        return cls(
            style=str(data.get("style", "normal")),
            confirmation_level=str(data.get("confirmationLevel", "normal")),
            timezone=str(data.get("timezone", "UTC")),
        )


@dataclass(frozen=True, slots=True)
class Permission:
    """User permission scope."""

    scope: str = ""  # read, write, admin
    resources: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "resources": list(self.resources),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Permission:
        return cls(
            scope=str(data.get("scope", "")),
            resources=tuple(str(r) for r in data.get("resources") or []),
        )


@dataclass(frozen=True, slots=True)
class RecentActivity:
    """Recent user activity."""

    action: str = ""  # edit, create, delete
    entity_id: str = ""
    timestamp: str = ""  # ISO8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "entityId": self.entity_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecentActivity:
        return cls(
            action=str(data.get("action", "")),
            entity_id=str(data.get("entityId", "")),
            timestamp=str(data.get("timestamp", "")),
        )


@dataclass(frozen=True, slots=True)
class UserContext:
    """User-specific context for planning."""

    user_id: str = ""
    user_name: str = ""
    preferences: UserPreference = field(default_factory=UserPreference)
    permissions: tuple[Permission, ...] = field(default_factory=tuple)
    recent_activity: tuple[RecentActivity, ...] = field(default_factory=tuple)
    skills: tuple[str, ...] = field(default_factory=tuple)
    knowledge_domains: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "userName": self.user_name,
            "preferences": self.preferences.to_dict(),
            "permissions": [p.to_dict() for p in self.permissions],
            "recentActivity": [a.to_dict() for a in self.recent_activity],
            "skills": list(self.skills),
            "knowledgeDomains": list(self.knowledge_domains),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserContext:
        return cls(
            user_id=str(data.get("userId", "")),
            user_name=str(data.get("userName", "")),
            preferences=UserPreference.from_dict(data.get("preferences") or {}),
            permissions=tuple(Permission.from_dict(p) for p in data.get("permissions") or []),
            recent_activity=tuple(
                RecentActivity.from_dict(a) for a in data.get("recentActivity") or []
            ),
            skills=tuple(str(s) for s in data.get("skills") or []),
            knowledge_domains=tuple(str(d) for d in data.get("knowledgeDomains") or []),
        )


@dataclass(frozen=True, slots=True)
class Deadline:
    """A time-bound deadline."""

    deadline_id: str
    description: str = ""
    due_time: str = ""  # ISO8601
    urgency: str = "normal"  # critical, high, normal, low
    associated_goal_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.deadline_id,
            "description": self.description,
            "dueTime": self.due_time,
            "urgency": self.urgency,
            "associatedGoalId": self.associated_goal_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Deadline:
        return cls(
            deadline_id=str(data["id"]),
            description=str(data.get("description", "")),
            due_time=str(data.get("dueTime", "")),
            urgency=str(data.get("urgency", "normal")),
            associated_goal_id=str(data.get("associatedGoalId", "")),
        )


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    """A scheduled calendar event."""

    event_id: str
    title: str = ""
    start_time: str = ""  # ISO8601
    end_time: str = ""  # ISO8601
    recurring: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.event_id,
            "title": self.title,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "recurring": self.recurring,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledEvent:
        return cls(
            event_id=str(data["id"]),
            title=str(data.get("title", "")),
            start_time=str(data.get("startTime", "")),
            end_time=str(data.get("endTime", "")),
            recurring=bool(data.get("recurring", False)),
        )


@dataclass(frozen=True, slots=True)
class TemporalContext:
    """Time-related state for the planner."""

    current_time: str = ""  # ISO8601
    timezone: str = "UTC"
    deadlines: tuple[Deadline, ...] = field(default_factory=tuple)
    scheduled_events: tuple[ScheduledEvent, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "currentTime": self.current_time,
            "timezone": self.timezone,
            "deadlines": [d.to_dict() for d in self.deadlines],
            "scheduledEvents": [e.to_dict() for e in self.scheduled_events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemporalContext:
        return cls(
            current_time=str(data.get("currentTime", "")),
            timezone=str(data.get("timezone", "UTC")),
            deadlines=tuple(Deadline.from_dict(d) for d in data.get("deadlines") or []),
            scheduled_events=tuple(
                ScheduledEvent.from_dict(e) for e in data.get("scheduledEvents") or []
            ),
        )


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A node in the relationship graph."""

    entity_id: str
    entity_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entityId": self.entity_id,
            "entityType": self.entity_type,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        return cls(
            entity_id=str(data["entityId"]),
            entity_type=str(data.get("entityType", "")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """An edge in the relationship graph."""

    source_id: str
    target_id: str
    relationship_type: str = ""  # imports, depends_on, contains, etc.
    strength: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "targetId": self.target_id,
            "relationshipType": self.relationship_type,
            "strength": self.strength,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        return cls(
            source_id=str(data["sourceId"]),
            target_id=str(data["targetId"]),
            relationship_type=str(data.get("relationshipType", "")),
            strength=float(data.get("strength", 1.0)),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class RelationshipGraph:
    """The entity relationship graph."""

    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelationshipGraph:
        return cls(
            nodes=tuple(GraphNode.from_dict(n) for n in data.get("nodes") or []),
            edges=tuple(GraphEdge.from_dict(e) for e in data.get("edges") or []),
        )


@dataclass(frozen=True, slots=True)
class RelationshipContext:
    """Relationship graph context for planning."""

    graph: RelationshipGraph = field(default_factory=RelationshipGraph)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph": self.graph.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelationshipContext:
        return cls(
            graph=RelationshipGraph.from_dict(data.get("graph") or {}),
        )


@dataclass(frozen=True, slots=True)
class ConfidenceFactors:
    """Factors contributing to state confidence."""

    data_freshness: float = 1.0
    data_completeness: float = 1.0
    source_reliability: float = 1.0
    temporal_relevance: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataFreshness": self.data_freshness,
            "dataCompleteness": self.data_completeness,
            "sourceReliability": self.source_reliability,
            "temporalRelevance": self.temporal_relevance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfidenceFactors:
        return cls(
            data_freshness=float(data.get("dataFreshness", 1.0)),
            data_completeness=float(data.get("dataCompleteness", 1.0)),
            source_reliability=float(data.get("sourceReliability", 1.0)),
            temporal_relevance=float(data.get("temporalRelevance", 1.0)),
        )


@dataclass(frozen=True, slots=True)
class StateConfidence:
    """Overall confidence score for the world state."""

    overall: float = 1.0
    factors: ConfidenceFactors = field(default_factory=ConfidenceFactors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "factors": self.factors.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateConfidence:
        return cls(
            overall=float(data.get("overall", 1.0)),
            factors=ConfidenceFactors.from_dict(data.get("factors") or {}),
        )


@dataclass(frozen=True, slots=True)
class WorldState:
    """The top-level world state container for the planner.

    This is the primary state structure that the Planner reasons about.
    """

    world_state_id: str
    timestamp: str = ""  # ISO8601
    confidence: StateConfidence = field(default_factory=StateConfidence)
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    workspace: WorkspaceState = field(default_factory=WorkspaceState)
    temporal: TemporalContext = field(default_factory=TemporalContext)
    relationships: RelationshipContext = field(default_factory=RelationshipContext)
    user: UserContext = field(default_factory=UserContext)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worldStateId": self.world_state_id,
            "timestamp": self.timestamp,
            "confidence": self.confidence.to_dict(),
            "environment": self.environment.to_dict(),
            "workspace": self.workspace.to_dict(),
            "temporal": self.temporal.to_dict(),
            "relationships": self.relationships.to_dict(),
            "user": self.user.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldState:
        return cls(
            world_state_id=str(data.get("worldStateId", "")),
            timestamp=str(data.get("timestamp", "")),
            confidence=StateConfidence.from_dict(data.get("confidence") or {}),
            environment=EnvironmentState.from_dict(data.get("environment") or {}),
            workspace=WorkspaceState.from_dict(data.get("workspace") or {}),
            temporal=TemporalContext.from_dict(data.get("temporal") or {}),
            relationships=RelationshipContext.from_dict(data.get("relationships") or {}),
            user=UserContext.from_dict(data.get("user") or {}),
        )

    def is_reliable(self, threshold: float = 0.8) -> bool:
        """Check if the state confidence is above the threshold."""
        return self.confidence.overall >= threshold
