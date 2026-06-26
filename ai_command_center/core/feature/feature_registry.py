"""
Feature Registry Service - Phase 1 Implementation

Feature flag management following the frozen Feature contract.
"""

from __future__ import annotations

from typing import Any

from ai_command_center.core.feature.feature import (
    Feature,
    FeatureStage,
    FeatureState,
    validate_feature,
)


class FeatureRegistry:
    """
    Feature flag management.
    
    Responsibilities:
    - Register features
    - Enable/disable features
    - Check feature availability
    - Feature state management
    """

    def __init__(self) -> None:
        self._features: dict[str, FeatureState] = {}
        # Initialize all features as disabled by default
        for feature in Feature:
            self._features[feature.value] = FeatureState(
                feature=feature,
                enabled=False,
                stage=FeatureStage.EXPERIMENTAL,
                metadata={},
            )

    def register(
        self,
        feature: Feature,
        enabled: bool = False,
        stage: FeatureStage = FeatureStage.EXPERIMENTAL,
        metadata: dict[str, Any] | None = None,
    ) -> FeatureState:
        """Register or update a feature."""
        if not validate_feature(feature.value):
            raise ValueError(f"Invalid feature: {feature}")

        state = FeatureState(
            feature=feature,
            enabled=enabled,
            stage=stage,
            metadata=metadata or {},
        )
        
        self._features[feature.value] = state
        return state

    def enable(self, feature: Feature) -> FeatureState:
        """Enable a feature."""
        if not validate_feature(feature.value):
            raise ValueError(f"Invalid feature: {feature}")
        
        current = self._features.get(feature.value)
        if current:
            state = FeatureState(
                feature=feature,
                enabled=True,
                stage=current.stage,
                metadata=current.metadata,
            )
            self._features[feature.value] = state
            return state
        return self.register(feature, enabled=True)

    def disable(self, feature: Feature) -> FeatureState:
        """Disable a feature."""
        if not validate_feature(feature.value):
            raise ValueError(f"Invalid feature: {feature}")
        
        current = self._features.get(feature.value)
        if current:
            state = FeatureState(
                feature=feature,
                enabled=False,
                stage=current.stage,
                metadata=current.metadata,
            )
            self._features[feature.value] = state
            return state
        return self.register(feature, enabled=False)

    def is_enabled(self, feature: Feature) -> bool:
        """Check if a feature is enabled."""
        state = self._features.get(feature.value)
        return state.enabled if state else False

    def get_state(self, feature: Feature) -> FeatureState | None:
        """Get the state of a feature."""
        return self._features.get(feature.value)

    def list_enabled(self) -> list[FeatureState]:
        """List all enabled features."""
        return [state for state in self._features.values() if state.enabled]

    def list_disabled(self) -> list[FeatureState]:
        """List all disabled features."""
        return [state for state in self._features.values() if not state.enabled]

    def list_all(self) -> list[FeatureState]:
        """List all features."""
        return list(self._features.values())

    def set_metadata(self, feature: Feature, metadata: dict[str, Any]) -> FeatureState:
        """Set metadata for a feature."""
        current = self._features.get(feature.value)
        if current:
            state = FeatureState(
                feature=feature,
                enabled=current.enabled,
                stage=current.stage,
                metadata=metadata,
            )
            self._features[feature.value] = state
            return state
        return self.register(feature, enabled=False, metadata=metadata)
