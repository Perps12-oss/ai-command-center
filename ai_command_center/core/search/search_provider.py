"""
Search Provider Interface - Phase 1 Implementation

Future-proof search architecture with pluggable providers (FTS, Fuzzy, Vector, Graph).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Unified search result."""

    entity_id: UUID
    entity_type: str
    title: str
    description: str
    score: float
    metadata: dict[str, Any]


class SearchProvider(ABC):
    """
    Future-proof search architecture.
    
    Implementations:
    - FTSSearchProvider (SQLite FTS5)
    - FuzzySearchProvider (RapidFuzz)
    - VectorSearchProvider (semantic search - future)
    - GraphSearchProvider (graph traversal - future)
    """

    @abstractmethod
    def search(self, query: str, context: dict[str, Any]) -> list[SearchResult]:
        """Execute search and return results."""
        pass

    @abstractmethod
    def supports_type(self, entity_type: str) -> bool:
        """Check if provider supports this entity type."""
        pass

    @abstractmethod
    def get_provider_info(self) -> dict[str, Any]:
        """Get provider metadata (name, version, capabilities)."""
        pass


class FTSSearchProvider(SearchProvider):
    """SQLite FTS5 full-text search provider."""

    def __init__(self, entity_repository: Any) -> None:
        self._entity_repository = entity_repository

    def search(self, query: str, context: dict[str, Any]) -> list[SearchResult]:
        """Execute FTS search."""
        entity_type = context.get("entity_type")
        entities = self._entity_repository.search(query, entity_type)
        
        results = []
        for entity in entities:
            results.append(
                SearchResult(
                    entity_id=entity.id,
                    entity_type=entity.entity_type,
                    title=entity.title,
                    description=entity.description,
                    score=1.0,  # FTS doesn't provide scores in basic implementation
                    metadata={"provider": "fts"},
                )
            )
        
        return results

    def supports_type(self, entity_type: str) -> bool:
        """FTS supports all entity types."""
        return True

    def get_provider_info(self) -> dict[str, Any]:
        """Get provider metadata."""
        return {
            "name": "FTSSearchProvider",
            "version": "1.0",
            "capabilities": ["full_text_search"],
        }


class FuzzySearchProvider(SearchProvider):
    """RapidFuzz fuzzy matching provider."""

    def __init__(self, entity_repository: Any) -> None:
        self._entity_repository = entity_repository

    def search(self, query: str, context: dict[str, Any]) -> list[SearchResult]:
        """Execute fuzzy search."""
        # Placeholder: RapidFuzz integration will be added in Phase 1
        # For now, use simple substring matching
        entity_type = context.get("entity_type")
        entities = self._entity_repository.search(query, entity_type)
        
        results = []
        for entity in entities:
            results.append(
                SearchResult(
                    entity_id=entity.id,
                    entity_type=entity.entity_type,
                    title=entity.title,
                    description=entity.description,
                    score=1.0,  # Placeholder score
                    metadata={"provider": "fuzzy"},
                )
            )
        
        return results

    def supports_type(self, entity_type: str) -> bool:
        """Fuzzy search supports all entity types."""
        return True

    def get_provider_info(self) -> dict[str, Any]:
        """Get provider metadata."""
        return {
            "name": "FuzzySearchProvider",
            "version": "1.0",
            "capabilities": ["fuzzy_matching"],
        }
