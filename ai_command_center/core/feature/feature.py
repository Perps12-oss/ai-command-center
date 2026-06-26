"""
Feature Registry Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the Feature registry for the Workspace Operating System.
Feature flags are the source of truth for available capabilities.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FeatureStage(Enum):
    """Maturity stage for a feature flag."""

    EXPERIMENTAL = "experimental"
    BETA = "beta"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class Feature(Enum):
    """
    Feature flags - source of truth for available capabilities.
    
    Use Cases:
    - Plugin feature detection
    - UI composition (hide unavailable features)
    - Feature flags (gradual rollout)
    - Capability checks before actions
    """

    # Core features
    FEATURE_ENTITY_SYSTEM = "entity_system"
    FEATURE_RELATIONSHIP_ENGINE = "relationship_engine"
    FEATURE_ACTION_SYSTEM = "action_system"

    # Search features
    FEATURE_FTS_SEARCH = "fts_search"
    FEATURE_FUZZY_SEARCH = "fuzzy_search"
    FEATURE_VECTOR_SEARCH = "vector_search"
    FEATURE_GRAPH_SEARCH = "graph_search"

    # Workspace features
    FEATURE_WORKSPACES = "workspaces"
    FEATURE_WORKSPACE_LAYOUTS = "workspace_layouts"

    # Knowledge features
    FEATURE_KNOWLEDGE_GRAPH = "knowledge_graph"
    FEATURE_TAG_ENTITIES = "tag_entities"

    # AI features
    FEATURE_AGENTS = "agents"
    FEATURE_PROMPT_SYSTEM = "prompt_system"
    FEATURE_AI_CAPABILITIES = "ai_capabilities"

    # Automation features
    FEATURE_WORKFLOWS = "workflows"
    FEATURE_WORKFLOW_TRIGGERS = "workflow_triggers"

    # Extensibility features
    FEATURE_PLUGINS = "plugins"
    FEATURE_EXTERNAL_INTEGRATIONS = "external_integrations"

    # Advanced features
    FEATURE_GRAPH_VIEW = "graph_view"
    FEATURE_ANALYTICS = "analytics"
    FEATURE_DOCKING = "docking"


@dataclass(frozen=True, slots=True)
class FeatureState:
    """
    Feature state - enabled/disabled with metadata and maturity stage.
    """

    feature: Feature
    enabled: bool
    stage: FeatureStage
    metadata: dict[str, Any]


# Valid features for validation
VALID_FEATURES = {feature.value for feature in Feature}


def validate_feature(feature: str) -> bool:
    """Validate that feature is a recognized Feature."""
    return feature in VALID_FEATURES
