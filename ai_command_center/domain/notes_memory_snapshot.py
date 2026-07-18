"""Domain snapshot for notes and memory projection."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class NoteCatalogItem:
    """Typed projection of a note search result."""

    path: str = ""
    title: str = ""
    snippet: str = ""


@dataclass(frozen=True, slots=True)
class MemoryCatalogItem:
    """Typed projection of a memory catalog entry."""

    node_id: str = ""
    label: str = ""
    workspace_id: str = ""
    entity_id: str = ""


@dataclass(frozen=True, slots=True)
class NotesMemorySnapshot:
    """Consolidated immutable projection of notes + memory state."""

    notes_catalog: tuple[NoteCatalogItem, ...] = ()
    note_selected: NoteCatalogItem | None = None
    note_index_status: tuple[int, int] = ()
    memory_catalog: tuple[MemoryCatalogItem, ...] = ()
    memory_selected: tuple[str, ...] = ()
    revision: int = 0

    @classmethod
    def from_components(
        cls,
        *,
        notes_catalog: tuple[NoteCatalogItem, ...],
        note_selected: NoteCatalogItem | None,
        note_index_status: tuple[int, int],
        memory_catalog: tuple[MemoryCatalogItem, ...],
        memory_selected: tuple[str, ...],
        revision: int,
    ) -> "NotesMemorySnapshot":
        return cls(
            notes_catalog=notes_catalog,
            note_selected=note_selected,
            note_index_status=note_index_status,
            memory_catalog=memory_catalog,
            memory_selected=memory_selected,
            revision=revision,
        )

    def with_revision(self, revision: int) -> "NotesMemorySnapshot":
        return replace(self, revision=revision)
