"""Production command sandbox — validates shell strings before subprocess spawn."""

from __future__ import annotations

import re
import shlex
from pathlib import Path


class SecurityError(Exception):
    """Raised when a command/path is rejected by the sandbox."""


_DANGEROUS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\b\s+-[a-z]*r", re.IGNORECASE),
    re.compile(r"\bdel\b\s+/[a-z]", re.IGNORECASE),
    re.compile(r"\brmdir\b\s+/s", re.IGNORECASE),
    re.compile(r"\bformat\b\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r":\s*\(\s*\)\s*\{", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breg\b\s+delete", re.IGNORECASE),
    re.compile(r"\bcurl\b.*\|\s*(sh|bash|powershell)", re.IGNORECASE),
    re.compile(r"\bInvoke-Expression\b|\biex\b", re.IGNORECASE),
)

_SHELL_METACHARS = set(";&|`$><\n\r")

_DEFAULT_ALLOWLIST = frozenset(
    {"echo", "cat", "type", "ls", "dir", "whoami", "hostname", "python", "git"}
)


class CommandSandbox:
    """Validates command strings before execution with ``shell=False``."""

    def __init__(
        self,
        allowlist: frozenset[str] | set[str] | None = None,
        *,
        vault_root: str | Path | None = None,
    ) -> None:
        self._allowlist = frozenset(
            _DEFAULT_ALLOWLIST if allowlist is None else allowlist
        )
        self._vault_root = Path(vault_root).resolve() if vault_root else None

    def validate_command(self, command: str) -> list[str]:
        """Return safe argv for ``command`` or raise :class:`SecurityError`."""
        if not isinstance(command, str) or not command.strip():
            raise SecurityError("empty or non-string command rejected")

        if any(ch in _SHELL_METACHARS for ch in command):
            raise SecurityError(
                f"command contains shell metacharacters and is rejected: {command!r}"
            )

        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(command):
                raise SecurityError(
                    f"command matches dangerous pattern {pattern.pattern!r}: {command!r}"
                )

        try:
            argv = shlex.split(command, posix=False)
        except ValueError as exc:
            raise SecurityError(f"command could not be parsed safely: {exc}") from exc
        if not argv:
            raise SecurityError("command produced no executable token")

        program = Path(argv[0]).name.lower()
        program = program[:-4] if program.endswith(".exe") else program
        if program not in self._allowlist:
            raise SecurityError(
                f"command {program!r} is not in the sandbox allowlist {sorted(self._allowlist)}"
            )
        return argv

    def is_safe(self, command: str) -> bool:
        try:
            self.validate_command(command)
            return True
        except SecurityError:
            return False

    def resolve_in_vault(self, rel_path: str | Path) -> Path:
        """Resolve ``rel_path`` inside the vault root or raise."""
        if self._vault_root is None:
            raise SecurityError("no vault root configured for path validation")
        candidate = Path(rel_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self._vault_root / candidate).resolve()
        try:
            resolved.relative_to(self._vault_root)
        except ValueError as exc:
            raise SecurityError(
                f"path {str(rel_path)!r} escapes vault root {self._vault_root}"
            ) from exc
        return resolved
