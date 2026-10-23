#!/usr/bin/env python3
"""
fetch_contributions.py
Scrapes the public GitHub contributions calendar for USERNAME and writes
data/contributions.json with raw day counts plus derived stats.
No auth token required.
"""

import json
import re
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

USERNAME = "26bhaveshnp-sudo"


def fetch_contributions_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_contribution_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # GitHub now uses <td class="ContributionCalendar-day"> with data-level (0-4)
    # and a <tool-tip> sibling whose text contains the count.
    # We also try the older <rect> form as a fallback.
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        cells = soup.select("rect.ContributionCalendar-day")

    raw = []
    for cell in cells:
        iso_date = cell.get("data-date")
        if not iso_date:
            continue

        # Try data-count first (old format), then parse the tooltip text
        count_str = cell.get("data-count")
        if count_str is not None:
            try:
                count_int = int(count_str)
            except ValueError:
                count_int = 0
        else:
            # New format: find the associated <tool-tip> by id
            cell_id = cell.get("id", "")
            tooltip_text = ""
            if cell_id:
                # tool-tip has for="<cell_id>"
                tip = soup.find("tool-tip", attrs={"for": cell_id})
                if tip:
                    tooltip_text = tip.get_text()
            # tooltip text is like "3 contributions on October 23, 2026"
            # or "No contributions on ..."
            m = re.match(r"(\d+)\s+contribution", tooltip_text)
            if m:
                count_int = int(m.group(1))
            else:
                # Fall back to data-level as a proxy (level 0=0, 1=1..4 contributions avg)
                level = int(cell.get("data-level", 0))
                count_int = level  # non-zero means active; we use level as-is

        raw.append({"date": iso_date, "count": count_int})

    # deduplicate, keep latest
    unique: dict[str, dict] = {}
    for day in raw:
        unique[day["date"]] = day
    return [unique[k] for k in sorted(unique.keys())]


def current_streak(days: list[dict]) -> int:
    by_date = {d["date"]: d["count"] for d in days}
    if not by_date:
        return 0
    cursor = date.fromisoformat(max(by_date))
    streak = 0
    while cursor.isoformat() in by_date and by_date[cursor.isoformat()] > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak(days: list[dict]) -> int:
    by_date = {d["date"]: d["count"] for d in days}
    if not by_date:
        return 0
    best = running = 0
    for iso in sorted(by_date):
        if by_date[iso] > 0:
            running += 1
            best = max(best, running)
        else:
            running = 0
    return best


def best_day(days: list[dict]) -> int:
    return max((d["count"] for d in days), default=0)


def monthly_totals(days: list[dict]) -> dict[str, int]:
    monthly: dict[str, int] = {}
    for d in days:
        key = date.fromisoformat(d["date"]).strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + d["count"]
    return monthly


def main() -> None:
    print(f"Fetching contributions for {USERNAME} ...")
    html = fetch_contributions_html(USERNAME)
    days = parse_contribution_days(html)
    total = sum(d["count"] for d in days)

    payload = {
        "username": USERNAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "days": days,
        "stats": {
            "current_streak": current_streak(days),
            "longest_streak": longest_streak(days),
            "best_day": best_day(days),
            "monthly_totals": monthly_totals(days),
            "total_contributions": total,
        },
    }

    out = DATA_DIR / "contributions.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {len(days)} days  →  {out}")
    print(f"Total: {total}  |  Current streak: {payload['stats']['current_streak']}  |  Longest: {payload['stats']['longest_streak']}")


if __name__ == "__main__":
    main()
