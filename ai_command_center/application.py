"""Application bootstrap - wires core layer without UI.

Service and repository wiring lives in ``core.service_factory``.
Add new services there; this file only orchestrates startup/shutdown.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.core.state.system_snapshot_builder import SystemSnapshotBuilder
from ai_command_center.core.workspace_os_service import WorkspaceOsService
from ai_command_center.db.connection import init_database


@dataclass
class ApplicationCore:
    """
    Composition root. Only this module constructs repositories.
    Public surface: bus, state_store, services - not repositories.
    """

    bus: EventBus
    state_store: AppStateStore
    services: ServiceManager
    db: sqlite3.Connection
    workspace_os: WorkspaceOsService | None = None

    def startup(self) -> None:
        self.bus.publish("app.phase", {"phase": "starting"}, source="application")
        self.services.load_all()
        SystemSnapshotBuilder(self.bus).publish(state_store=self.state_store)
        self.bus.publish("app.phase", {"phase": "ready"}, source="application")

    def shutdown(self) -> None:
        self.services.shutdown()
        self.state_store.close()
        self.db.close()
        self.bus.publish("app.phase", {"phase": "stopped"}, source="application")


def create_application(
    *,
    debug_mode: bool = False,
    workspace_os_enabled: bool = True,
    db: sqlite3.Connection | None = None,
) -> ApplicationCore:
    db = db or init_database()
    bus = EventBus(debug_mode=debug_mode)
    state_store = AppStateStore(bus)

    wired = build_services(db, bus, workspace_os_enabled=workspace_os_enabled)

    return ApplicationCore(
        bus=bus,
        state_store=state_store,
        services=wired.services,
        db=db,
        workspace_os=wired.workspace_os,
    )

