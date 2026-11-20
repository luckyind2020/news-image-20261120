#!/usr/bin/env python3
"""The World Today - front page for Friday 20 November 2026.

Renders a newspaper front page at run time from the seven stories
listed below, using only the Python standard library. No network, no
files read, no randomness: the picture is fully deterministic.

Layout: a masthead, one lead story with a globe drawing, then six
stories in a two-column grid, each with its own small pictogram,
and a footer naming the day. Text is drawn with a 5x7 bitmap font
defined in this file; the PNG bytes are encoded by hand.
"""

import hashlib
import math
import os
import struct
import zlib

# ---------------------------------------------------------------- canvas

WIDTH = 1024
HEIGHT = 1024

PAPER = (246, 241, 227)
INK = (28, 28, 28)
RED = (172, 32, 32)
GREY = (112, 106, 92)

CANVAS = None  # built fresh by new_canvas() on every render


def new_canvas():
    px = bytearray(WIDTH * HEIGHT * 3)
    for i in range(0, len(px), 3):
        px[i] = PAPER[0]
        px[i + 1] = PAPER[1]
        px[i + 2] = PAPER[2]
    return px


def put(canvas, x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        o = (y * WIDTH + x) * 3
        canvas[o] = color[0]
        canvas[o + 1] = color[1]
        canvas[o + 2] = color[2]


def fill_rect(canvas, x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            put(canvas, xx, yy, color)


def hline(canvas, x0, x1, y, color, thick=1):
    for t in range(thick):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            put(canvas, x, y + t, color)


def vline(canvas, x, y0, y1, color, thick=1):
    for t in range(thick):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            put(canvas, x + t, y, color)


def segment(canvas, x0, y0, x1, y1, color, thick=1):
    """Bresenham line, with an optional square brush."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for a in range(thick):
            for b in range(thick):
                put(canvas, x + a - thick // 2, y + b - thick // 2, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def ring(canvas, cx, cy, r, color, thick=2):
    steps = max(24, int(2 * math.pi * r))
    for i in range(steps + 1):
        a = 2 * math.pi * i / steps
        put(canvas, cx + int(round(r * math.cos(a))),
            cy + int(round(r * math.sin(a))), color)
        if thick > 1:
            put(canvas, cx + int(round((r - 1) * math.cos(a))),
                cy + int(round((r - 1) * math.sin(a))), color)


def disc(canvas, cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                put(canvas, xx, yy, color)


def polyline(canvas, points, color, thick=1):
    for i in range(len(points) - 1):
        segment(canvas, points[i][0], points[i][1],
                points[i + 1][0], points[i + 1][1], color, thick)


# ------------------------------------------------------------------- font
# 5x7 bitmap font. Each glyph is seven rows of five bits, written as
# strings of 0 and 1, left to right, top to bottom.

GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    ".MID": ("00000", "00000", "00000", "01100", "01100", "00000", "00000"),
}

ADVANCE = 6  # glyph width 5 plus one pixel of tracking


def text_width(text, scale):
    return len(text) * ADVANCE * scale - scale


def draw_glyph(canvas, x, y, char, scale, color):
    rows = GLYPHS.get(char, GLYPHS["?"])
    for r, row in enumerate(rows):
        for c, bit in enumerate(row):
            if bit == "1":
                fill_rect(canvas, x + c * scale, y + r * scale,
                          scale, scale, color)


def draw_text(canvas, x, y, text, scale, color, align="l"):
    if align == "c":
        x -= text_width(text, scale) // 2
    elif align == "r":
        x -= text_width(text, scale)
    cx = x
    for ch in text:
        draw_glyph(canvas, cx, y, ch, scale, color)
        cx += ADVANCE * scale
    return cx


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines fitting max_width."""
    per_line = max(1, max_width // (ADVANCE * scale))
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) <= per_line:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_block(canvas, x, y, text, scale, color, max_width, leading=None):
    if leading is None:
        leading = 7 * scale + 2
    lines = wrap_text(text, scale, max_width)
    for i, line in enumerate(lines):
        draw_text(canvas, x, y + i * leading, line, scale, color)
    return y + len(lines) * leading


# ----------------------------------------------------------------- stories

# Seven stories, all reported on Friday 20 November 2026.
# Sources: Reuters / Times of India (Trump); The Hindu (Akvan);
# el-fondo / TechFlow / PropTraderz (markets); Mezha (GTA 6);
# Times of India / Jagran Josh (cricket); BBC (Europe talks);
# Studmentor school-assembly roundup (Seoul court).

LEAD = {
    "kicker": "WORLD - WASHINGTON",
    "headline": "TRUMP PUTS IRAN WAR DECISION OFF TO 2027",
    "body": "THE PRESIDENT SAYS THERE IS NO RUSH ON A DECISION OVER "
            "IRAN, AND THAT HE WILL SEE WHAT HAPPENS AFTER JANUARY 1, "
            "COOLING TALK OF IMMINENT ACTION AFTER DAYS OF STRIKES "
            "AROUND THE STRAIT OF HORMUZ.",
    "icon": "globe",
}

STORIES = [
    {
        "kicker": "ASIA - WEATHER",
        "headline": "300,000 FLEE AS CYCLONE AKVAN NEARS ODISHA",
        "body": "AUTHORITIES EVACUATE COASTAL DISTRICTS AND DEPLOY 423 "
                "RESCUE TEAMS AS THE STORM NEARS THE COAST.",
        "icon": "cyclone",
    },
    {
        "kicker": "MARKETS",
        "headline": "GOLD SLIDES BELOW $3,700 AS STOCKS AND BITCOIN FALL",
        "body": "SPOT GOLD BREAKS BELOW $3,700, ITS LOWEST SINCE "
                "SEPTEMBER 2025. BITCOIN SLIPS UNDER $64,500.",
        "icon": "gold",
    },
    {
        "kicker": "CULTURE - GAMES",
        "headline": "GTA 6 SALES PASS THE ODYSSEY'S $1.80BN GLOBAL RUN",
        "body": "ROCKSTAR'S SEQUEL OVERTAKES THE FILM'S WORLDWIDE GROSS "
                "WITHIN A DAY OF LAUNCH, AFTER 13 YEARS OF WAITING.",
        "icon": "controller",
    },
    {
        "kicker": "SPORT - CRICKET",
        "headline": "NICHOLLS 113 NOT OUT AS NZ BAT INDIA ON DAY ONE",
        "body": "HENRY NICHOLLS SCORES AN UNBEATEN CENTURY AT THE BASIN "
                "RESERVE AS NEW ZEALAND CLOSE DAY ONE ON 243 FOR FIVE.",
        "icon": "cricket",
    },
    {
        "kicker": "EUROPE - DIPLOMACY",
        "headline": "EUROPE READY FOR TALKS WITH RUSSIA TO END UKRAINE WAR",
        "body": "EUROPEAN LEADERS SAY THEY ARE PREPARED TO NEGOTIATE AN "
                "END TO THE WAR AS DIPLOMACY PICKS UP PACE.",
        "icon": "stars",
    },
    {
        "kicker": "ASIA - SEOUL",
        "headline": "S. KOREA COURT CLEARS EX-PM HAN",
        "body": "THE SUPREME COURT OVERTURNS HIS CONVICTION IN A CASE "
                "LINKED TO THE 2024 MARTIAL LAW DECLARATION.",
        "icon": "court",
    },
]

# ------------------------------------------------------------------ icons

def icon_globe(canvas, cx, cy, r):
    ring(canvas, cx, cy, r, INK, 2)
    segment(canvas, cx - r, cy, cx + r, cy, INK, 2)
    segment(canvas, cx, cy - r, cx, cy + r, INK, 2)
    pts = []
    for i in range(41):
        a = math.pi * i / 40
        pts.append((cx + int(round(r * 0.55 * math.sin(a))),
                    cy - r + int(round(2 * r * i / 40))))
    polyline(canvas, pts, INK, 1)
    pts = []
    for i in range(41):
        a = math.pi * i / 40
        pts.append((cx - int(round(r * 0.55 * math.sin(a))),
                    cy - r + int(round(2 * r * i / 40))))
    polyline(canvas, pts, INK, 1)
    disc(canvas, cx, cy, 3, RED)


def icon_cyclone(canvas, cx, cy, r):
    pts = []
    steps = 90
    for i in range(steps + 1):
        t = 4.5 * math.pi * i / steps
        rr = r * i / steps
        pts.append((cx + int(round(rr * math.cos(t))),
                    cy + int(round(rr * math.sin(t)))))
    polyline(canvas, pts, INK, 2)
    disc(canvas, cx, cy, 5, RED)
    for dx in (-26, 0, 26):
        segment(canvas, cx + dx, cy + r + 8, cx + dx - 6, cy + r + 22,
                GREY, 2)


def icon_gold(canvas, cx, cy, r):
    top = cy - 16
    bot = cy + 20
    polyline(canvas, [(cx - 40, bot), (cx - 30, top), (cx + 30, top),
                      (cx + 40, bot), (cx - 40, bot)], INK, 2)
    segment(canvas, cx - 34, bot - 10, cx + 34, bot - 10, INK, 1)
    draw_text(canvas, cx, top + 8, "$", 3, RED, align="c")
    segment(canvas, cx + 52, cy - 34, cx + 52, cy + 26, RED, 3)
    segment(canvas, cx + 52, cy + 26, cx + 42, cy + 14, RED, 3)
    segment(canvas, cx + 52, cy + 26, cx + 62, cy + 14, RED, 3)


def icon_controller(canvas, cx, cy, r):
    hline(canvas, cx - 44, cx + 44, cy - 20, INK, 2)
    hline(canvas, cx - 44, cx + 44, cy + 20, INK, 2)
    segment(canvas, cx - 44, cy - 20, cx - 44, cy + 20, INK, 2)
    segment(canvas, cx + 44, cy - 20, cx + 44, cy + 20, INK, 2)
    segment(canvas, cx - 30, cy - 6, cx - 30, cy + 6, INK, 3)
    segment(canvas, cx - 36, cy, cx - 24, cy, INK, 3)
    disc(canvas, cx + 8, cy - 6, 5, INK)
    disc(canvas, cx + 26, cy + 4, 4, RED)
    disc(canvas, cx + 36, cy - 6, 4, RED)


def icon_cricket(canvas, cx, cy, r):
    for dx in (-16, 0, 16):
        vline(canvas, cx + dx, cy - 26, cy + 18, INK, 3)
    hline(canvas, cx - 20, cx + 20, cy - 30, INK, 3)
    segment(canvas, cx - 34, cy + 30, cx - 6, cy - 34, INK, 5)
    disc(canvas, cx + 26, cy + 22, 8, RED)


def icon_stars(canvas, cx, cy, r):
    for i in range(12):
        a = 2 * math.pi * i / 12 - math.pi / 2
        disc(canvas, cx + int(round(38 * math.cos(a))),
             cy + int(round(38 * math.sin(a))), 4, INK)
    segment(canvas, cx - 26, cy + 26, cx - 6, cy + 12, INK, 2)
    segment(canvas, cx + 26, cy + 26, cx + 6, cy + 12, INK, 2)
    fill_rect(canvas, cx - 24, cy - 22, 48, 22, INK)
    fill_rect(canvas, cx - 21, cy - 19, 42, 16, PAPER)
    draw_text(canvas, cx, cy - 17, "TALK", 2, INK, align="c")


def icon_court(canvas, cx, cy, r):
    segment(canvas, cx - 40, cy - 18, cx, cy - 40, INK, 2)
    segment(canvas, cx, cy - 40, cx + 40, cy - 18, INK, 2)
    hline(canvas, cx - 44, cx + 44, cy - 18, INK, 3)
    for dx in (-28, 0, 28):
        vline(canvas, cx + dx, cy - 14, cy + 22, INK, 4)
    hline(canvas, cx - 44, cx + 44, cy + 26, INK, 3)
    hline(canvas, cx - 38, cx + 38, cy + 32, INK, 2)


ICONS = {
    "globe": icon_globe,
    "cyclone": icon_cyclone,
    "gold": icon_gold,
    "controller": icon_controller,
    "cricket": icon_cricket,
    "stars": icon_stars,
    "court": icon_court,
}

# ----------------------------------------------------------------- layout

MARGIN = 36
CONTENT_W = WIDTH - 2 * MARGIN


def draw_masthead(canvas):
    y = 30
    draw_text(canvas, WIDTH // 2, y, "THE WORLD TODAY", 6, INK, align="c")
    y += 56
    hline(canvas, MARGIN, WIDTH - MARGIN, y, INK, 2)
    y += 12
    draw_text(canvas, WIDTH // 2, y, "FRIDAY, 20 NOVEMBER 2026", 2, RED,
              align="c")
    y += 24
    draw_text(canvas, WIDTH // 2, y, "SEVEN STORIES FROM ONE DAY OF "
              "WORLD NEWS", 2, GREY, align="c")
    y += 26
    hline(canvas, MARGIN, WIDTH - MARGIN, y, INK, 3)
    hline(canvas, MARGIN, WIDTH - MARGIN, y + 5, INK, 1)
    return y + 14


def draw_lead(canvas, y):
    box_h = 232
    draw_text(canvas, MARGIN, y + 8, LEAD["kicker"], 2, RED)
    head_lines = wrap_text(LEAD["headline"], 4, 600)
    hy = y + 34
    for line in head_lines:
        draw_text(canvas, MARGIN, hy, line, 4, INK)
        hy += 32
    by = hy + 10
    draw_block(canvas, MARGIN, by, LEAD["body"], 2, INK, 600)
    icon_cx = WIDTH - MARGIN - 150
    icon_cy = y + box_h // 2 + 6
    ICONS[LEAD["icon"]](canvas, icon_cx, icon_cy, 78)
    return y + box_h


def draw_cell(canvas, x, y, w, h, story):
    icon_w = 116
    tx = x + icon_w + 12
    tw = w - icon_w - 12
    ICONS[story["icon"]](canvas, x + icon_w // 2, y + 62, 44)
    draw_text(canvas, tx, y + 6, story["kicker"], 2, RED)
    head_lines = wrap_text(story["headline"], 3, tw)
    hy = y + 30
    for line in head_lines:
        draw_text(canvas, tx, hy, line, 3, INK)
        hy += 23
    draw_block(canvas, tx, hy + 6, story["body"], 2, INK, tw)
    hline(canvas, x, x + w, y + h - 2, GREY, 1)


def draw_footer(canvas, y):
    hline(canvas, MARGIN, WIDTH - MARGIN, y, INK, 2)
    draw_text(canvas, WIDTH // 2, y + 12,
              "FRIDAY 20 NOVEMBER 2026 - SEVEN STORIES, ONE DAY", 2,
              GREY, align="c")


def render():
    canvas = new_canvas()
    y = draw_masthead(canvas)
    y = draw_lead(canvas, y)
    y += 12
    hline(canvas, MARGIN, WIDTH - MARGIN, y, INK, 2)
    y += 14
    cell_w = (CONTENT_W - 24) // 2
    cell_h = 168
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        cx = MARGIN + col * (cell_w + 24)
        cy = y + row * (cell_h + 12)
        draw_cell(canvas, cx, cy, cell_w, cell_h, story)
    foot_y = y + 3 * cell_h + 2 * 12 + 6
    draw_footer(canvas, foot_y)
    return canvas


# -------------------------------------------------------------- png encode

def png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    raw = bytearray()
    for yy in range(HEIGHT):
        raw.append(0)
        raw += canvas[yy * WIDTH * 3:(yy + 1) * WIDTH * 3]
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += png_chunk(b"IEND", b"")
    return png


# -------------------------------------------------------------------- main

def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    digest = hashlib.sha256(data).hexdigest()
    print("wrote %s (%d bytes) sha256=%s" % (path, len(data), digest))


if __name__ == "__main__":
    main()
