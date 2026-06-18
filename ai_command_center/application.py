"""Application bootstrap — wires core layer without UI."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.db.connection import init_database
from ai_command_center.db.conversation_repository import ConversationRepository
from ai_command_center.db.note_repository import NoteRepository
from ai_command_center.db.repository import SettingsRepository
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.obsidian_service import ObsidianService
from ai_command_center.services.ollama_http_service import OllamaHttpService
from ai_command_center.services.session_service import SessionService
from ai_command_center.services.settings_service import SettingsService


@dataclass
class ApplicationCore:
    """
    Composition root. Only this module constructs repositories.
    Public surface: bus, state_store, services — not repositories.
    """

    bus: EventBus
    state_store: AppStateStore
    services: ServiceManager
    db: sqlite3.Connection

    def startup(self) -> None:
        self.bus.publish("app.phase", {"phase": "starting"}, source="application")
        self.services.load_all()
        self.bus.publish("app.phase", {"phase": "ready"}, source="application")

    def shutdown(self) -> None:
        self.services.shutdown()
        self.state_store.close()
        self.db.close()
        self.bus.publish("app.phase", {"phase": "stopped"}, source="application")


def create_application(*, debug_mode: bool = False) -> ApplicationCore:
    db = init_database()
    bus = EventBus(debug_mode=debug_mode)
    state_store = AppStateStore(bus)
    services = ServiceManager(bus)
    settings_repo = SettingsRepository(db)
    context_manager = ContextManager()
    ollama = OllamaHttpService(bus)
    note_repo = NoteRepository(db)
    conv_repo = ConversationRepository(db)
    obsidian = ObsidianService(bus, note_repo)
    session = SessionService(bus, conv_repo)
    services.register(SettingsService(bus, settings_repo))
    services.register(CommandRouterService(bus))
    services.register(ollama)
    services.register(obsidian)
    services.register(session)
    services.register(
        ChatHandlerService(bus, context_manager, ollama, obsidian, session)
    )
    return ApplicationCore(
        bus=bus,
        state_store=state_store,
        services=services,
        db=db,
    )
