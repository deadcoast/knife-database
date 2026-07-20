"""Concept 02 — TRUE SCALE. The terminal as a measuring bench.

Nothing is drawn that the database does not know. Every blade is rendered at
identical physical scale (1 braille dot = 1 mm) against a real millimeter
ruler, from live records. Accuracy is the aesthetic; no invented shapes.

Study 04 — the Scale Wall: blades at true relative scale, live data
Study 05 — touchmarks: a deterministic maker's mark generated from each record

Run:  python design/proofs/concept-02-true-scale.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from rich.console import Console
from rich.text import Text

console = Console()
DB_PATH = Path(__file__).resolve().parents[2] / "knivves" / "data" / "knives.json"

# 1 braille dot = 1 mm horizontally; one cell = 2 dots = 2 mm
MM_PER_DOT = 1.0
BIT = {(0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08,
       (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80}

STEEL_RAMP = ["#3a4046", "#454c53", "#525a62", "#626b74", "#758089",
              "#8b96a0", "#a5b0ba", "#c2cdd6", "#dde6ee"]
DIM = "#5c6670"
LABEL = "#8b96a0"
VALUE = "#dde6ee"
ACCENT = "#d7a455"

IN_TO_MM = 25.4
LEN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:in|\")|(\d+(?:\.\d+)?)\s*mm", re.I)


def blade_mm(record: dict) -> float | None:
    raw = (record.get("mechanism") or {}).get("blade_length") or ""
    mm_match = re.search(r"(\d+(?:\.\d+)?)\s*mm", raw, re.I)
    if mm_match:
        return float(mm_match.group(1))
    in_match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if in_match:
        return float(in_match.group(1)) * IN_TO_MM
    return None


def price_of(record: dict) -> float | None:
    for r in record.get("canadian_online_retailers") or []:
        p = r.get("listed_price_cad")
        if isinstance(p, (int, float)):
            return p
    return None


def braille_row(dots_wide: int, taper_from: float, height_dots: int = 4) -> list[list[bool]]:
    """A schematic blade bar: exact length, tapering to a point after taper_from."""
    grid = [[False] * dots_wide for _ in range(height_dots)]
    for x in range(dots_wide):
        if x < taper_from * dots_wide:
            lo, hi = 0, height_dots
        else:
            t = (x - taper_from * dots_wide) / max(dots_wide - taper_from * dots_wide, 1)
            half = (height_dots / 2) * (1 - t)
            lo = int(height_dots / 2 - half)
            hi = int(height_dots / 2 + half) + 1
        for y in range(lo, min(hi, height_dots)):
            grid[y][x] = True
    return grid


def render_bar(grid: list[list[bool]], color_for_col) -> Text:
    height = len(grid)
    width = len(grid[0]) if grid else 0
    text = Text()
    for cy in range((height + 3) // 4):
        for cx in range((width + 1) // 2):
            code = 0x2800
            for dx in range(2):
                for dy in range(4):
                    x, y = cx * 2 + dx, cy * 4 + dy
                    if y < height and x < width and grid[y][x]:
                        code |= BIT[(dx, dy)]
            text.append(" " if code == 0x2800 else chr(code), style=color_for_col(cx))
    return text


def ruler(max_mm: int, label_col: int) -> Text:
    """Millimeter ruler: tick every 10 mm, number every 50 mm. 1 cell = 2 mm."""
    cells = max_mm // 2 + 1
    marks = [" "] * cells
    for mm in range(0, max_mm + 1, 10):
        marks[mm // 2] = "┸" if mm % 50 == 0 else "╵"
    line = Text(" " * label_col)
    line.append("".join(marks), style=DIM)
    numbers = [" "] * cells
    for mm in range(0, max_mm + 1, 50):
        for i, ch in enumerate(f"{mm}"):
            pos = mm // 2 + i
            if pos < cells:
                numbers[pos] = ch
    nline = Text(" " * label_col)
    nline.append("".join(numbers), style=DIM)
    nline.append("  mm", style=DIM)
    return Group_(line, nline)


def Group_(*items):
    from rich.console import Group
    return Group(*items)


def touchmark(record_id: str) -> list[str]:
    """Deterministic 4-cell-wide maker's mark from the record identity."""
    digest = hashlib.sha256(record_id.encode()).digest()
    rows = []
    for cy in range(2):
        row = ""
        cells = []
        for cx in range(4):
            code = 0x2800
            for dx in range(2):
                for dy in range(4):
                    bit_index = cy * 32 + cx * 8 + dx * 4 + dy
                    if digest[bit_index // 8] >> (bit_index % 8) & 1:
                        # mirror horizontally for symmetry: right half mirrors left
                        code |= BIT[(dx, dy)]
            cells.append(chr(code))
        # mirror: 4 cells -> 8 cells wide symmetric mark
        mirrored = cells + [chr(0x2800 + _mirror_bits(ord(c) - 0x2800)) for c in reversed(cells)]
        rows.append("".join(mirrored))
    return rows


def _mirror_bits(code: int) -> int:
    left = {0x01: 0x08, 0x02: 0x10, 0x04: 0x20, 0x40: 0x80}
    out = 0
    for a, b in left.items():
        if code & a:
            out |= b
        if code & b:
            out |= a
    return out


def main() -> None:
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    rows = []
    for k in db["knives"]:
        mm = blade_mm(k)
        if mm:
            rows.append((mm, k))
    rows.sort(key=lambda r: -r[0])
    # spread: longest, then every ~3rd for variety, cap 8
    picks = rows[:1] + rows[1::3]
    picks = picks[:8]

    label_col = 34
    max_mm = int(max(mm for mm, _ in picks) // 10 * 10 + 10)

    console.print()
    console.print(Text("STUDY 04 — THE SCALE WALL   ·   1 dot = 1 mm   ·   live records only", style=f"bold {LABEL}"))
    console.print()
    console.print(ruler(max_mm, label_col))
    console.print()
    for mm, k in picks:
        name = f"{k['brand']} {k['model']}"
        if len(name) > label_col - 4:
            name = name[: label_col - 5] + "…"
        price = price_of(k)
        steel_idx = min(len(STEEL_RAMP) - 1, int((mm / max_mm) * (len(STEEL_RAMP) - 1)))

        label = Text(f"{name:<{label_col - 2}}", style=VALUE)
        grid = braille_row(int(mm), taper_from=0.82)
        bar = render_bar(grid, lambda cx: STEEL_RAMP[min(len(STEEL_RAMP) - 1, 3 + cx // 18)])
        line = Text("  ")
        line.append_text(label)
        line.append_text(bar)
        line.append(f"  {mm:.0f} mm", style=DIM)
        if price is not None:
            line.append(f"  ·  ${price:,.2f}", style=LABEL)
        console.print(line)
        console.print()

    console.print(Text("STUDY 05 — TOUCHMARKS   ·   each record's identity as a maker's mark", style=f"bold {LABEL}"))
    console.print()
    sample = [k for _, k in picks[:6]]
    mark_rows = [touchmark(k["id"]) for k in sample]
    for line_idx in range(2):
        line = Text("  ")
        for marks in mark_rows:
            line.append(marks[line_idx], style=ACCENT)
            line.append("      ")
        console.print(line)
    names = Text("  ")
    for k in sample:
        names.append(f"{k['brand'][:12]:<14}", style=DIM)
    console.print(names)
    console.print()


if __name__ == "__main__":
    main()
