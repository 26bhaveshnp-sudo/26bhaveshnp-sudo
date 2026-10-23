#!/usr/bin/env python3
"""
fetch_contributions.py
Scrapes the public GitHub contributions calendar for USERNAME and writes
data/contributions.json with raw day counts plus derived stats.
No auth token required.
"""

import json
from datetime import date, timedelta, datetime
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
    rects = soup.select("rect.ContributionCalendar-day")
    raw = []
    for rect in rects:
        iso_date = rect.get("data-date")
        count_str = rect.get("data-count", "0")
        if not iso_date:
            continue
        try:
            count_int = int(count_str)
        except ValueError:
            count_int = 0
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
        "generated_at": datetime.utcnow().isoformat() + "Z",
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
