#!/usr/bin/env python3
"""Draws assets/header-dark.svg and assets/header-light.svg.

Every glyph is outlined to a path. GitHub serves README images through a proxy
that cannot load web fonts, so live <text> would fall back to whatever the
viewer has installed. Outlined, the header looks the same on every machine.

    pip install fonttools uharfbuzz brotli
    python scripts/build_header.py

Fonts (all OFL) are fetched from google/fonts on first run and cached.
"""

import os
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

# (local name, upstream path, wght to instance at or None for static fonts)
FONTS = {
    "serif":        ("InstrumentSerif-Regular.ttf", "instrumentserif/InstrumentSerif-Regular.ttf", None),
    "serif-italic": ("InstrumentSerif-Italic.ttf",  "instrumentserif/InstrumentSerif-Italic.ttf",  None),
    "mono":         ("FiraCode-Regular.ttf",        "firacode/FiraCode%5Bwght%5D.ttf",             400),
    "mono-medium":  ("FiraCode-Medium.ttf",         "firacode/FiraCode%5Bwght%5D.ttf",             500),
    "jp":           ("NotoSansJP-Regular.ttf",      "notosansjp/NotoSansJP%5Bwght%5D.ttf",         400),
    "jp-light":     ("NotoSansJP-Light.ttf",        "notosansjp/NotoSansJP%5Bwght%5D.ttf",         300),
}

W, H = 1200, 440
PAD = 64

PALETTES = {
    "dark": {
        "bg": "#0c0b09", "edge": "#2a2214", "glow": "#ffb000", "glow_op": "0.11",
        "dots": "#ffb000", "dots_op": "0.16",
        "name": "#ffb000", "lede": "#d6ae6a", "meta": "#8c7448",
        "label": "#7d6537", "value": "#f1dcb3", "rule": "#2e2615",
        "tick": "#5a4723", "cursor": "#ffb000", "live": "#3ddc84", "jp": "#4a3b1f",
    },
    "light": {
        "bg": "#fbf7ee", "edge": "#e6dac0", "glow": "#ffb000", "glow_op": "0.12",
        "dots": "#a87400", "dots_op": "0.18",
        "name": "#1c1508", "lede": "#8a5a00", "meta": "#8f7c58",
        "label": "#9a865f", "value": "#2b2214", "rule": "#e7dbc0",
        "tick": "#cdb98f", "cursor": "#d99400", "live": "#1f9d55", "jp": "#dccba5",
    },
}


def fmt(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


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


def split_runs(text, primary, fallback):
    runs, cur, cur_face = [], "", None
    for ch in text:
        # Spaces always come from the primary face; CJK fonts carry narrower ones.
        f = primary if primary.covers(ch) else fallback
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
    primary, alt = face(key), face(fallback)
    features = features or {"kern": True, "liga": True, "calt": False}

    placed, cursor = [], 0.0
    for f, run in split_runs(text, primary, alt):
        s = size / f.upem * (jp_scale if f is alt else 1)
        buf = hb.Buffer()
        buf.add_str(run)
        buf.guess_segment_properties()
        hb.shape(f.hb, buf, features)
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            placed.append((f, f.order[info.codepoint], s, cursor + pos.x_offset * s, pos.y_offset * s))
            cursor += pos.x_advance * s + tracking
    width = cursor - tracking if placed else 0.0

    x0 = x - width if anchor == "end" else x
    d = "".join(outline(f, name, (s, 0, 0, -s, x0 + dx, y - dy)) for f, name, s, dx, dy in placed)
    return d, width


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


# --- content -----------------------------------------------------------------

HANDLE = "infinity_block"
WHERE = "JAPAN  ·  UTC+9"
NAME = "Evan Alferez"
LEDE = "I build the software Japanese businesses run on."
VERTICAL = "設計から運用まで"  # "from design to operation" — the line from evanserv.com

COLUMNS = [
    ("SHIPPING",      "帳場ラボ · Chouba Lab"),
    ("IN PRODUCTION", "Sabizu · Happy Island"),
    ("OPEN DATA",     "OpenJLPT"),
    ("SPEAKS",        "EN · 日本語 · CEB · TL"),
]


def build(theme):
    p = PALETTES[theme]
    out = []
    add = out.append

    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="title desc">')
    add('<title id="title">Evan Alferez</title>')
    add('<desc id="desc">Evan Alferez (infinity_block), full-stack engineer in Japan. '
        'Shipping Chouba Lab; in production: Sabizu and Happy Island; open data: OpenJLPT. '
        'Speaks English, Japanese, Cebuano and Tagalog.</desc>')
    add("<style>"
        ".cursor{animation:blink 1.1s steps(1) infinite}"
        ".ring{transform-box:fill-box;transform-origin:center;animation:ring 2.6s ease-out infinite}"
        "@keyframes blink{50%{opacity:0}}"
        "@keyframes ring{0%{transform:scale(1);opacity:.55}80%,100%{transform:scale(3.2);opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.cursor,.ring{animation:none}.ring{opacity:0}}"
        "</style>")
    add("<defs>")
    add(f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<circle cx="11" cy="11" r="1" fill="{p["dots"]}"/></pattern>')
    add(f'<radialGradient id="glow" cx="{W - 170}" cy="40" r="620" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{p["glow"]}" stop-opacity="{p["glow_op"]}"/>'
        f'<stop offset="1" stop-color="{p["glow"]}" stop-opacity="0"/></radialGradient>')
    add(f'<radialGradient id="fadeg" cx="{W - 150}" cy="60" r="560" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    add(f'<mask id="fade"><rect width="{W}" height="{H}" fill="url(#fadeg)"/></mask>')
    add(f'<clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    add("</defs>")

    add('<g clip-path="url(#card)">')
    add(f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>')
    add(f'<rect width="{W}" height="{H}" fill="url(#glow)"/>')
    add(f'<rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#fade)" opacity="{p["dots_op"]}"/>')

    # top row
    d, _ = set_line(HANDLE, PAD, 70, 14, "mono-medium", tracking=1.6)
    add(f'<path fill="{p["meta"]}" d="{d}"/>')
    d, w = set_line(WHERE, W - PAD, 70, 13, "mono", tracking=1.8, anchor="end")
    add(f'<path fill="{p["meta"]}" d="{d}"/>')
    dot_x = W - PAD - w - 18
    add(f'<circle class="ring" cx="{fmt(dot_x)}" cy="65.5" r="3.5" fill="{p["live"]}"/>')
    add(f'<circle cx="{fmt(dot_x)}" cy="65.5" r="3.5" fill="{p["live"]}"/>')

    # name + cursor
    d, w = set_line(NAME, PAD - 4, 212, 128, "serif", tracking=-0.5)
    add(f'<path fill="{p["name"]}" d="{d}"/>')
    add(f'<rect class="cursor" x="{fmt(PAD + w + 10)}" y="128" width="30" height="86" fill="{p["cursor"]}"/>')

    # lede
    d, _ = set_line(LEDE, PAD, 268, 34, "serif-italic", tracking=0.1)
    add(f'<path fill="{p["lede"]}" d="{d}"/>')

    # vertical Japanese, right edge
    d = set_vertical(VERTICAL, W - PAD - 12, 134, 19, "jp-light")
    add(f'<path fill="{p["jp"]}" d="{d}"/>')

    # rule with ticks, one per column
    rule_y = 326
    add(f'<path stroke="{p["rule"]}" stroke-width="1" d="M{PAD} {rule_y}H{W - PAD}"/>')
    col_w = (W - 2 * PAD) / len(COLUMNS)
    ticks = "".join(f"M{fmt(PAD + i * col_w)} {rule_y - 5}v10" for i in range(len(COLUMNS))) + f"M{W - PAD} {rule_y - 5}v10"
    add(f'<path stroke="{p["tick"]}" stroke-width="1" d="{ticks}"/>')

    for i, (label, value) in enumerate(COLUMNS):
        x = PAD + i * col_w
        d, _ = set_line(f"0{i + 1}  {label}", x, 362, 11.5, "mono-medium", tracking=2.2)
        add(f'<path fill="{p["label"]}" d="{d}"/>')
        d, _ = set_line(value, x, 394, 17, "mono", tracking=0.2)
        add(f'<path fill="{p["value"]}" d="{d}"/>')

    add("</g>")
    add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" stroke="{p["edge"]}"/>')
    add("</svg>")
    return "\n".join(out) + "\n"


def main():
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for theme in PALETTES:
        path = assets / f"header-{theme}.svg"
        path.write_text(build(theme), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
