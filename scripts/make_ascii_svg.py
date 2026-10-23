#!/usr/bin/env python3
"""
make_ascii_svg.py

Converts source-prepped.png into avi-ascii.svg — a monochrome ASCII
portrait where each row types itself in left-to-right, staggered top to
bottom. Plays once, then freezes (no loop).

Set env var STATIC=1 to emit a frozen frame for local Quick Look previews.
"""

import os
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "source-prepped.png"
OUT  = ROOT / "avi-ascii.svg"

# Density ramp: space = brightest/empty, @ = darkest/dense
RAMP = " .`:-=+*cs#%@"

# Target column count; height is calculated to preserve aspect ratio
TARGET_W = 96


def main() -> None:
    if not SRC.exists():
        raise SystemExit(
            "source-prepped.png not found.\n"
            "Run:  python scripts/prep_photo.py <your-photo.jpg>"
        )

    img = Image.open(SRC).convert("L")
    img = ImageOps.autocontrast(img)

    # Monospace characters are roughly 0.5× as wide as they are tall,
    # so shrink the target height by ~0.5 to avoid vertical stretching.
    target_h = max(32, int(img.height * TARGET_W / img.width * 0.48))
    img = img.resize((TARGET_W, target_h), Image.Resampling.LANCZOS)

    lines: list[str] = []
    for y in range(img.height):
        row: list[str] = []
        for x in range(img.width):
            value = img.getpixel((x, y))
            idx = int((255 - value) / 256 * len(RAMP))
            idx = max(0, min(len(RAMP) - 1, idx))
            row.append(RAMP[idx])
        lines.append("".join(row))

    FONT_W  = 6   # px per glyph at font-size 8px
    FONT_H  = 10  # px per line
    PADDING = 18

    width  = TARGET_W * FONT_W + PADDING * 2
    height = target_h * FONT_H + PADDING * 2

    static = os.environ.get("STATIC", "0") == "1"

    svg: list[str] = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )

    if not static:
        svg.append("""
  <style>
    text {
      font-family: "SFMono-Regular", Consolas, Menlo, monospace;
      font-size: 8px;
      letter-spacing: 0.15px;
      fill: #c9d9f0;
    }
    .ln { opacity: 0; animation: wipe 0.18s ease-out forwards; }
    @keyframes wipe {
      from { opacity: 0; clip-path: inset(0 100% 0 0); }
      to   { opacity: 1; clip-path: inset(0 0% 0 0); }
    }
  </style>""")
    else:
        svg.append("""
  <style>
    text {
      font-family: "SFMono-Regular", Consolas, Menlo, monospace;
      font-size: 8px;
      letter-spacing: 0.15px;
      fill: #c9d9f0;
    }
  </style>""")

    svg.append(
        f'  <rect width="{width}" height="{height}" fill="#0d1117" rx="12"/>'
    )

    for i, row_text in enumerate(lines):
        y = PADDING + i * FONT_H
        # Escape XML special chars in ASCII art (unlikely but safe)
        safe = row_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        delay_ms = i * 28
        if not static:
            svg.append(
                f'  <text class="ln" x="{PADDING}" y="{y}" '
                f'style="animation-delay:{delay_ms}ms;">{safe}</text>'
            )
        else:
            svg.append(f'  <text x="{PADDING}" y="{y}">{safe}</text>')

    svg.append("</svg>")
    OUT.write_text("\n".join(svg), encoding="utf-8")
    print(f"Wrote  →  {OUT}  ({target_h} rows × {TARGET_W} cols)")


if __name__ == "__main__":
    main()
