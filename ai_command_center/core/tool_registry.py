"""
Tool Registry Contract - FROZEN ARCHITECTURE SPECIFICATION

Unified registry for both internal and external tools. Agents consume tools
through this interface without caring about implementation.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Tool:
    """
    Unified tool contract.
    
    A tool can wrap:
    - Internal capabilities (Search, AI, File operations)
    - External executables (Git, Browser, Terminal)
    - Future capabilities (Plugins, APIs)
    
    Agents use tools through this uniform interface.
    """

    id: UUID
    name: str
    description: str
    execute: Callable[[dict[str, Any]], Any]

    # Categorization
    internal: bool = False  # True for internal system capabilities
    external: bool = False  # True for external executables

    # Future-proofing
    required_permissions: list[str] = None  # type: ignore[assignment]
    parameters_schema: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # Avoid mutable defaults issues with frozen dataclass
        object.__setattr__(
            self, "required_permissions", self.required_permissions or []
        )
        object.__setattr__(
            self, "parameters_schema", self.parameters_schema or {}
        )


class ToolRegistry(ABC):
    """
    Tool registry contract.
    
    Responsibilities:
    - Register tools
    - Retrieve tools by ID
    - Execute tools with parameters
    - List available tools
    """

    @abstractmethod
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        pass

    @abstractmethod
    def get(self, tool_id: UUID) -> Tool | None:
        """Get tool by ID."""
        pass

    @abstractmethod
    def execute(self, tool_id: UUID, parameters: dict[str, Any]) -> Any:
        """Execute a tool with the given parameters."""
        pass

    @abstractmethod
    def list_all(self) -> list[Tool]:
        """List all registered tools."""
        pass


def create_tool(
    name: str,
    description: str,
    execute: Callable[[dict[str, Any]], Any],
    internal: bool = False,
    external: bool = False,
    required_permissions: list[str] | None = None,
    parameters_schema: dict[str, Any] | None = None,
) -> Tool:
    """Factory for creating tools."""
    return Tool(
        id=uuid4(),
        name=name,
        description=description,
        execute=execute,
        internal=internal,
        external=external,
        required_permissions=required_permissions,
        parameters_schema=parameters_schema,
    )
