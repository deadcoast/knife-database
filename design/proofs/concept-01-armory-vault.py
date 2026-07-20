"""Proof sheet: three rendered studies. Judged cold, no narration.

Study 01 — blade drawn at braille dot resolution (2x4 dots per cell)
Study 02 — data-driven dimensioning pulled from the live database record
Study 03 — machined panel & metal palette treatment

Run:  python proof_sheet.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from rich.console import Console, Group
from rich.text import Text

console = Console()

# ----------------------------------------------------------------- braille canvas

BIT = {(0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08,
       (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80}


class Canvas:
    """Dot canvas rendered as braille cells; 2x4 dots per terminal cell."""

    def __init__(self, width_dots: int, height_dots: int) -> None:
        self.w = width_dots
        self.h = height_dots
        self.dots: set[tuple[int, int]] = set()

    def set(self, x: int, y: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.dots.add((x, y))

    def unset(self, x: int, y: int) -> None:
        self.dots.discard((x, y))

    def render(self, color_at) -> Text:
        text = Text()
        for cy in range(self.h // 4):
            for cx in range(self.w // 2):
                code = 0x2800
                for dx in range(2):
                    for dy in range(4):
                        if (cx * 2 + dx, cy * 4 + dy) in self.dots:
                            code |= BIT[(dx, dy)]
                if code == 0x2800:
                    text.append(" ")
                else:
                    text.append(chr(code), style=color_at(cx, cy))
            text.append("\n")
        return text


# ----------------------------------------------------------------- steel palette

STEEL_RAMP = ["#31363c", "#3a4046", "#454c53", "#525a62", "#626b74",
              "#758089", "#8b96a0", "#a5b0ba", "#c2cdd6", "#dde6ee"]


def steel(cx: int, cy: int, rows: int, cols: int) -> str:
    """Vertical ramp dark spine -> bright edge, slight brightening toward tip."""
    row_t = cy / max(rows - 1, 1)
    col_t = cx / max(cols - 1, 1)
    idx = min(len(STEEL_RAMP) - 1, int(row_t * (len(STEEL_RAMP) - 1) + col_t * 1.5))
    return STEEL_RAMP[idx]


# ----------------------------------------------------------------- study 01: blade

def draw_blade() -> Canvas:
    """Drop-point folder blade, side profile, opening-hole; drawn from curves."""
    W, H = 120, 40
    c = Canvas(W, H)
    tip_x, tip_y = 116, 16
    spine_y, edge_y = 6, 30
    drop_start, belly_start = 58, 68

    def y_top(x: float) -> float:
        if x < drop_start:
            return spine_y
        t = (x - drop_start) / (tip_x - drop_start)
        return spine_y + (tip_y - spine_y) * (t ** 1.6)

    def y_bot(x: float) -> float:
        if x < belly_start:
            return edge_y
        t = (x - belly_start) / (tip_x - belly_start)
        return edge_y - (edge_y - tip_y) * (t ** 2.3)

    for x in range(0, tip_x + 1):
        top, bot = y_top(x), y_bot(x)
        for y in range(int(top), int(bot) + 1):
            c.set(x, y)

    # opening hole (folder signature)
    hx, hy, r = 20, 14, 5.4
    for x in range(int(hx - r) - 1, int(hx + r) + 2):
        for y in range(int(hy - r) - 1, int(hy + r) + 2):
            if math.hypot(x - hx, y - hy) <= r:
                c.unset(x, y)

    # plunge line: clean one-dot seam where the grind begins
    px = 34
    for y in range(int(y_top(px)) + 4, int(y_bot(px)) - 2):
        c.unset(px, y)
    return c


# ----------------------------------------------------------------- study 02: dims

DB_PATH = Path(r"C:\Users\ryanf\github\_new\knife-database\knivves\data\knives.json")


def load_record() -> dict:
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    for k in db["knives"]:
        if k["id"] == "spyderco-manix-2-xl-cru-wear-micarta-brown-c95mpcw2":
            return k
    raise SystemExit("record not found")


DIM = "#5c6670"
DIM_TEXT = "#8b96a0"
ACCENT = "#d7a455"


def dimension_layer(rec: dict, blade_cells: int) -> Group:
    mech = rec["mechanism"]
    length_label = f" {mech['blade_length']} "
    pad = blade_cells - len(length_label) - 2
    left = pad // 2
    right = pad - left
    dim_line = Text()
    dim_line.append("├" + "─" * left, style=DIM)
    dim_line.append(length_label, style=DIM_TEXT)
    dim_line.append("─" * right + "┤", style=DIM)

    price = rec["canadian_online_retailers"][0]["listed_price_cad"]
    callout = Text()
    callout.append("      └─ ", style=DIM)
    callout.append(f"{mech['blade_steel']}", style=ACCENT)
    callout.append(f"  ·  {mech['lock_type']}", style=DIM_TEXT)
    callout.append(f"  ·  ${price:,.2f} CAD", style=DIM_TEXT)
    return Group(dim_line, callout)


# ----------------------------------------------------------------- study 03: panel

EDGE = "#6b7680"
FACE = "#3a4046"
LABEL = "#8b96a0"
VALUE = "#dde6ee"


def title_block(rec: dict) -> Text:
    fields = [
        ("PLATE", "C95MPCW2"),
        ("MAKER", rec["brand"].upper()),
        ("MODEL", "MANIX 2 XL"),
        ("CLASS", (rec["user_classification"] or "UNREVIEWED").upper()),
    ]
    widths = [max(len(a), len(b)) + 2 for a, b in fields]
    top = "┏" + "┳".join("━" * w for w in widths) + "┓"
    mid = "┃" + "┃".join(f" {a:<{w - 2}} " for (a, _), w in zip(fields, widths)) + "┃"
    val = "┃" + "┃".join(f" {b:<{w - 2}} " for (_, b), w in zip(fields, widths)) + "┃"
    bot = "┗" + "┻".join("━" * w for w in widths) + "┛"
    t = Text()
    t.append(top + "\n", style=EDGE)
    t.append_text(Text(mid + "\n", style=LABEL))
    t.append_text(Text(val + "\n", style=VALUE))
    t.append(bot, style=EDGE)
    return t


def metal_swatch() -> Text:
    t = Text()
    t.append("MILLED RAMP   ", style=LABEL)
    for hexcode in STEEL_RAMP:
        t.append("██", style=hexcode)
    t.append("\n")
    t.append("BEVEL         ", style=LABEL)
    t.append("▛" + "▀" * 18 + "▜", style="#a5b0ba")
    t.append("\n")
    t.append("              ", style=LABEL)
    t.append("▙" + "▄" * 18 + "▟", style="#454c53")
    return t


# ----------------------------------------------------------------- sheet

def main() -> None:
    rec = load_record()
    blade = draw_blade()
    rows, cols = blade.h // 4, blade.w // 2

    console.print()
    console.print(Text("STUDY 01 — BLADE, BRAILLE RESOLUTION", style="bold #8b96a0"))
    console.print()
    console.print(blade.render(lambda cx, cy: steel(cx, cy, rows, cols)))

    console.print(Text("STUDY 02 — DIMENSIONING FROM LIVE RECORD", style="bold #8b96a0"))
    console.print()
    console.print(dimension_layer(rec, cols))
    console.print()

    console.print(Text("STUDY 03 — MACHINED PANEL / PALETTE", style="bold #8b96a0"))
    console.print()
    console.print(title_block(rec))
    console.print()
    console.print(metal_swatch())
    console.print()


if __name__ == "__main__":
    main()
