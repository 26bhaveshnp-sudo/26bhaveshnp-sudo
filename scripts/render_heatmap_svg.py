#!/usr/bin/env python3
"""
render_heatmap_svg.py
Reads data/contributions.json and writes contrib-heatmap.svg — a
53-week × 7-day contribution grid with a diagonal CSS slide-in animation
that plays once on load, then freezes.
"""

import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "contributions.json"
OUT_PATH = ROOT / "contrib-heatmap.svg"

# GitHub-ish green ramp:  0 = empty, 5 = brightest
PALETTE = [
    "#161b22",  # 0 — empty
    "#0e4429",  # 1
    "#006d32",  # 2
    "#26a641",  # 3
    "#39d353",  # 4
    "#69f0a0",  # 5 — neon top end
]


def fmt(n: int) -> str:
    return f"{n:,}"


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def level_for_count(count: int, max_count: int) -> int:
    if max_count <= 0 or count <= 0:
        return 0
    if count >= max_count:
        return 5
    ratio = count / max_count
    if ratio < 0.20:
        return 1
    if ratio < 0.40:
        return 2
    if ratio < 0.70:
        return 3
    return 4


def build_svg(data: dict) -> str:
    days = data.get("days", [])
    if not days:
        raise SystemExit("No contribution data found in contributions.json.")

    counts = {d["date"]: d["count"] for d in days}
    max_count = max(counts.values(), default=1)

    all_dates = sorted(date.fromisoformat(k) for k in counts)
    start_date = all_dates[0]
    end_date = all_dates[-1]

    # Align to Monday / Sunday boundaries
    start_monday = start_date - timedelta(days=start_date.weekday())
    end_sunday = end_date + timedelta(days=(6 - end_date.weekday()))
    total_weeks = (end_sunday - start_monday).days // 7 + 1

    # Normalise to exactly 53 columns
    if total_weeks < 53:
        start_monday -= timedelta(weeks=(53 - total_weeks))
    elif total_weeks > 53:
        start_monday += timedelta(weeks=(total_weeks - 53))

    CELL = 12
    GAP = 3
    PAD = 28          # left/right padding (extra on left for weekday labels)
    TOP_LABEL = 22    # room for month labels above the grid
    BOT_EXTRA = 68    # room for legend + stat footer below the grid

    grid_w = 53 * (CELL + GAP) - GAP
    grid_h = 7 * (CELL + GAP) - GAP
    width  = grid_w + PAD * 2
    height = grid_h + PAD + TOP_LABEL + BOT_EXTRA

    svg: list[str] = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )

    svg.append("""
  <style>
    .day {
      opacity: 0;
      transform: translate(-5px, 5px);
      animation: reveal 0.30s ease-out forwards;
    }
    text { font-family: "SFMono-Regular", Consolas, Menlo, monospace; }
    .lbl  { fill: #c9d1d9; font-size: 11px; }
    .meta { fill: #8b949e; font-size: 11px; }
    .stat { fill: #d0d7de; font-size: 13px; }
    @keyframes reveal {
      from { opacity: 0; transform: translate(-5px, 5px); }
      to   { opacity: 1; transform: translate(0, 0); }
    }
  </style>""")

    # Background
    svg.append(
        f'  <rect width="{width}" height="{height}" fill="#0d1117" rx="12"/>'
    )

    # ── Month labels ──────────────────────────────────────────────────────────
    MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    month_seen: set[int] = set()
    for wi in range(53):
        ws = start_monday + timedelta(weeks=wi)
        m = ws.month
        if m not in month_seen:
            month_seen.add(m)
            x = PAD + wi * (CELL + GAP)
            svg.append(
                f'  <text class="lbl" x="{x}" y="{TOP_LABEL - 4}">'
                f'{MONTH_NAMES[m - 1]}</text>'
            )

    # ── Weekday labels (Mon / Wed / Fri) ─────────────────────────────────────
    for row_idx, label in [(0, "Mon"), (2, "Wed"), (4, "Fri")]:
        y = TOP_LABEL + PAD // 2 + row_idx * (CELL + GAP) + CELL
        svg.append(f'  <text class="meta" x="2" y="{y}">{label}</text>')

    # ── Contribution cells ────────────────────────────────────────────────────
    for wi in range(53):
        for di in range(7):
            day_date = start_monday + timedelta(weeks=wi, days=di)
            count = counts.get(day_date.isoformat(), 0)
            level = level_for_count(count, max_count)
            x = PAD + wi * (CELL + GAP)
            y = TOP_LABEL + PAD // 2 + di * (CELL + GAP)
            fill = PALETTE[level]
            # stagger delay: diagonal front-to-back
            delay_ms = wi * 80 + di * 30
            tooltip = f"{count} contributions on {day_date.isoformat()}"
            svg.append(
                f'  <rect class="day" x="{x}" y="{y}" '
                f'width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{fill}" '
                f'style="animation-delay:{delay_ms}ms;">'
                f'<title>{tooltip}</title>'
                f'</rect>'
            )

    # ── Legend ────────────────────────────────────────────────────────────────
    leg_y = height - BOT_EXTRA + 16
    svg.append(f'  <text class="meta" x="{PAD}" y="{leg_y + 10}">Less</text>')
    for i, color in enumerate(PALETTE):
        lx = PAD + 38 + i * 16
        svg.append(
            f'  <rect x="{lx}" y="{leg_y}" width="12" height="12" '
            f'rx="2" fill="{color}"/>'
        )
    svg.append(
        f'  <text class="meta" '
        f'x="{PAD + 38 + len(PALETTE) * 16 + 6}" y="{leg_y + 10}">More</text>'
    )

    # ── Stats footer ──────────────────────────────────────────────────────────
    total_count = data.get("stats", {}).get("total_contributions", 0)
    c_streak    = data.get("stats", {}).get("current_streak", 0)
    l_streak    = data.get("stats", {}).get("longest_streak", 0)
    svg.append(
        f'  <text class="stat" x="{PAD}" y="{height - 10}">'
        f'{fmt(total_count)} contributions in the last year  '
        f'·  {c_streak}-day streak  '
        f'·  {l_streak} longest'
        f'</text>'
    )

    svg.append("</svg>")
    return "\n".join(svg)


def main() -> None:
    data = load_data()
    svg = build_svg(data)
    OUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Wrote  →  {OUT_PATH}")


if __name__ == "__main__":
    main()
