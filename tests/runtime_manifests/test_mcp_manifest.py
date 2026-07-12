"""Tests for MCP manifest validator."""

import pytest

from ai_command_center.runtime_manifests.mcp_manifest import (
    MCPManifestValidator,
    MCPServerManifest,
    ValidationSeverity,
)


class TestMCPManifestValidator:
    """Test cases for MCPManifestValidator."""

    def setup_method(self) -> None:
        self.validator = MCPManifestValidator()

    def test_valid_minimal_manifest(self) -> None:
        """Test validation of a minimal valid manifest."""
        manifest = {
            "server_id": "test-server",
            "name": "Test Server",
        }
        result = self.validator.validate(manifest)
        assert result.valid
        assert len(result.errors) == 0

    def test_valid_full_manifest(self) -> None:
        """Test validation of a full manifest with all fields."""
        manifest = {
            "server_id": "full-server",
            "name": "Full Server",
            "version": "2.0.0",
            "description": "A complete MCP server",
            "tools": [
                {"name": "tool1", "description": "First tool"},
                {"name": "tool2"},
            ],
            "resources": [
                {"uri": "file:///test", "name": "Test File"},
            ],
            "capabilities": ["tools", "resources"],
        }
        result = self.validator.validate(manifest)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_required_server_id(self) -> None:
        """Test validation fails when server_id is missing."""
        manifest = {"name": "Test Server"}
        result = self.validator.validate(manifest)
        assert not result.valid
        assert any("server_id" in e.message for e in result.errors)

    def test_missing_required_name(self) -> None:
        """Test validation fails when name is missing."""
        manifest = {"server_id": "test-server"}
        result = self.validator.validate(manifest)
        assert not result.valid
        assert any("name" in e.message for e in result.errors)

    def test_invalid_server_id_type(self) -> None:
        """Test validation fails when server_id is not a string."""
        manifest = {"server_id": 123, "name": "Test"}
        result = self.validator.validate(manifest)
        assert not result.valid

    def test_invalid_name_type(self) -> None:
        """Test validation fails when name is not a string."""
        manifest = {"server_id": "test", "name": ["not", "a", "string"]}
        result = self.validator.validate(manifest)
        assert not result.valid

    def test_tools_must_be_array(self) -> None:
        """Test validation fails when tools is not an array."""
        manifest = {"server_id": "test", "name": "Test", "tools": "not an array"}
        result = self.validator.validate(manifest)
        assert not result.valid

    def test_tool_missing_name(self) -> None:
        """Test validation warning when tool is missing name."""
        manifest = {
            "server_id": "test",
            "name": "Test",
            "tools": [{"description": "No name"}],
        }
        result = self.validator.validate(manifest)
        assert result.valid  # Still valid, just warning
        assert len(result.warnings) > 0

    def test_resources_must_be_array(self) -> None:
        """Test validation fails when resources is not an array."""
        manifest = {"server_id": "test", "name": "Test", "resources": {}}
        result = self.validator.validate(manifest)
        assert not result.valid

    def test_resource_missing_uri(self) -> None:
        """Test validation warning when resource is missing uri."""
        manifest = {
            "server_id": "test",
            "name": "Test",
            "resources": [{"name": "No URI"}],
        }
        result = self.validator.validate(manifest)
        assert result.valid  # Still valid, just warning
        assert len(result.warnings) > 0

    def test_capabilities_must_be_array(self) -> None:
        """Test validation fails when capabilities is not an array."""
        manifest = {"server_id": "test", "name": "Test", "capabilities": "tools"}
        result = self.validator.validate(manifest)
        assert not result.valid

    def test_unknown_capability_warning(self) -> None:
        """Test validation warning for unknown capability."""
        manifest = {
            "server_id": "test",
            "name": "Test",
            "capabilities": ["unknown_capability"],
        }
        result = self.validator.validate(manifest)
        assert result.valid  # Still valid, just warning
        assert any("unknown_capability" in w.message for w in result.warnings)

    def test_parse_valid_manifest(self) -> None:
        """Test parsing a valid manifest."""
        manifest = {
            "server_id": "parse-test",
            "name": "Parse Test",
            "version": "1.0.0",
            "tools": [{"name": "my_tool", "description": "A tool"}],
        }
        parsed = self.validator.parse(manifest)
        assert parsed is not None
        assert isinstance(parsed, MCPServerManifest)
        assert parsed.server_id == "parse-test"
        assert parsed.name == "Parse Test"
        assert parsed.version == "1.0.0"
        assert len(parsed.tools) == 1
        assert parsed.tools[0].name == "my_tool"

    def test_parse_invalid_manifest_returns_none(self) -> None:
        """Test parsing an invalid manifest returns None."""
        manifest = {"name": "Missing server_id"}
        parsed = self.validator.parse(manifest)
        assert parsed is None


class TestValidationResult:
    """Test cases for ValidationResult."""

    def test_success_result(self) -> None:
        """Test creating a success result."""
        from ai_command_center.runtime_manifests.mcp_manifest import ValidationResult
        result = ValidationResult.success()
        assert result.valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error_makes_invalid(self) -> None:
        """Test adding an error makes result invalid."""
        from ai_command_center.runtime_manifests.mcp_manifest import ValidationResult
        result = ValidationResult.success()
        result.add_error("field", "Error message")
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].path == "field"
        assert result.errors[0].message == "Error message"
        assert result.errors[0].severity == ValidationSeverity.ERROR

    def test_add_warning_keeps_valid(self) -> None:
        """Test adding a warning keeps result valid."""
        from ai_command_center.runtime_manifests.mcp_manifest import ValidationResult
        result = ValidationResult.success()
        result.add_warning("field", "Warning message")
        assert result.valid  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == ValidationSeverity.WARNING
