"""MCP Manifest Validator — validates MCP server manifests against schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationSeverity(str, Enum):
    """Severity level for validation errors."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    """A single validation error."""

    path: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass
class ValidationResult:
    """Result of manifest validation."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def add_error(self, path: str, message: str) -> None:
        self.valid = False
        self.errors.append(ValidationError(path=path, message=message))

    def add_warning(self, path: str, message: str) -> None:
        self.warnings.append(ValidationError(path=path, message=message, severity=ValidationSeverity.WARNING))

    @classmethod
    def success(cls) -> ValidationResult:
        return cls(valid=True)


@dataclass
class MCPToolSchema:
    """Schema for an MCP tool."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResourceSchema:
    """Schema for an MCP resource."""

    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPServerManifest:
    """Validated MCP server manifest."""

    server_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    tools: list[MCPToolSchema] = field(default_factory=list)
    resources: list[MCPResourceSchema] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class MCPManifestValidator:
    """Validates MCP server manifests against the schema."""

    REQUIRED_FIELDS = {"server_id", "name"}
    OPTIONAL_FIELDS = {"version", "description", "tools", "resources", "capabilities"}
    VALID_CAPABILITIES = {"tools", "resources", "prompts"}

    def validate(self, manifest: dict[str, Any]) -> ValidationResult:
        """Validate an MCP manifest.

        Args:
            manifest: Raw manifest dictionary

        Returns:
            ValidationResult with any errors or warnings
        """
        result = ValidationResult.success()

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in manifest:
                result.add_error(field_name, f"Required field '{field_name}' is missing")

        if not result.valid:
            return result

        # Validate field types
        self._validate_types(manifest, result)

        # Validate tools
        if "tools" in manifest:
            self._validate_tools(manifest["tools"], result)

        # Validate resources
        if "resources" in manifest:
            self._validate_resources(manifest["resources"], result)

        # Validate capabilities
        if "capabilities" in manifest:
            self._validate_capabilities(manifest["capabilities"], result)

        return result

    def _validate_types(self, manifest: dict[str, Any], result: ValidationResult) -> None:
        """Validate field types."""
        if "server_id" in manifest and not isinstance(manifest["server_id"], str):
            result.add_error("server_id", "server_id must be a string")

        if "name" in manifest and not isinstance(manifest["name"], str):
            result.add_error("name", "name must be a string")

        if "version" in manifest and not isinstance(manifest["version"], str):
            result.add_error("version", "version must be a string")

        if "description" in manifest and not isinstance(manifest["description"], str):
            result.add_error("description", "description must be a string")

    def _validate_tools(self, tools: Any, result: ValidationResult) -> None:
        """Validate tools array."""
        if not isinstance(tools, list):
            result.add_error("tools", "tools must be an array")
            return

        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                result.add_error(f"tools[{i}]", "Tool must be an object")
                continue

            if "name" not in tool:
                result.add_warning(f"tools[{i}]", "Tool missing 'name' field")
            elif not isinstance(tool["name"], str):
                result.add_error(f"tools[{i}].name", "Tool name must be a string")

    def _validate_resources(self, resources: Any, result: ValidationResult) -> None:
        """Validate resources array."""
        if not isinstance(resources, list):
            result.add_error("resources", "resources must be an array")
            return

        for i, resource in enumerate(resources):
            if not isinstance(resource, dict):
                result.add_error(f"resources[{i}]", "Resource must be an object")
                continue

            if "uri" not in resource:
                result.add_warning(f"resources[{i}]", "Resource missing 'uri' field")
            elif not isinstance(resource["uri"], str):
                result.add_error(f"resources[{i}].uri", "Resource uri must be a string")

    def _validate_capabilities(self, capabilities: Any, result: ValidationResult) -> None:
        """Validate capabilities array."""
        if not isinstance(capabilities, list):
            result.add_error("capabilities", "capabilities must be an array")
            return

        for i, cap in enumerate(capabilities):
            if not isinstance(cap, str):
                result.add_error(f"capabilities[{i}]", "Capability must be a string")
                continue

            if cap not in self.VALID_CAPABILITIES:
                result.add_warning(
                    f"capabilities[{i}]",
                    f"Unknown capability '{cap}'. Valid: {', '.join(self.VALID_CAPABILITIES)}",
                )

    def parse(self, manifest: dict[str, Any]) -> MCPServerManifest | None:
        """Parse and validate a manifest.

        Args:
            manifest: Raw manifest dictionary

        Returns:
            MCPServerManifest if valid, None otherwise
        """
        result = self.validate(manifest)
        if not result.valid:
            return None

        tools = [
            MCPToolSchema(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in manifest.get("tools", [])
        ]

        resources = [
            MCPResourceSchema(
                uri=r.get("uri", ""),
                name=r.get("name", ""),
                description=r.get("description", ""),
                mime_type=r.get("mimeType", "text/plain"),
            )
            for r in manifest.get("resources", [])
        ]

        return MCPServerManifest(
            server_id=manifest["server_id"],
            name=manifest["name"],
            version=manifest.get("version", "1.0.0"),
            description=manifest.get("description", ""),
            tools=tools,
            resources=resources,
            capabilities=manifest.get("capabilities", []),
            raw=manifest,
        )


__all__ = [
    "MCPManifestValidator",
    "MCPServerManifest",
    "MCPResourceSchema",
    "MCPToolSchema",
    "ValidationResult",
    "ValidationError",
    "ValidationSeverity",
]
