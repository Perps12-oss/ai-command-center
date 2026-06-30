"""Risk area #3 - path traversal in the Obsidian vault indexer.

A crafted note path that escapes the vault root (``../../../../Windows/System32``)
must be refused: the vault repository returns ``None`` and never touches a file
outside the vault. The reference sandbox raises a ``SecurityError`` for the same
input.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ai_command_center.repositories.vault_repository import VaultRepository
from tests.support import CommandSandbox, SecurityError

pytestmark = pytest.mark.security

# Forward-slash separators escape the vault on every OS.
TRAVERSAL_PATHS = [
    "../../../../Windows/System32/config",
    "../../etc/passwd",
    "notes/../../../secret.txt",
]

# Backslash is only a path separator on Windows; on POSIX it is a literal
# filename char and is safely contained, so this case is Windows-only.
if sys.platform == "win32":
    TRAVERSAL_PATHS.append("..\\..\\..\\Windows\\System32\\drivers\\etc\\hosts")


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "ok.md").write_text("# Safe note\n", encoding="utf-8")
    # A secret living *outside* the vault that traversal would try to reach.
    (tmp_path / "secret.txt").write_text("TOP SECRET", encoding="utf-8")
    return root


@pytest.mark.parametrize("evil", TRAVERSAL_PATHS)
def test_vault_repo_rejects_traversal_resolve(vault: Path, evil: str) -> None:
    repo = VaultRepository(vault)
    assert repo.resolve_path(evil) is None, (
        f"resolve_path must reject vault escape {evil!r}"
    )


@pytest.mark.parametrize("evil", TRAVERSAL_PATHS)
def test_vault_repo_read_note_ignores_traversal(vault: Path, evil: str) -> None:
    repo = VaultRepository(vault)
    assert repo.read_note(evil) is None, (
        f"read_note must not read outside the vault via {evil!r}"
    )


@pytest.mark.parametrize("evil", TRAVERSAL_PATHS)
def test_vault_repo_write_note_blocks_traversal(vault: Path, evil: str) -> None:
    repo = VaultRepository(vault)
    assert repo.write_note(evil, "pwned") is None, (
        f"write_note must refuse to write outside the vault via {evil!r}"
    )


def test_safe_relative_path_is_allowed(vault: Path) -> None:
    repo = VaultRepository(vault)
    assert repo.read_note("ok.md") == "# Safe note\n"


@pytest.mark.parametrize("evil", TRAVERSAL_PATHS)
def test_sandbox_resolve_in_vault_raises(vault: Path, evil: str) -> None:
    sandbox = CommandSandbox(vault_root=vault)
    with pytest.raises(SecurityError):
        sandbox.resolve_in_vault(evil)


def test_sandbox_resolve_in_vault_allows_safe_path(vault: Path) -> None:
    sandbox = CommandSandbox(vault_root=vault)
    resolved = sandbox.resolve_in_vault("ok.md")
    assert resolved == (vault / "ok.md").resolve()
