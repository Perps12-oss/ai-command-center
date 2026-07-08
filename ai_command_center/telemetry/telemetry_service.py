"""Telemetry package entry — re-exports the bus-facing service.

Canonical implementation: ``services.telemetry_service.TelemetryService``.
Import from here or ``services``; both resolve to the same class.
"""

from ai_command_center.services.telemetry_service import TelemetryService

__all__ = ["TelemetryService"]
