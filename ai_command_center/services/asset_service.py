"""Asset service facade for UI-safe image loading."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ai_command_center.repositories.asset_repository import AssetRepository


class AssetService:
    """Service wrapper around asset repository operations."""

    def __init__(self, repo: AssetRepository | None = None) -> None:
        self._repo = repo or AssetRepository()

    def load_image(self, path: Path) -> Image.Image:
        return self._repo.load_image(path)
