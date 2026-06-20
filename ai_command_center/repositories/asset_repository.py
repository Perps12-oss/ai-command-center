"""Asset repository for image loading."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


class AssetRepository:
    """Owns image file access for UI assets."""

    def load_image(self, path: Path) -> Image.Image:
        with Image.open(path) as image:
            return image.copy()
