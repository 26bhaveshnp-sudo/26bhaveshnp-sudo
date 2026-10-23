#!/usr/bin/env python3
"""
make_info_card.py

Generates info-card.svg — a neofetch-style terminal panel that fades in
line by line. Edit the LINES list below to match your actual bio.

Set STATIC=1 to emit a frozen frame for local preview.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "info-card.svg"

# ── Your info — edit these ────────────────────────────────────────────────────
PROMPT  = "26bhaveshnp@github ~ $ whoami"

LINES = [
    # (key,          value)
    ("user",         "26bhaveshnp-sudo"),
    ("now",          "Building & learning in public"),
    ("stack",        "Python • TypeScript • Linux • Git"),
    ("interests",    "AI • automation • open source"),
    ("contact",      "github.com/26bhaveshnp-sudo"),
]
# ─────────────────────────────────────────────────────────────────────────────

WIDTH   = 520
HEIGHT  = 60 + len(LINES) * 46 + 40  # auto-size to content


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    static = os.environ.get("STATIC", "0") == "1"

    svg: list[str] = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">'
    )

    if not static:
        svg.append("""
  <style>
    text { font-family: "SFMono-Regular", Consolas, Menlo, monospace; }
    .title { fill: #e6edf3; font-size: 17px; }
    .key   { fill: #7dd3fc; font-size: 16px; }
    .val   { fill: #c9d1d9; font-size: 16px; }
    .cursor { fill: #7dd3fc; }
    .ln { opacity: 0; animation: rise 0.38s ease-out forwards; }
    @keyframes rise {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  </style>""")
    else:
        svg.append("""
  <style>
    text { font-family: "SFMono-Regular", Consolas, Menlo, monospace; }
    .title { fill: #e6edf3; font-size: 17px; }
    .key   { fill: #7dd3fc; font-size: 16px; }
    .val   { fill: #c9d1d9; font-size: 16px; }
  </style>""")

    # Card background
    svg.append(
        f'  <rect width="{WIDTH}" height="{HEIGHT}" fill="#0d1117" rx="14"/>'
    )
    # Title bar
    svg.append(
        f'  <rect x="0" y="0" width="{WIDTH}" height="46" '
        f'fill="#111827" rx="14"/>'
    )
    svg.append(
        f'  <rect x="0" y="24" width="{WIDTH}" height="22" fill="#111827"/>'
    )
    # Traffic-light dots
    for i, col in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        svg.append(
            f'  <circle cx="{18 + i * 20}" cy="23" r="6" fill="{col}"/>'
        )
    # Prompt line
    svg.append(
        f'  <text class="title" x="72" y="29">{esc(PROMPT)}</text>'
    )

    # Info rows
    KEY_X = 26
    VAL_X = 160
    y = 76
    for idx, (key, value) in enumerate(LINES):
        delay_ms = idx * 100
        if not static:
            svg.append(
                f'  <g class="ln" style="animation-delay:{delay_ms}ms;">'
            )
        svg.append(
            f'    <text class="key" x="{KEY_X}" y="{y}">{esc(key)}</text>'
        )
        svg.append(
            f'    <text class="val" x="{VAL_X}" y="{y}">: {esc(value)}</text>'
        )
        if not static:
            svg.append("  </g>")
        y += 46

    svg.append("</svg>")
    OUT.write_text("\n".join(svg), encoding="utf-8")
    print(f"Wrote  →  {OUT}")


if __name__ == "__main__":
    main()
