"""
Observability Metric Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the Metric contract for the Workspace Operating System.
Observability layer provides instrumentation for all major operations.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Metric:
    """
    Observability metric - instrumentation data.
    
    Metrics to track:
    - Action execution count and duration
    - Search latency (by provider)
    - Agent runtime and token usage
    - Plugin errors and load times
    - Workflow success/failure rates
    - Entity creation/deletion rates
    - Workspace switching patterns
    """

    id: UUID
    metric_type: str  # action_execution, search_latency, agent_runtime, etc.

    entity_id: UUID | None
    entity_type: str | None

    value: float | int
    unit: str  # ms, count, bytes, etc.

    tags: dict[str, str]

    timestamp: datetime


# Metric types
METRIC_TYPE_ACTION_EXECUTION = "action_execution"
METRIC_TYPE_SEARCH_LATENCY = "search_latency"
METRIC_TYPE_AGENT_RUNTIME = "agent_runtime"
METRIC_TYPE_PLUGIN_ERROR = "plugin_error"
METRIC_TYPE_WORKFLOW_SUCCESS = "workflow_success"
METRIC_TYPE_WORKFLOW_FAILURE = "workflow_failure"
METRIC_TYPE_ENTITY_CREATED = "entity_created"
METRIC_TYPE_ENTITY_DELETED = "entity_deleted"
METRIC_TYPE_WORKSPACE_SWITCH = "workspace_switch"

# Valid metric types for validation
VALID_METRIC_TYPES = {
    METRIC_TYPE_ACTION_EXECUTION,
    METRIC_TYPE_SEARCH_LATENCY,
    METRIC_TYPE_AGENT_RUNTIME,
    METRIC_TYPE_PLUGIN_ERROR,
    METRIC_TYPE_WORKFLOW_SUCCESS,
    METRIC_TYPE_WORKFLOW_FAILURE,
    METRIC_TYPE_ENTITY_CREATED,
    METRIC_TYPE_ENTITY_DELETED,
    METRIC_TYPE_WORKSPACE_SWITCH,
}

# Common units
UNIT_MILLISECONDS = "ms"
UNIT_COUNT = "count"
UNIT_BYTES = "bytes"
UNIT_PERCENT = "percent"
UNIT_TOKENS = "tokens"


def validate_metric_type(metric_type: str) -> bool:
    """Validate that metric_type is a recognized metric type."""
    return metric_type in VALID_METRIC_TYPES
