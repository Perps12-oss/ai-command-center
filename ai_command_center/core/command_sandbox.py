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

# Arguments that make an allowlisted program execute caller-supplied code.
# ``git -c`` sets arbitrary config (core.fsmonitor, alias.x=!cmd) and
# ``--upload-pack``/``--receive-pack``/``--exec`` name a program to run.
_ARG_DENYLIST: dict[str, frozenset[str]] = {
    "python": frozenset({"-c", "--command", "-m"}),
    "git": frozenset(
        {
            "-c",
            "--config-env",
            "--exec",
            "--exec-path",
            "--receive-pack",
            "--upload-pack",
        }
    ),
}


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
        self._reject_code_bearing_arguments(program, argv)
        return argv

    @staticmethod
    def _reject_code_bearing_arguments(program: str, argv: list[str]) -> None:
        """Reject arguments that turn an allowlisted program into an interpreter.

        Allowlisting ``argv[0]`` is not sufficient: ``python`` and ``git`` both
        accept code or program paths as *arguments*, so ``shell=False`` provides
        no protection. Values may be attached with ``=``
        (``--upload-pack=calc``) or supplied as the next token (``-c cfg=val``),
        so compare on the flag portion only.
        """
        denied = _ARG_DENYLIST.get(program)
        if not denied:
            return
        for token in argv[1:]:
            flag = token.split("=", 1)[0].strip().strip("\"'").lower()
            if flag in denied:
                raise SecurityError(
                    f"{program} inline execution via {flag!r} is not permitted "
                    f"by the sandbox: {' '.join(argv)!r}"
                )

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


# Bounded READ-only runner used by tests and the READONLY_SHELL_TOOL path.
from ai_command_center.core.security_policy import READONLY_SHELL_ALLOWLIST

READONLY_COMMAND_SANDBOX = CommandSandbox(allowlist=READONLY_SHELL_ALLOWLIST)
