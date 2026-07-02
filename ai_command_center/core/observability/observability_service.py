"""
Observability Service - Phase 1 Implementation

Instrumentation service for metrics and error tracking following the frozen Metric contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.observability.metric import (
    Metric,
    validate_metric_type,
)
from ai_command_center.core.event_bus import (
    EVENT_OBSERVABILITY_METRIC,
    EVENT_OBSERVABILITY_ERROR,
)


class ObservabilityService:
    """
    Observability service for instrumentation.
    
    Responsibilities:
    - Collect metrics (action execution, search latency, agent runtime, etc.)
    - Track errors
    - Event publishing for observability data
    """

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        # In-memory metrics storage (future: persist to database)
        self._metrics: list[Metric] = []

    def record_metric(
        self,
        metric_type: str,
        value: float | int,
        unit: str,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> Metric:
        """Record a metric."""
        if not validate_metric_type(metric_type):
            raise ValueError(f"Invalid metric_type: {metric_type}")
        
        metric = Metric(
            id=uuid4(),
            metric_type=metric_type,
            entity_id=entity_id,
            entity_type=entity_type,
            value=value,
            unit=unit,
            tags=tags or {},
            timestamp=datetime.utcnow(),
        )
        
        self._metrics.append(metric)
        
        # Publish event
        self._event_bus.publish(
            EVENT_OBSERVABILITY_METRIC,
            {
                "metric_id": str(metric.id),
                "metric_type": metric.metric_type,
                "value": metric.value,
                "unit": metric.unit,
                "entity_id": str(metric.entity_id) if metric.entity_id else None,
            },
            source="observability_service",
        )
        
        return metric

    def record_error(
        self,
        error_type: str,
        error_message: str,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record an error."""
        # Publish error event
        self._event_bus.publish(
            EVENT_OBSERVABILITY_ERROR,
            {
                "error_type": error_type,
                "error_message": error_message,
                "entity_id": str(entity_id) if entity_id else None,
                "entity_type": entity_type,
                "tags": tags or {},
            },
            source="observability_service",
        )

    def get_metrics_by_type(self, metric_type: str, limit: int = 100) -> list[Metric]:
        """Get metrics by type."""
        return [m for m in self._metrics if m.metric_type == metric_type][:limit]

    def get_metrics_by_entity(self, entity_id: UUID, limit: int = 100) -> list[Metric]:
        """Get metrics for a specific entity."""
        return [m for m in self._metrics if m.entity_id == entity_id][:limit]

    def get_recent_metrics(self, limit: int = 50) -> list[Metric]:
        """Get recent metrics."""
        return self._metrics[-limit:]

    def list_all_metrics(self) -> list[Metric]:
        """List all metrics."""
        return self._metrics.copy()
