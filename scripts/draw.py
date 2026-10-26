#!/usr/bin/env python3
"""Draws every graphic on the profile README, in a light and a dark variant.

Every glyph is outlined to a path. GitHub serves README images through a proxy
that cannot load web fonts, so live <text> would fall back to whatever the
viewer has installed. Outlined, the graphics look the same on every machine.

    pip install fonttools uharfbuzz brotli
    python scripts/draw.py              # header, cards, sections, stack -> assets/
    python scripts/draw.py activity     # needs GITHUB_TOKEN; run daily by Actions
    python scripts/draw.py activity --sample   # fake data, for previewing locally

Fonts (all OFL) are fetched from google/fonts on first run and cached.
"""

import argparse
import datetime as dt
import json
import os
import random
import urllib.request
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "evanclan-header"
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
LOGIN = "evanclan"

# (local name, upstream path, wght to instance at or None for static fonts)
FONTS = {
    "serif":        ("InstrumentSerif-Regular.ttf", "instrumentserif/InstrumentSerif-Regular.ttf", None),
    "serif-italic": ("InstrumentSerif-Italic.ttf",  "instrumentserif/InstrumentSerif-Italic.ttf",  None),
    "mono":         ("FiraCode-Regular.ttf",        "firacode/FiraCode%5Bwght%5D.ttf",             400),
    "mono-medium":  ("FiraCode-Medium.ttf",         "firacode/FiraCode%5Bwght%5D.ttf",             500),
    "jp":           ("NotoSansJP-Regular.ttf",      "notosansjp/NotoSansJP%5Bwght%5D.ttf",         400),
    "jp-light":     ("NotoSansJP-Light.ttf",        "notosansjp/NotoSansJP%5Bwght%5D.ttf",         300),
}

PALETTES = {
    "dark": {
        "bg": "#0c0b09", "edge": "#2a2214", "glow": "#ffb000", "glow_op": "0.11",
        "dots": "#ffb000", "dots_op": "0.16",
        "name": "#ffb000", "lede": "#d6ae6a", "meta": "#8c7448",
        "label": "#7d6537", "value": "#f1dcb3", "rule": "#2e2615",
        "tick": "#5a4723", "cursor": "#ffb000", "jp": "#4a3b1f",
        "live": "#3ddc84", "review": "#ffb000", "open": "#5ac8ff", "build": "#e05a3a",
        "heat": ["#1a1710", "#4d3700", "#8f6500", "#d99400", "#ffc24d"],
    },
    "light": {
        "bg": "#fbf7ee", "edge": "#e6dac0", "glow": "#ffb000", "glow_op": "0.12",
        "dots": "#a87400", "dots_op": "0.18",
        "name": "#1c1508", "lede": "#8a5a00", "meta": "#8f7c58",
        "label": "#9a865f", "value": "#2b2214", "rule": "#e7dbc0",
        "tick": "#cdb98f", "cursor": "#d99400", "jp": "#dccba5",
        "live": "#1f9d55", "review": "#c98a00", "open": "#1f78b4", "build": "#c2410c",
        "heat": ["#efe6d3", "#f2d38a", "#e3a92e", "#b97800", "#7a4f00"],
    },
}


def fmt(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# --- type engine --------------------------------------------------------------

def font_file(key):
    name, upstream, wght = FONTS[key]
    out = CACHE / name
    if out.exists():
        return out
    CACHE.mkdir(parents=True, exist_ok=True)
    raw = CACHE / upstream.rsplit("/", 1)[1].replace("%5B", "[").replace("%5D", "]")
    if not raw.exists():
        urllib.request.urlretrieve(GF + upstream, raw)
    if wght is None:
        raw.rename(out)
    else:
        tt = TTFont(raw)
        instancer.instantiateVariableFont(tt, {"wght": wght}, inplace=True)
        tt.save(out)
    return out


class Face:
    def __init__(self, key):
        path = str(font_file(key))
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        self.cmap = self.tt.getBestCmap()
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(path)))

    def covers(self, ch):
        return ch.isspace() or ord(ch) in self.cmap


FACES = {}


def face(key):
    if key not in FACES:
        FACES[key] = Face(key)
    return FACES[key]


def outline(f, name, transform):
    # The pen needs the face's glyph set to resolve composite glyphs.
    pen = SVGPathPen(f.glyphs, ntos=fmt)
    f.glyphs[name].draw(TransformPen(pen, transform))
    return pen.getCommands()


def split_runs(text, primary, fallback_key):
    runs, cur, cur_face = [], "", None
    for ch in text:
        # Spaces always come from the primary face; CJK fonts carry narrower ones.
        # The fallback is only loaded when a glyph actually needs it.
        f = primary if primary.covers(ch) else face(fallback_key)
        if f is not cur_face and cur:
            runs.append((cur_face, cur))
            cur = ""
        cur_face = f
        cur += ch
    if cur:
        runs.append((cur_face, cur))
    return runs


def set_line(text, x, y, size, key, *, tracking=0.0, fallback="jp", jp_scale=0.94,
             anchor="start", features=None):
    """Returns (path data, advance width) for one line of text."""
    primary = face(key)
    features = features or {"kern": True, "liga": True, "calt": False}

    placed, cursor = [], 0.0
    for f, run in split_runs(text, primary, fallback):
        s = size / f.upem * (1 if f is primary else jp_scale)
        buf = hb.Buffer()
        buf.add_str(run)
        buf.guess_segment_properties()
        hb.shape(f.hb, buf, features)
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            placed.append((f, f.order[info.codepoint], s, cursor + pos.x_offset * s, pos.y_offset * s))
            cursor += pos.x_advance * s + tracking
    width = cursor - tracking if placed else 0.0

    x0 = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
    d = "".join(outline(f, name, (s, 0, 0, -s, x0 + dx, y - dy)) for f, name, s, dx, dy in placed)
    return d, width


def measure(text, size, key, **kw):
    return set_line(text, 0, 0, size, key, **kw)[1]


def wrap(text, width, size, key, **kw):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and measure(trial, size, key, **kw) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def set_vertical(text, x, y, size, key):
    """Stacks CJK characters top to bottom, each centred on x."""
    f = face(key)
    s = size / f.upem
    d = ""
    for i, ch in enumerate(text):
        name = f.cmap[ord(ch)]
        adv = f.tt["hmtx"][name][0] * s
        d += outline(f, name, (s, 0, 0, -s, x - adv / 2, y + i * size * 1.18))
    return d


class Canvas:
    """Collects SVG fragments; text() outlines a line and appends it."""

    def __init__(self, w, h, title, desc, css=""):
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="title desc">',
            f"<title id=\"title\">{esc(title)}</title><desc id=\"desc\">{esc(desc)}</desc>",
            "<style>"
            ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.6s ease-out infinite}"
            "@keyframes pulse{0%{transform:scale(1);opacity:.55}80%,100%{transform:scale(3.2);opacity:0}}"
            f"{css}"
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}.pulse{opacity:0}}"
            "</style>",
        ]

    def add(self, s):
        self.parts.append(s)

    def text(self, s, x, y, size, key, fill, **kw):
        d, w = set_line(s, x, y, size, key, **kw)
        if d:
            self.add(f'<path fill="{fill}" d="{d}"/>')
        return w

    def status_dot(self, cx, cy, color, live):
        if live:
            self.add(f'<circle class="pulse" cx="{fmt(cx)}" cy="{fmt(cy)}" r="3.5" fill="{color}"/>')
        self.add(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="3.5" fill="{color}"/>')

    def svg(self):
        return "\n".join(self.parts + ["</svg>"]) + "\n"


def panel(c, p, x, y, w, h, rx=18, glow_at=None, dots=True):
    """The shared card surface: ink fill, amber glow, faded dot grid, hairline edge."""
    uid = f"{int(x)}_{int(y)}"
    gx, gy = glow_at or (x + w - 150, y + 40)
    c.add("<defs>"
          f'<pattern id="dots{uid}" width="22" height="22" patternUnits="userSpaceOnUse">'
          f'<circle cx="11" cy="11" r="1" fill="{p["dots"]}"/></pattern>'
          f'<radialGradient id="glow{uid}" cx="{fmt(gx)}" cy="{fmt(gy)}" r="{fmt(max(w, h) * 0.55)}" gradientUnits="userSpaceOnUse">'
          f'<stop offset="0" stop-color="{p["glow"]}" stop-opacity="{p["glow_op"]}"/>'
          f'<stop offset="1" stop-color="{p["glow"]}" stop-opacity="0"/></radialGradient>'
          f'<radialGradient id="fadeg{uid}" cx="{fmt(gx)}" cy="{fmt(gy)}" r="{fmt(max(w, h) * 0.47)}" gradientUnits="userSpaceOnUse">'
          '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
          f'<mask id="fade{uid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#fadeg{uid})"/></mask>'
          f'<clipPath id="clip{uid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>'
          "</defs>")
    c.add(f'<g clip-path="url(#clip{uid})">')
    c.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{p["bg"]}"/>')
    c.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#glow{uid})"/>')
    if dots:
        c.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#dots{uid})" '
              f'mask="url(#fade{uid})" opacity="{p["dots_op"]}"/>')
    c.add("</g>")
    c.add(f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{w - 1}" height="{h - 1}" rx="{rx - 0.5}" '
          f'fill="none" stroke="{p["edge"]}"/>')


# --- content ------------------------------------------------------------------

HEADER = {
    "handle": "infinity_block",
    "where": "JAPAN  ·  UTC+9",
    "name": "Evan Alferez",
    "lede": "I build the software Japanese businesses run on.",
    "vertical": "設計から運用まで",  # "from design to operation", the line from evanserv.com
    "columns": [
        ("SHIPPING",      "帳場ラボ · Chouba Lab"),
        ("IN PRODUCTION", "Sabizu · Happy Island"),
        ("OPEN DATA",     "OpenJLPT"),
        ("SPEAKS",        "EN · 日本語 · CEB · TL"),
    ],
}

# status -> (label, palette colour, pulses, counts as in production)
STATUS = {
    "review":   ("IN REVIEW",   "review", True,  True),
    "live":     ("LIVE",        "live",   True,  True),
    "in-use":   ("IN USE",      "live",   True,  True),
    "active":   ("ACTIVE",      "live",   True,  True),
    "open":     ("OPEN SOURCE", "open",   False, False),
    "building": ("BUILDING",    "build",  False, False),
}

PROJECTS = [
    {
        "id": "chouba-lab", "name": "Chouba Lab", "jp": "帳場ラボ", "kicker": "SHOPIFY → FREEE",
        "status": "review", "link": "https://choubalab.com",
        "pitch": "Orders, refunds and payout fees become itemised, tax-correct journal entries in freee.",
        "stack": "Remix · Polaris · Prisma · Fly.io",
        "metric": ("Since Jul 2026", "IN PRODUCTION"),
    },
    {
        "id": "sabizu", "name": "Sabizu", "kicker": "BOOKING SAAS",
        "status": "live", "link": "https://sabizu.com",
        "pitch": "Booking for one-person shops. Overlapping slots are rejected by Postgres itself.",
        "stack": "Next.js 16 · Supabase · Stripe",
        "metric": ("10/10", "TABLES WITH VERIFIED RLS"),
    },
    {
        "id": "happy-island", "name": "Happy Island", "kicker": "PARENT ↔ TEACHER",
        "status": "live", "link": "https://apps.apple.com/jp/app/happy-island/id6760802460?l=en-US",
        "pitch": "School messaging for primary-school families, on iOS, Android and the web.",
        "stack": "Expo · Next.js 16 · Supabase · CF Workers",
        "metric": ("1", "BACKEND FOR ALL THREE APPS"),
    },
    {
        "id": "openjlpt", "name": "OpenJLPT", "kicker": "JLPT N5–N1 DATASET",
        "status": "open", "link": "https://github.com/evanclan/OpenJLPT",
        "pitch": "7,811 words, 2,383 kanji and 526 grammar points, on npm, PyPI and SQLite.",
        "stack": "TypeScript · SQLite · CI-validated",
        "metric": ("99.7%", "OF WORDS LINKED TO JMDICT"),
    },
    {
        "id": "raja-r", "name": "raja-r.com", "jp": "かえる留学", "kicker": "SITE MIGRATION",
        "status": "live", "link": "https://www.raja-r.com",
        "pitch": "A study-abroad agency moved off Jimdo without losing the rankings it had earned.",
        "stack": "Next.js 16 · Vercel · Resend",
        "metric": ("26", "LEGACY URLS, ONE-HOP 301"),
    },
    {
        "id": "attendance", "name": "Attendance", "kicker": "ATTENDANCE & PAYROLL",
        "status": "in-use", "link": "https://github.com/evanclan/natsuki-attendance",
        "pitch": "RFID and QR check-in, payroll, and LINE alerts to guardians for schools.",
        "stack": "Next.js · Supabase · LINE · n8n",
        "metric": ("RFID + QR", "CHECK-IN, SEVERAL CLIENTS"),
    },
    {
        "id": "guro-ako", "name": "Guro Ako", "kicker": "EDUCATION MEDIA · PH",
        "status": "active", "link": "https://www.facebook.com/mgakaguro.page/",
        "pitch": "A community, a video channel and a web platform for Filipino teachers.",
        "stack": "Next.js · Sanity · YouTube Data API",
        "metric": ("500K+", "COMBINED REACH SINCE 2021"),
    },
    {
        "id": "ryuugaku-quest", "name": "Ryuugaku Quest", "jp": "留学クエスト", "kicker": "GODOT 4.7 RPG",
        "status": "building", "link": None,
        "pitch": "Right answers are attacks. Missed words respawn through spaced repetition.",
        "stack": "Godot · GDScript · Python",
        "metric": ("英検 5–2級", "EIKEN LEVEL BANDS"),
    },
]

SECTIONS = [
    ("work",     "Work",        lambda: "{} projects · {} in production".format(
        len(PROJECTS), sum(STATUS[p["status"]][3] for p in PROJECTS))),
    ("progress", "In progress", lambda: "on the bench"),
    ("method",   "How I work",  lambda: "five rules"),
    ("stack",    "Stack",       lambda: "{} tools".format(sum(len(g[1]) for g in STACK))),
    ("activity", "Activity",    lambda: "redrawn daily by GitHub Actions"),
    ("contact",  "Elsewhere",   lambda: "EN · 日本語 · CEB · TL"),
]

STACK = [
    ("PRODUCT",  ["TypeScript", "React", "Next.js", "React Native", "Remix", "Tailwind"]),
    ("DATA",     ["PostgreSQL", "Supabase RLS", "Prisma", "SQLite", "OAuth 2.0"]),
    ("INFRA",    ["Vercel", "Fly.io", "Cloudflare Workers", "Netlify", "GitHub Actions"]),
    ("COMMERCE", ["Shopify apps", "freee", "Money Forward", "Stripe", "LINE", "Resend"]),
    ("AI",       ["Claude", "OpenAI", "Gemini", "MCP servers", "n8n", "Playwright"]),
    ("CRAFT",    ["Godot", "After Effects", "Premiere Pro", "Photoshop", "Illustrator"]),
]


# --- header -------------------------------------------------------------------

def draw_header(p):
    W, H, PAD = 1200, 440, 64
    h = HEADER
    desc = ("Evan Alferez (infinity_block), full-stack engineer in Japan. "
            + ". ".join(f"{k.title()}: {v}" for k, v in h["columns"]) + ".")
    c = Canvas(W, H, h["name"], desc, css=".cursor{animation:blink 1.1s steps(1) infinite}"
                                           "@keyframes blink{50%{opacity:0}}")
    panel(c, p, 0, 0, W, H, glow_at=(W - 170, 40))

    c.text(h["handle"], PAD, 70, 14, "mono-medium", p["meta"], tracking=1.6)
    w = c.text(h["where"], W - PAD, 70, 13, "mono", p["meta"], tracking=1.8, anchor="end")
    c.status_dot(W - PAD - w - 18, 65.5, p["live"], True)

    w = c.text(h["name"], PAD - 4, 212, 128, "serif", p["name"], tracking=-0.5)
    c.add(f'<rect class="cursor" x="{fmt(PAD + w + 10)}" y="128" width="30" height="86" fill="{p["cursor"]}"/>')
    c.text(h["lede"], PAD, 268, 34, "serif-italic", p["lede"], tracking=0.1)
    c.add(f'<path fill="{p["jp"]}" d="{set_vertical(h["vertical"], W - PAD - 12, 134, 19, "jp-light")}"/>')

    rule_y = 326
    c.add(f'<path stroke="{p["rule"]}" d="M{PAD} {rule_y}H{W - PAD}"/>')
    col_w = (W - 2 * PAD) / len(h["columns"])
    ticks = "".join(f"M{fmt(PAD + i * col_w)} {rule_y - 5}v10" for i in range(len(h["columns"])))
    c.add(f'<path stroke="{p["tick"]}" d="{ticks}M{W - PAD} {rule_y - 5}v10"/>')
    for i, (label, value) in enumerate(h["columns"]):
        x = PAD + i * col_w
        c.text(f"0{i + 1}  {label}", x, 362, 11.5, "mono-medium", p["label"], tracking=2.2)
        c.text(value, x, 394, 17, "mono", p["value"], tracking=0.2)
    return c.svg()


# --- project cards --------------------------------------------------------------

def draw_card(p, proj):
    # A transparent 10px gutter is drawn into each card, so two cards set side by
    # side at width="50%" get a gap without any markup between them.
    W, H, G = 600, 344, 10
    x0, y0, w, h = G, G, W - 2 * G, H - 2 * G
    L, R = x0 + 34, x0 + w - 34
    label, colour, pulses, _ = STATUS[proj["status"]]
    metric, metric_label = proj["metric"]

    desc = f'{proj["name"]}: {proj["pitch"]} {metric} {metric_label.lower()}. Status: {label.lower()}.'
    c = Canvas(W, H, proj["name"], desc)
    panel(c, p, x0, y0, w, h, rx=16, glow_at=(x0 + w - 90, y0 + 20))

    c.text(proj["kicker"], L, y0 + 46, 11.5, "mono-medium", p["label"], tracking=2.2)
    sw = c.text(label, R, y0 + 46, 11, "mono-medium", p[colour], tracking=1.8, anchor="end")
    c.status_dot(R - sw - 14, y0 + 41.8, p[colour], pulses)

    nw = c.text(proj["name"], L - 2, y0 + 112, 54, "serif", p["value"], tracking=-0.3)
    if proj.get("jp"):
        c.text(proj["jp"], L + nw + 14, y0 + 110, 19, "jp-light", p["meta"])

    for i, line in enumerate(wrap(proj["pitch"], R - L, 22, "serif-italic")[:2]):
        c.text(line, L, y0 + 150 + i * 28, 22, "serif-italic", p["lede"])

    c.text(proj["stack"], L, y0 + 228, 11.5, "mono", p["label"], tracking=0.6)

    rule_y = y0 + 248
    c.add(f'<path stroke="{p["rule"]}" d="M{L} {rule_y}H{R}"/>')
    mw = c.text(metric, L - 1, y0 + 296, 40, "serif", p["name"], fallback="jp", jp_scale=0.78)
    c.text(metric_label, L + mw + 16, y0 + 291, 10.5, "mono-medium", p["meta"], tracking=1.8)
    if proj["link"]:
        c.text("↗", R, y0 + 294, 20, "mono", p["meta"], anchor="end")
    return c.svg()


# --- section dividers -----------------------------------------------------------

def draw_section(p, index, title, note):
    W, H = 1200, 96
    c = Canvas(W, H, title, f"Section {index:02d}: {title}. {note}.")
    c.text(f"{index:02d}", 2, 62, 14, "mono-medium", p["cursor"], tracking=1.5)
    tw = c.text(title, 44, 64, 46, "serif", p["value"], tracking=-0.2)
    nw = c.text(note.upper() if note.isascii() else note, W - 2, 60, 11, "mono-medium", p["meta"],
                tracking=1.8, anchor="end")
    x1, x2 = 44 + tw + 22, W - 2 - nw - 22
    if x2 > x1:
        c.add(f'<path stroke="{p["rule"]}" d="M{fmt(x1)} 55.5H{fmt(x2)}"/>')
        c.add(f'<circle cx="{fmt(x1)}" cy="55.5" r="2" fill="{p["tick"]}"/>')
    return c.svg()


# --- stack panel ----------------------------------------------------------------

def draw_stack(p):
    W, PAD, LINE = 1200, 56, 28
    cols = 3
    cw = (W - 2 * PAD) / cols

    def lines(items):
        out, line = [], ""
        for item in items:
            trial = f"{line} · {item}" if line else item
            if line and measure(trial, 17, "mono") > cw - 34:
                out.append(line)
                line = item
            else:
                line = trial
        return out + [line]

    groups = [(label, items, lines(items)) for label, items in STACK]
    rows = [groups[i:i + cols] for i in range(0, len(groups), cols)]
    row_h = [40 + max(len(g[2]) for g in row) * LINE for row in rows]
    H = 2 * PAD + sum(row_h) + 28 * (len(rows) - 1)

    desc = " ".join(f"{label}: {', '.join(items)}." for label, items in STACK)
    c = Canvas(W, H, "Stack", desc)
    panel(c, p, 0, 0, W, H, glow_at=(80, H - 20))

    y = PAD
    for row, rh in zip(rows, row_h):
        for i, (label, items, text_lines) in enumerate(row):
            x = PAD + i * cw
            c.text(label, x, y + 14, 11.5, "mono-medium", p["label"], tracking=2.2)
            c.text(f"{len(items):02d}", x + cw - 34, y + 14, 11.5, "mono", p["tick"], tracking=1, anchor="end")
            c.add(f'<path stroke="{p["rule"]}" d="M{fmt(x)} {fmt(y + 28)}H{fmt(x + cw - 34)}"/>')
            for j, line in enumerate(text_lines):
                c.text(line, x, y + 60 + j * LINE, 17, "mono", p["value"])
        y += rh + 28
    return c.svg()


# --- activity -------------------------------------------------------------------

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { totalContributions weeks { contributionDays {
    date contributionCount contributionLevel } } } } } }"""


def fetch_calendar(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]])
             for d in w["contributionDays"]] for w in cal["weeks"]]


def sample_calendar():
    rng = random.Random(7)
    end = dt.date.today()
    start = end - dt.timedelta(days=end.weekday() + 1 + 52 * 7)
    weeks, day = [], start
    while day <= end:
        week = []
        for _ in range(7):
            if day > end:
                break
            n = 0 if rng.random() < 0.3 else int(rng.expovariate(1 / 6))
            week.append((day.isoformat(), n, 0 if n == 0 else min(4, 1 + n // 5)))
            day += dt.timedelta(days=1)
        weeks.append(week)
    return weeks


def streaks(days):
    longest = run = 0
    for _, n, _ in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    # Today often has no contributions yet; don't let that zero the current streak.
    current, tail = 0, days[:-1] if days and days[-1][1] == 0 else days
    for _, n, _ in reversed(tail):
        if not n:
            break
        current += 1
    return current, longest


def draw_activity(p, weeks):
    W, H, PAD = 1200, 300, 56
    days = [d for w in weeks for d in w]
    total = sum(n for _, n, _ in days)
    current, longest = streaks(days)
    best = max(days, key=lambda d: d[1])
    best_day = dt.date.fromisoformat(best[0]).strftime("%b %-d")
    active = sum(1 for _, n, _ in days if n)

    plural = lambda n: f"{n} day" if n == 1 else f"{n} days"
    desc = (f"{total:,} contributions in the last year across {active} active days. "
            f"Longest streak {plural(longest)}, current streak {plural(current)}.")
    cell, gap = 12, 3
    gx = W - PAD - len(weeks) * (cell + gap) + gap
    c = Canvas(W, H, "Activity", desc)
    panel(c, p, 0, 0, W, H, glow_at=(140, 40))

    c.text("LAST 12 MONTHS", PAD, PAD + 14, 11.5, "mono-medium", p["label"], tracking=2.2)
    c.text(f"{total:,}", PAD - 3, PAD + 94, 76, "serif", p["name"], tracking=-0.5)
    c.text("contributions", PAD, PAD + 126, 22, "serif-italic", p["lede"])
    rows = [("longest streak", plural(longest)), ("current streak", plural(current)),
            ("busiest day", f"{best_day} · {best[1]}")]
    for i, (k, v) in enumerate(rows):
        y = PAD + 164 + i * 22
        c.text(k.upper(), PAD, y, 10.5, "mono-medium", p["meta"], tracking=1.6)
        c.text(v, gx - 44, y, 13, "mono", p["value"], anchor="end")

    # month labels, at the first column whose week starts in a new month
    gy, last, last_i = PAD + 50, None, -9
    for i, w in enumerate(weeks):
        m = dt.date.fromisoformat(w[0][0]).strftime("%b")
        if m != last and i - last_i >= 3 and i < len(weeks) - 2:
            c.text(m.upper(), gx + i * (cell + gap), gy - 14, 10, "mono-medium", p["meta"], tracking=1.2)
            last_i = i
        last = m
    for r, name in ((1, "MON"), (3, "WED"), (5, "FRI")):
        c.text(name, gx - 12, gy + r * (cell + gap) + 9.5, 9.5, "mono", p["tick"], anchor="end")

    for i, w in enumerate(weeks):
        for date, _, level in w:
            r = dt.date.fromisoformat(date).isoweekday() % 7  # Sunday = row 0, as on GitHub
            c.add(f'<rect x="{fmt(gx + i * (cell + gap))}" y="{fmt(gy + r * (cell + gap))}" width="{cell}" '
                  f'height="{cell}" rx="2.5" fill="{p["heat"][level]}"/>')

    ly = gy + 7 * (cell + gap) + 26
    lx = W - PAD - 5 * (cell + gap) + gap
    c.text("LESS", lx - 10, ly + 9.5, 9.5, "mono", p["meta"], tracking=1.2, anchor="end")
    for i, colour in enumerate(p["heat"]):
        c.add(f'<rect x="{fmt(lx + i * (cell + gap))}" y="{ly}" width="{cell}" height="{cell}" rx="2.5" fill="{colour}"/>')
    c.text("MORE", W - PAD + 10, ly + 9.5, 9.5, "mono", p["meta"], tracking=1.2)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("drawn %Y-%m-%d %H:%M JST")
    c.text(stamp, gx, ly + 9.5, 9.5, "mono", p["tick"], tracking=1)
    return c.svg()


# --- main -----------------------------------------------------------------------

def write(out, name, svg):
    path = out / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} ({len(svg) // 1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="?", default="static", choices=["static", "activity"])
    ap.add_argument("--out", type=Path, default=ROOT / "assets")
    ap.add_argument("--sample", action="store_true", help="activity: use fake data")
    args = ap.parse_args()

    if args.what == "activity":
        weeks = sample_calendar() if args.sample else fetch_calendar(os.environ["GITHUB_TOKEN"])
        for theme, p in PALETTES.items():
            write(args.out, f"activity-{theme}.svg", draw_activity(p, weeks))
        return

    for theme, p in PALETTES.items():
        write(args.out, f"header-{theme}.svg", draw_header(p))
        for proj in PROJECTS:
            write(args.out, f"cards/{proj['id']}-{theme}.svg", draw_card(p, proj))
        for i, (sid, title, note) in enumerate(SECTIONS, 1):
            write(args.out, f"sections/{sid}-{theme}.svg", draw_section(p, i, title, note()))
        write(args.out, f"stack-{theme}.svg", draw_stack(p))


if __name__ == "__main__":
    main()
