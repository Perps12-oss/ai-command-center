"""Vault repository for file-backed note storage."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


class VaultRepository:
    """Owns vault path resolution and markdown file access."""

    def __init__(self, vault_path: str | Path | None = None) -> None:
        self._vault_path: Path | None = Path(vault_path) if vault_path else None

    def set_vault_path(self, vault_path: str | Path | None) -> None:
        self._vault_path = Path(vault_path) if vault_path else None

    def get_vault_path(self) -> Path | None:
        return self._vault_path

    def resolve_path(self, rel_path: str | Path) -> Path | None:
        if self._vault_path is None:
            return None
        path = Path(rel_path)
        if not path.is_absolute():
            path = self._vault_path / path
        try:
            path.resolve().relative_to(self._vault_path.resolve())
        except ValueError:
            return None
        return path

    def read_note(self, rel_path: str | Path) -> str | None:
        path = self.resolve_path(rel_path)
        if path is None or not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def write_note(self, rel_path: str | Path, content: str) -> Path | None:
        path = self.resolve_path(rel_path)
        if path is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(content, encoding="utf-8")
        except OSError:
            return None
        return path

    def iter_markdown_files(self) -> Iterator[Path]:
        if self._vault_path is None or not self._vault_path.is_dir():
            return iter(())
        return (path for path in self._vault_path.rglob("*.md") if path.is_file())

    def relative_path(self, path: Path) -> str:
        if self._vault_path is None:
            return str(path)
        try:
            return str(path.resolve().relative_to(self._vault_path.resolve())).replace("\\", "/")
        except ValueError:
            return str(path)
