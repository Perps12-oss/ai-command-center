"""Legacy database bootstrap — use ``repositories`` for data access.

Connection helpers (``connect``, ``init_database``) remain here for
application bootstrap and headless scripts.
"""

from ai_command_center.db.connection import connect, get_database_path, init_database

__all__ = [
    "connect",
    "get_database_path",
    "init_database",
]
