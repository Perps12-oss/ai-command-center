#!/usr/bin/env python3
"""Generate procedural background assets for BackgroundCanvas."""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "ai_command_center" / "ui" / "assets" / "backgrounds"
W, H = 1100, 700
BASE = (11, 12, 21)


def _vignette(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img, "RGBA")
    for i in range(40):
        alpha = int(i * 3)
        margin = i * 3
        draw.rectangle(
            [margin, margin, W - margin, H - margin],
            outline=(0, 0, 0, alpha),
        )
    return img


def _noise(img: Image.Image, amount: int = 800) -> Image.Image:
    px = img.load()
    rng = random.Random(42)
    for _ in range(amount):
        x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
        v = rng.randint(20, 45)
        px[x, y] = (v, v + 2, v + 8, 30)
    return img


def dark_canvas() -> Image.Image:
    img = Image.new("RGBA", (W, H), BASE + (255,))
    return _vignette(img)


def static_grid() -> Image.Image:
    img = Image.new("RGBA", (W, H), BASE + (255,))
    draw = ImageDraw.Draw(img)
    step = 48
    for x in range(0, W, step):
        draw.line([(x, 0), (x, H)], fill=(30, 35, 55, 80), width=1)
    for y in range(0, H, step):
        draw.line([(0, y), (W, y)], fill=(30, 35, 55, 80), width=1)
    return _vignette(img)


def abstract_flow() -> Image.Image:
    img = Image.new("RGBA", (W, H), BASE + (255,))
    draw = ImageDraw.Draw(img)
    for i in range(12):
        y = H // 2 + int(80 * math.sin(i * 0.8))
        draw.arc(
            [80 + i * 60, y - 120, 400 + i * 60, y + 120],
            start=200,
            end=340,
            fill=(0, 180, 200, 40),
            width=2,
        )
    draw.ellipse([W // 2 - 200, H - 80, W // 2 + 200, H + 40], fill=(0, 255, 255, 25))
    return _noise(_vignette(img))


def neural_map() -> Image.Image:
    img = Image.new("RGBA", (W, H), BASE + (255,))
    draw = ImageDraw.Draw(img)
    rng = random.Random(7)
    nodes = [(rng.randint(50, W - 50), rng.randint(50, H - 50)) for _ in range(24)]
    for a in nodes:
        for b in nodes:
            if a == b:
                continue
            if rng.random() < 0.08:
                draw.line([a, b], fill=(60, 80, 120, 50), width=1)
    for x, y in nodes:
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 200, 220, 90))
    return _vignette(img)


def chat_void() -> Image.Image:
    img = Image.new("RGBA", (W, H), (8, 9, 14, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, H - 120, W, H], fill=(15, 18, 28, 180))
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assets = {
        "dark_canvas.png": dark_canvas,
        "system_grid.png": static_grid,
        "home_core_world.png": abstract_flow,
        "notes_surface.png": neural_map,
        "chat_void.png": chat_void,
    }
    for name, fn in assets.items():
        path = OUT / name
        fn().save(path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
