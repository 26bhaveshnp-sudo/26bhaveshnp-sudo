#!/usr/bin/env python3
"""
fetch_contributions.py

Scrapes the public GitHub contributions calendar for USERNAME and writes
data/contributions.json with raw day counts plus derived stats
(current streak, longest streak, best day, monthly totals).

No token, no auth, no GraphQL -- just the public HTML GitHub already serves.
Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "contributions.json"

USERNAME = os.environ.get("GH_PROFILE_USER", "26bhaveshnp-sudo")
URL = f"https://github.com/users/{USERNAME}/contributions"


def fetch_days():
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        cells = soup.select("rect.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    raw = []
    for cell in cells:
        date_str = cell.get("data-date")
        if not date_str:
            continue
        count_str = cell.get("data-count")
        if count_str is not None:
            try:
                count = int(count_str)
            except ValueError:
                count = 0
        else:
            cell_id = cell.get("id")
            tooltip_el = soup.find("tool-tip", attrs={"for": cell_id}) if cell_id else None
            text = tooltip_el.get_text(strip=True) if tooltip_el else ""
            if re.search(r"no contributions", text, re.I):
                count = 0
            else:
                m = re.match(r"(\d+)", text)
                count = int(m.group(1)) if m else int(cell.get("data-level") or 0)
        level = int(cell.get("data-level") or 0)
        raw.append({"date": date_str, "count": count, "level": level})

    # deduplicate by date
    unique = {}
    for d in raw:
        unique[d["date"]] = d
    days = [unique[k] for k in sorted(unique.keys())]
    return days


def compute_current_streak(days):
    if not days:
        return 0, None, None
    idx = len(days) - 1
    # If today has 0 commits, don't break the streak yet if today isn't over
    if days[idx]["count"] == 0:
        idx -= 1
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days):
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end


def build_data(days):
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"]) if days else {"date": "", "count": 0}
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]} if days else {"start": "", "end": ""},
        "total": total,
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "stats": {
            "current_streak": cur_len,
            "longest_streak": long_len,
            "best_day": best["count"],
            "monthly_totals": monthly,
            "total_contributions": total,
        },
        "days": days,
    }


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    days = fetch_days()
    data = build_data(days)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT_PATH}: {data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, "
          f"longest streak {data['longest_streak']['length']}")


if __name__ == "__main__":
    main()
