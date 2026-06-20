"""Shared background image loading, blur, shadows, and canvas painting."""



from __future__ import annotations



import logging

import tkinter as tk

from pathlib import Path



from PIL import Image, ImageDraw, ImageFilter, ImageTk



_log = logging.getLogger(__name__)





def resize_image(path: Path, size: tuple[int, int]) -> Image.Image:

    image = Image.open(path)

    if image.size != size:

        image = image.resize(size, Image.Resampling.LANCZOS)

    if image.mode not in ("RGB", "RGBA"):

        image = image.convert("RGB")

    return image





def apply_blur(pil_image: Image.Image, radius: float) -> Image.Image:

    if radius <= 0:

        return pil_image

    return pil_image.filter(ImageFilter.GaussianBlur(radius=radius))





def apply_vignette(pil_image: Image.Image, dim: float) -> Image.Image:

    if dim <= 0:

        return pil_image

    w, h = pil_image.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    draw = ImageDraw.Draw(overlay)

    margin = int(min(w, h) * 0.08)

    draw.rectangle((0, 0, w, h), fill=(0, 0, 0, int(255 * dim * 0.35)))

    draw.rectangle((margin, margin, w - margin, h - margin), fill=(0, 0, 0, 0))

    base = pil_image.convert("RGBA")

    return Image.alpha_composite(base, overlay).convert("RGB")





def create_drop_shadow(

    width: int,

    height: int,

    *,

    radius: int = 6,

    offset: int = 10,

    corner_radius: int = 16,

) -> ImageTk.PhotoImage:

    pad = offset + radius

    sw = width + pad * 2

    sh = height + pad * 2

    shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))

    draw = ImageDraw.Draw(shadow)

    x0, y0 = pad, pad

    x1, y1 = pad + width, pad + height

    draw.rounded_rectangle((x0, y0, x1, y1), radius=corner_radius, fill=(0, 0, 0, 180))

    blurred = shadow.filter(ImageFilter.GaussianBlur(radius=radius))

    return ImageTk.PhotoImage(blurred)





def paint_canvas(

    canvas: tk.Canvas,

    path: Path,

    size: tuple[int, int],

    *,

    blur_radius: float = 0,

    vignette_dim: float = 0,

) -> ImageTk.PhotoImage | None:

    try:

        pil = resize_image(path, size)

        if blur_radius > 0:

            pil = apply_blur(pil, blur_radius)

        if vignette_dim > 0:

            pil = apply_vignette(pil, vignette_dim)

        photo = ImageTk.PhotoImage(pil)

        canvas.delete("bg")

        canvas.configure(width=size[0], height=size[1])

        canvas.create_image(0, 0, anchor="nw", image=photo, tags="bg")

        canvas.tag_lower("bg")

        for item in canvas.find_withtag("zone_ui"):

            canvas.tag_raise(item)

        _log.info(

            "Background painted %s at %sx%s blur=%s",

            path.name,

            size[0],

            size[1],

            blur_radius,

        )

        return photo

    except Exception as exc:

        _log.error("Background paint failed %s: %s", path, exc)

        return None


