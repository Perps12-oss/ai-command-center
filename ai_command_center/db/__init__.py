"""Database package.

Backwards-compatible re-export of the canonical repository implementations.
New code should import directly from ``ai_command_center.repositories``.
"""

from ai_command_center.db.connection import connect, get_database_path, init_database
from ai_command_center.repositories.conversation_repository import ConversationRepository
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.repositories.note_repository import NoteRepository
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.repositories.telemetry_repository import TelemetryRepository

__all__ = [
    "connect",
    "get_database_path",
    "init_database",
    "ConversationRepository",
    "MemoryRepository",
    "NoteRepository",
    "SettingsRepository",
    "TelemetryRepository",
]
