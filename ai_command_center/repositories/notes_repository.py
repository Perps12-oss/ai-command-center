"""Compatibility spelling for AGENTS.md ``notes_repository`` name.

Authoritative implementation: ``note_repository.NoteRepository`` (index + vault).
This module re-exports that type — it is not a second persistence authority.
"""

from __future__ import annotations

from ai_command_center.repositories.note_repository import NoteHit, NoteRepository

# Historical class name used in AGENTS.md deliverable list.
NotesRepository = NoteRepository

__all__ = ["NoteHit", "NoteRepository", "NotesRepository"]
