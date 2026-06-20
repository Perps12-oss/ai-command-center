"""Generate hero_core.png for HeroPanel."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "ai_command_center" / "ui" / "assets" / "hero_core.png"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    w, h = 640, 160
    img = Image.new("RGBA", (w, h), (11, 12, 21, 255))
    draw = ImageDraw.Draw(img)
    # Battery shell
    draw.rounded_rectangle([80, 30, 560, 120], radius=20, outline=(0, 255, 255, 120), width=3)
    # Three segments
    for i, x in enumerate((110, 250, 390)):
        fill = (0, 255, 255, 80 + i * 30)
        draw.rounded_rectangle([x, 50, x + 100, 100], radius=10, fill=fill)
    img.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
