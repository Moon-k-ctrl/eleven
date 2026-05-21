"""Generate app icons for eleven (拾遗)."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

# Color palette
BG_START = (64, 80, 200)      # deep blue-purple
BG_END = (100, 140, 240)      # lighter blue
FG_COLOR = (255, 255, 255)     # white
ACCENT = (180, 200, 255)       # light accent


def _draw_rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int, fill) -> None:
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.pieslice([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=fill)


def _draw_clipboard_icon(draw: ImageDraw.Draw, cx: int, cy: int, size: int) -> None:
    """Draw a clipboard shape in the center."""
    s = size / 2

    # Clipboard body (rounded rect)
    body_x1 = cx - s * 0.6
    body_y1 = cy - s * 0.3
    body_x2 = cx + s * 0.6
    body_y2 = cy + s * 0.8
    radius = int(s * 0.15)

    _draw_rounded_rect(draw, (body_x1, body_y1, body_x2, body_y2), radius, FG_COLOR)

    # Clipboard clip area (top)
    clip_w = s * 0.35
    clip_h = s * 0.25
    clip_x1 = cx - clip_w
    clip_y1 = body_y1 - clip_h
    clip_x2 = cx + clip_w
    clip_y2 = body_y1

    _draw_rounded_rect(draw, (clip_x1, clip_y1, clip_x2, clip_y2), int(radius * 0.8), FG_COLOR)

    # Dark inset on clipboard body
    inset_margin = s * 0.15
    _draw_rounded_rect(
        draw,
        (body_x1 + inset_margin, body_y1 + inset_margin,
         body_x2 - inset_margin, body_y2 - inset_margin),
        int(radius * 0.6),
        (40, 55, 120),
    )

    # Lines on the clipboard (representing content)
    line_color = (140, 170, 230)
    line_y_start = body_y1 + inset_margin + s * 0.18
    for i in range(3):
        ly = line_y_start + i * s * 0.16
        lw = (body_x2 - body_x1 - 2 * inset_margin) * (0.9 - i * 0.1)
        lx = cx - lw / 2
        draw.rounded_rectangle(
            [lx, ly, lx + lw, ly + s * 0.06],
            radius=int(s * 0.03),
            fill=line_color,
        )


def _vertical_gradient(draw: ImageDraw.Draw, width: int, height: int,
                       top: tuple, bottom: tuple) -> None:
    """Draw vertical gradient."""
    for y in range(height):
        ratio = y / height
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def generate_icon(size: int = 256, output_path: Optional[Path] = None,
                  output_ico: Optional[Path] = None) -> Image.Image:
    """Generate the app icon.

    Args:
        size: Size in pixels (square).
        output_path: Optional path to save as PNG.
        output_ico: Optional path to save as ICO.

    Returns:
        The generated PIL Image.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded square
    margin = size * 0.08
    radius = size * 0.22

    # Gradient background
    # First draw gradient on a separate layer
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)

    inner_size = size - 2 * margin
    _draw_rounded_rect(
        bg_draw,
        (margin, margin, margin + inner_size, margin + inner_size),
        int(radius),
        (255, 255, 255, 255),
    )

    # Apply gradient using the rounded rect as mask
    gradient = Image.new("RGBA", (size, size))
    gd = ImageDraw.Draw(gradient)
    _vertical_gradient(gd, size, size, BG_START, BG_END)

    # Composite gradient with rounded mask
    img.paste(gradient, mask=bg)

    # Border (subtle)
    bg2 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg2_draw = ImageDraw.Draw(bg2)
    _draw_rounded_rect(
        bg2_draw,
        (margin - 1, margin - 1, margin + inner_size + 1, margin + inner_size + 1),
        int(radius + 1),
        (255, 255, 255, 60),
    )
    _draw_rounded_rect(
        bg2_draw,
        (margin + 2, margin + 2, margin + inner_size - 2, margin + inner_size - 2),
        int(radius - 1),
        (0, 0, 0, 0),  # punch hole for border only
    )
    # Simpler: just draw border lines
    img.paste(bg2, mask=bg2)

    # Draw clipboard icon
    _draw_clipboard_icon(draw, size // 2, size // 2, size * 0.55)

    # Save as PNG
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        print(f"Saved PNG: {output_path}")

    # Save as ICO (multi-res for Windows)
    if output_ico:
        output_ico.parent.mkdir(parents=True, exist_ok=True)
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        icons = []
        for ico_size in sizes:
            ico_img = img.resize(ico_size, Image.Resampling.LANCZOS)
            icons.append(ico_img)
        # Save first icon as ICO with all sizes
        icons[0].save(output_ico, "ICO", sizes=[(s[0], s[1]) for s in sizes], append_images=icons[1:])
        print(f"Saved ICO: {output_ico}")

    return img


def main() -> None:
    """Generate all icon assets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    png_path = OUTPUT_DIR / "icon.png"
    ico_path = OUTPUT_DIR / "icon.ico"

    generate_icon(256, png_path, ico_path)

    # Also generate tray-specific size (16x16 for tray)
    tray_png = OUTPUT_DIR / "tray-icon.png"
    tray_img = generate_icon(64)
    tray_img = tray_img.resize((16, 16), Image.Resampling.LANCZOS)
    tray_img.save(tray_png, "PNG")
    print(f"Saved tray icon: {tray_png}")


if __name__ == "__main__":
    main()
