"""Permission declarations for provider manifests."""

from __future__ import annotations

from dataclasses import dataclass


KNOWN_PERMISSIONS: frozenset[str] = frozenset(
    {
        "filesystem.read",
        "filesystem.write",
        "network.outbound",
        "shell.execute",
        "clipboard.read",
        "clipboard.write",
        "calendar.read",
        "calendar.write",
        "email.send",
        "mcp.invoke",
    }
)


@dataclass(frozen=True, slots=True)
class PermissionDecl:
    name: str
    required: bool = True

    def validate(self) -> str | None:
        if not self.name:
            return "permission name is required"
        if self.name not in KNOWN_PERMISSIONS:
            return f"unknown permission {self.name!r}"
        return None
