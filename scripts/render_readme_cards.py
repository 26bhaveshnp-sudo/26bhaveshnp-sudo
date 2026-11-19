#!/usr/bin/env python3
"""
render_readme_cards.py

Render the profile README's cards as animated SVGs into cards/.

Design: "Three Worlds", paper, ink, and three brand colours:
  - BUILD blue (#2f55ff)
  - CRAFT / BRAND red (#ef3b2d)
  - LEARN yellow (#ffc81a)
Typography: Instrument Serif, Geist Sans, Geist Mono.

Every card is a standalone SVG shown through <img>, using only what GitHub
allows there: inline CSS keyframes, SMIL <set> / <animateTransform>,
and fonts embedded as base64 WOFF data URIs (no external requests, no JS).

Live numbers come from data/contributions.json (written by fetch_contributions.py).
Run by .github/workflows/update-profile-art.yml daily.
Set STATIC=1 to freeze animations at their final state for preview/screenshots.
"""
import base64
import datetime
import json
import os
import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "cards"
FONTS = ROOT / "fonts"
PORTRAIT = ROOT / "bhavesh-ascii.svg"
if not PORTRAIT.exists():
    PORTRAIT = ROOT / "avi-ascii.svg"

# ---- profile info -----------------------------------------------------------
NAME_FIRST = "Bhavesh"
NAME_LAST = "Patil"
USERNAME = "26bhaveshnp-sudo"
HEADLINE = "FULLSTACK & AUTOMATION ENGINEER"
BIO_LINES = [
    "Building modern web apps, automation systems,",
    "and exploring AI workflows in public.",
]
LINK_TEXT = "github.com/26bhaveshnp-sudo"
LINK_URL = "https://github.com/26bhaveshnp-sudo"

# ---- brand tokens -----------------------------------------------------------
PAPER = "#f3f3f1"
PAPER_DEEP = "#e2e2de"
INK = "#111111"
INK_SOFT = "#3a3a3c"
MUTED = "#6e6e73"
RULE = "#dcdcd7"
TECH = "#2f55ff"
STUDIO = "#ef3b2d"
LEARN = "#ffc81a"
W = 880  # full card width, GitHub's README column at 100%

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff"),
    "sans": ("Geist", "normal", 400, "geist-400.woff"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""

_font_cache = {}


def font_face(keys):
    out = []
    for k in keys:
        if k not in _font_cache:
            fam, style, weight, fn = FONT_FILES[k]
            fpath = FONTS / fn
            if fpath.exists():
                b64 = base64.b64encode(fpath.read_bytes()).decode()
                _font_cache[k] = (
                    f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
                    f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
                )
            else:
                _font_cache[k] = ""
        out.append(_font_cache[k])
    return "".join(out)


BOTTOM = 12       # bottom padding per row to keep vertical spacing clean
COL = W / 3       # each card in a row of three is exactly a third of the column


def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    """Card of w x h drawn at x=left inside a transparent canvas, padded so rows tile exactly."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w_total, h_total = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):
        css += ".r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_total:.3f}" height="{h_total}" viewBox="0 0 {w_total:.3f} {h_total}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f"<style>{css}</style>{body}</svg>"
    )


def write(name, content):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    print(f"wrote cards/{name} ({len(content) // 1024} KB)")


def d(s):  # animation delay attribute
    return f'style="animation-delay:{s:.2f}s"'


def wrap(text, n):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def text_lines(x, y, lines, lh, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines)
    )


# ---- 1 · hero -----------------------------------------------------------------
def hero():
    h = 420
    portrait_rows = []
    if PORTRAIT.exists():
        src = PORTRAIT.read_text(encoding="utf-8")
        rows = re.findall(r'<text[^>]*\by=["\']([\d.]+)["\'][^>]*>(.*?)</text>', src, re.S)
        for i, (y_val, txt) in enumerate(rows):
            portrait_rows.append(
                f'<text class="f" style="animation-delay:{0.25 + i * 0.02:.3f}s;animation-duration:.35s" '
                f'xml:space="preserve" x="20" y="{y_val}" fill="{INK}" font-size="7.5" '
                f'textLength="600" lengthAdjust="spacing">{txt}</text>'
            )

    s = 0.58
    portrait_markup = (
        f'<g transform="translate(470 42) scale({s}) translate(-20 -20)" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">\n'
        f'{"".join(portrait_rows)}\n</g>'
        if portrait_rows else ""
    )

    body = f"""
<defs>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}"/>
    <stop offset=".5" stop-color="{TECH}"/><stop offset=".58" stop-color="{INK}"/>
    <stop offset="1" stop-color="{INK}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0"
      keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<g class="f" {d(0)}>
  <rect class="live" x="48" y="49" width="8" height="8" rx="2" fill="{TECH}"/>
  <text x="66" y="57" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{escape(HEADLINE)}</text>
</g>
<text class="r" {d(0.15)} x="44" y="190" font-family="{SERIF}" font-size="116" letter-spacing="-2.5" fill="{INK}">{escape(NAME_FIRST)}</text>
<text class="r" {d(0.3)} x="44" y="290" font-family="{SERIF}" font-style="italic" font-size="116" letter-spacing="-2.5" fill="url(#shine)">{escape(NAME_LAST)}</text>
<g class="r" {d(0.55)}>
  {text_lines(48, 338, BIO_LINES, 27, f'font-family="{SANS}" font-size="18" fill="{INK_SOFT}"')}
</g>
<g class="f" {d(0.8)}>
  <text x="48" y="396" font-family="{MONO}" font-size="13" fill="{INK}">{escape(LINK_TEXT)}</text>
  <text class="nu" x="250" y="396" font-family="{MONO}" font-size="13" fill="{TECH}">&#8599;</text>
</g>
{portrait_markup}
"""
    write("hero.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                          f"{NAME_FIRST} {NAME_LAST}. {HEADLINE}. {' '.join(BIO_LINES)}"))


# ---- 2 · world tiles ----------------------------------------------------------
TILE_W, TILE_H = 880 / 3 - 8, 210  # 285.333: two 12px gaps across the row


def count_up(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    """Number counts up from 0 with SMIL <set> frames (works inside <img>), easing out."""
    m = re.match(r"([\d.]+)(.*)", str(num))
    if not m:
        return f'<text x="{x}" y="{y}" {attrs}>{escape(str(num))} <tspan font-style="italic">{escape(word)}</tspan></text>'
    val, suf = float(m.group(1)), m.group(2)
    dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    tail = f' <tspan font-style="italic">{escape(word)}</tspan>'
    if os.environ.get("STATIC"):
        return f'<text x="{x}" y="{y}" {attrs}>{escape(str(num))}{tail}</text>'
    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        txt = str(num) if i == frames else f"{val * e:.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = "" if i == frames else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        out.append(f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
                   f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>')
    return "".join(out)


def tile(name, label, color, on, num, word, blurb, delay, pos):
    lines = wrap(blurb, 34)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.75 + i * 0.1)} x="24" y="{150 + i * 20}" font-family="{SANS}" '
        f'font-size="14" fill="{on}" opacity=".92">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    body = f"""
<defs>
  <clipPath id="card-{name}"><rect width="{TILE_W:.2f}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="slot-{name}"><rect x="0" y="62" width="{TILE_W:.2f}" height="62"/></clipPath>
  <linearGradient id="gl-{name}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card-{name})">
    <rect width="{TILE_W:.2f}" height="{TILE_H}" fill="{color}"/>
    <circle class="rg" {d(delay + 0.5)} cx="{TILE_W - 40:.2f}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".5" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl-{name})" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{label}</text>
  <g class="ai" {d(delay + 0.5)}><text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="{TILE_W - 35:.2f}" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text></g>
  <g clip-path="url(#slot-{name})"><g class="ro" {d(delay + 0.45)}>
    {count_up(num, word, 22, 112, f'font-family="{SERIF}" font-size="44" fill="{on}"', delay + 0.45)}
  </g></g>
  {blurb_svg}
</g>
"""
    write(f"{name}.svg", svg(TILE_W, TILE_H, body, ["serif", "serif-i", "sans", "mono"],
                             f"{label}: {num} {word}. {blurb}", left=4 * pos, right=8 - 4 * pos))


# ---- 3 · activity (monthly bars) ------------------------------------------------
def activity(data):
    h = 340
    monthly = data.get("monthly", [])[-12:]
    if not monthly:
        monthly = [{"month": k, "total": v} for k, v in sorted(data.get("stats", {}).get("monthly_totals", {}).items())][-12:]
    
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"]) if monthly else {"total": 1, "month": "2026-01"}
    top = max(1, best["total"])
    x0, x1, base, maxh, gap = 40, 600, 292, 140, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / max(1, len(monthly))
    bars = []
    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = (m["month"] == best["month"])
        bh = max(4, round(m["total"] / top * maxh)) if m["total"] > 0 else 4
        x = x0 + i * (bw + gap)
        fill = TECH if is_best else ("#c9c9c4" if partial else (INK if m["total"] > 0 else "#e2e2de"))
        try:
            label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
        except Exception:
            label = m["month"][-2:]
        bars.append(
            f'<rect class="g" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">{label}</text>'
        )
        if is_best and m["total"] > 0:
            bars.append(
                f'<text class="p" style="animation-delay:3.2s" x="{x + bw / 2:.1f}" y="{base - bh - 10}" '
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{TECH}">{m["total"]:,}</text>'
            )

    cur_s = data.get("current_streak", {})
    cs = cur_s.get("length", 0) if isinstance(cur_s, dict) else int(cur_s or 0)
    long_s = data.get("longest_streak", {})
    ls = long_s.get("length", 0) if isinstance(long_s, dict) else int(long_s or 0)
    streak_note = "current streak, and the longest" if cs >= ls and cs > 0 else f"current streak, longest {ls}"
    
    total_days = len(data.get("days", [])) or 365
    active_days = data.get("active_days") or sum(1 for d in data.get("days", []) if d.get("count", 0) > 0)
    best_day_info = data.get("best_day", {})
    best_day_count = best_day_info.get("count", 0) if isinstance(best_day_info, dict) else int(best_day_info or 0)
    total_contrib = data.get("total_contributions", data.get("total", 0))

    stats = [
        (f'{cs} <tspan font-style="italic">days</tspan>', streak_note),
        (f'{active_days}<tspan fill="#8e8e93"> / {total_days}</tspan>', "days with a commit"),
        (f'{best_day_count}', "on the busiest day"),
    ]
    side = []
    for i, (big, small) in enumerate(stats):
        y = 104 + i * 92
        side.append(
            f'<g class="r" {d(2.6 + i * 0.15)}>'
            f'<text x="650" y="{y}" font-family="{SERIF}" font-size="40" fill="{INK}">{big}</text>'
            f'<text x="650" y="{y + 24}" font-family="{SANS}" font-size="13" fill="{MUTED}">{small}</text></g>'
        )
        if i < 2:
            side.append(f'<rect class="f" {d(2.6)} x="650" y="{y + 44}" width="190" height="1" fill="{RULE}"/>')
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="f" {d(1.9)} x="40" y="58" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.0)} x="38" y="114" font-family="{SERIF}" font-size="52" fill="{INK}">{total_contrib:,} <tspan font-style="italic">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    write("activity.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                              f"{total_contrib:,} contributions in the last year, {cs}-day streak"))


# ---- 4 · repo cards -----------------------------------------------------------
REPO_W, REPO_H = 880 / 3 - 8, 176
REPOS = [
    ("FieldForceConnect-QA-Machine-Test", "Automated QA test suite: Selenium, TestNG, Maven & Postman API tests.", "Java", STUDIO),
    ("26bhaveshnp-sudo", "Dynamic animated SVG profile cards & daily scheduled GitHub Actions.", "Python", TECH),
    ("automation-lab", "Exploring modern web tooling, AI integrations, and developer workflows.", "TypeScript", LEARN),
]


def repo_card(i, name, desc, lang, color, stars=0):
    delay = 4.6 + i * 0.12
    meta = f"{lang}  ·  ★ {stars}" if stars else f"{lang}  ·  live"
    body = f"""
<rect width="{REPO_W:.2f}" height="{REPO_H}" rx="14" fill="{PAPER}"/>
<g class="r" {d(delay)}>
  <rect x="24" y="30" width="8" height="8" rx="2" fill="{color}"/>
  <text x="40" y="39" font-family="{SANS}" font-weight="600" font-size="16" fill="{INK}">{escape(name if len(name) <= 24 else name[:22] + '…')}</text>
  {text_lines(24, 72, wrap(desc, 34), 21, f'font-family="{SANS}" font-size="14" fill="{INK_SOFT}"')}
  <text x="24" y="{REPO_H - 24}" font-family="{MONO}" font-size="12" fill="{MUTED}">{escape(meta)}</text>
</g>
"""
    write(f"repo-{name}.svg", svg(REPO_W, REPO_H, body, ["sans", "sans-b", "mono"], f"{name}: {desc}",
                                  left=4 * i, right=8 - 4 * i))


def section_title(text, italic, theme):
    fg = "#e6edf3" if theme == "dark" else INK
    body = (
        f'<text class="r" {d(4.4)} x="2" y="46" font-family="{SERIF}" font-size="34" fill="{fg}">{escape(text)} '
        f'<tspan font-style="italic">{escape(italic)}</tspan></text>'
    )
    write(f"title-coding-{theme}.svg", svg(W, 64, body, ["serif", "serif-i"], f"{text} {italic}", bottom=0))


# ---- 5 · blue contribution graph -----------------------------------------------
BLUE = [PAPER_DEEP, "#c8d3ff", "#94a8ff", "#6280ff", TECH, "#1a3be0"]


def level_for(c):
    return 0 if c == 0 else 1 if c <= 3 else 2 if c <= 7 else 3 if c <= 14 else 4 if c <= 20 else 5


def heatmap(data):
    days = data.get("days", [])
    if not days:
        return
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday = 0
    cell, step, gx, gy = 12, 15, 44, 96
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date_obj = datetime.date.fromisoformat(day["date"])
        if date_obj.day <= 7 and (date_obj.year, date_obj.month) not in seen and row == 0:
            seen.add((date_obj.year, date_obj.month))
            months.append((col, date_obj.strftime("%b")))
        c = day.get("count", 0)
        delay = 1.0 + col * 0.03 + row * 0.02
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="3" fill="{BLUE[level_for(c)]}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )
    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    legend_x = right - len(BLUE) * 14
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">{m}</text>'
        for col, m in months if (gx + col * step + 32) < (legend_x - 36)
    )
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(BLUE)
    )
    h = gy + 7 * step + 44
    total_contrib = data.get("total_contributions", data.get("total", 0))
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="r" {d(0.8)} x="42" y="62" font-family="{SERIF}" font-size="34" fill="{INK}">Every day, <tspan font-style="italic" fill="{TECH}">in blue</tspan></text>
<text class="f" {d(0.8)} x="{right}" y="60" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.4)}>{labels}
<text x="{legend_x - 8}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>
{legend}
<text x="{legend_x + len(BLUE) * 14 + 2}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text></g>
"""
    write("heatmap.svg", svg(W, h, body, ["serif", "serif-i", "mono"],
                             f"Contribution graph: {total_contrib:,} contributions in the last year"))


def repo_stars():
    stars = {}
    try:
        import requests
        for name, *_ in REPOS:
            r = requests.get(f"https://api.github.com/repos/{USERNAME}/{name}", timeout=5)
            if r.ok:
                stars[name] = r.json().get("stargazers_count", 0)
    except Exception as e:
        print(f"stars unavailable: {e}")
    return stars


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    
    # 1. Hero
    hero()
    
    # 2. Three World Tiles
    # BUILD (Blue #2f55ff), CRAFT/TEST (Red #ef3b2d), LEARN (Yellow #ffc81a)
    tile("build", "BUILD", TECH, "#ffffff", "5+", "projects",
         "Full-stack apps, QA automation test suites, and open-source tools.", 3.1, 0)
    tile("brand", "CRAFT", STUDIO, "#ffffff", "100%", "automated",
         "Selenium, TestNG, Maven & Postman API test automation workflows.", 3.35, 1)
    
    cur_streak = data.get("current_streak", {})
    streak_val = cur_streak.get("length", 0) if isinstance(cur_streak, dict) else int(cur_streak or 0)
    streak_str = str(streak_val) if streak_val > 0 else "Daily"
    tile("learn", "LEARN", LEARN, INK, streak_str, "day streak",
         "Consistent daily coding, continuous learning, and sharing in public.", 3.6, 2)
    
    # 3. Monthly Activity Bars
    activity(data)
    
    # 4. Featured Repos
    stars = repo_stars()
    for i, (name, desc, lang, color) in enumerate(REPOS):
        repo_card(i, name, desc, lang, color, stars.get(name, 0))
    section_title("What I'm", "coding", "dark")
    section_title("What I'm", "coding", "light")
    
    # 5. Blue Heatmap
    heatmap(data)


if __name__ == "__main__":
    main()
