"""Application bootstrap - wires core layer without UI.

Service and repository wiring lives in ``core.service_factory``.
Add new services there; this file only orchestrates startup/shutdown.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.core.state.system_snapshot_builder import SystemSnapshotBuilder
from ai_command_center.core.workspace_os_service import WorkspaceOsService
from ai_command_center.db.conn_sync import ConnectionCloseTimeout
from ai_command_center.db.connection import init_database
from ai_command_center.platform.hero_assets import load_hero_ctk_image

_logger = logging.getLogger(__name__)


class ShutdownIncompleteError(RuntimeError):
    """Raised when teardown cannot restore its lifecycle invariant.

    Shutdown stays bounded, but a bounded shutdown that did not finish must not
    be reported as success — callers decide whether to force process exit.
    """


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
    hero_image: ctk.CTkImage | None = field(default=None, repr=False)

    def startup(self) -> None:
        self.bus.publish("app.phase", {"phase": "starting"}, source="application")
        self.services.load_all()
        SystemSnapshotBuilder(self.bus).publish(state_store=self.state_store)
        self.bus.publish("app.phase", {"phase": "ready"}, source="application")

    def shutdown(self) -> None:
        """Tear down bounded and in dependency order.

        Invariant: the EventBus must be fully stopped (no dispatch work that
        could still own the SQLite handle) before the connection is closed. If
        the bus cannot be drained we surface a lifecycle failure instead of
        closing the DB underneath a live worker or waiting forever.
        """
        self.services.shutdown()
        self.state_store.close()
        self.bus.publish("app.phase", {"phase": "stopped"}, source="application")
        # ``EventBus.shutdown()`` reports whether dispatch actually stopped;
        # only an explicit False means the invariant was not restored.
        bus_stopped = self.bus.shutdown()
        if bus_stopped is False:
            _logger.error(
                "application.shutdown_incomplete: EventBus dispatch still active; "
                "leaving database open to avoid closing it under a live worker"
            )
            raise ShutdownIncompleteError(
                "EventBus dispatch did not stop; database left open"
            )
        try:
            self.db.close()
        except ConnectionCloseTimeout as exc:
            _logger.error("application.shutdown_incomplete: %s", exc)
            raise ShutdownIncompleteError(str(exc)) from exc


def create_application(
    *,
    debug_mode: bool = False,
    workspace_os_enabled: bool = True,
    db: sqlite3.Connection | None = None,
) -> ApplicationCore:
    db = db or init_database()
    bus = EventBus(debug_mode=debug_mode, async_dispatch=True)
    state_store = AppStateStore(bus)

    wired = build_services(db, bus, workspace_os_enabled=workspace_os_enabled)

    return ApplicationCore(
        bus=bus,
        state_store=state_store,
        services=wired.services,
        db=db,
        workspace_os=wired.workspace_os,
        hero_image=load_hero_ctk_image(),
    )

