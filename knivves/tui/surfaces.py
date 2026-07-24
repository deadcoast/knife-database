"""Machined surfaces — drawn material, not styled boxes.

- BrushedSteel: a rendered metal skin. Deterministic grain (no randomness:
  the same surface every launch) with faint glints, drawn line by line.
  Used as the masthead's under-layer.
- Engraving: a station header cut into the surface — letterspaced caps
  over a machined rule, bright beneath the title, falling off dim.
- Teletype: a surface that PRINTS its data — lines land at the house
  cadence with a block cursor riding the print head. It dramatizes
  arrival only; an interrupted print keeps exactly what landed.
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static

from . import laws

_BASE = (32, 37, 43)

# The stamp font — the brand cut into steel at nameplate size. Three rows
# tall, drawn from half-blocks; only the letters the building needs.
_STAMP_FONT: dict[str, tuple[str, str, str]] = {
    "K": ("█ ▄▀", "██▀ ", "█ ▀▄"),
    "N": ("█▚ █", "█ ▚█", "█  █"),
    "I": ("▀█▀", " █ ", "▄█▄"),
    "V": ("▌ ▐", "▐ ▌", " █ "),
    "E": ("█▀▀", "█▀ ", "█▄▄"),
    "S": ("▄▀▀", "▀▀▄", "▄▄▀"),
    " ": (" ", " ", " "),
}


def stamp_rows(text: str) -> tuple[str, str, str]:
    """``text`` rendered in the stamp font: three strings, one per row."""
    glyphs = [_STAMP_FONT.get(ch, _STAMP_FONT[" "]) for ch in text.upper()]
    return tuple(" ".join(g[row] for g in glyphs) for row in range(3))  # type: ignore[return-value]


def _grain(x: int, y: int) -> int:
    """Deterministic surface noise: sparse, subtle, stable per cell."""
    h = (x * 2654435761 + y * 40503) & 0xFF
    if h < 6:
        return 3
    if h > 250:
        return -2
    return 0


def grain_tone(x: int, y: int) -> str:
    """The brushed-steel background tone for a cell, as an rgb() string."""
    delta = _grain(x, y)
    return f"rgb({_BASE[0] + delta},{_BASE[1] + delta},{_BASE[2] + delta})"


class BrushedSteel(Widget):
    """A drawn steel skin; sits beneath content on its own layer."""

    DEFAULT_CSS = """
    BrushedSteel {
        width: 100%;
        height: 100%;
    }
    """

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        segments = []
        run_start = 0
        run_delta = _grain(0, y)
        for x in range(1, width + 1):
            delta = _grain(x, y) if x < width else None
            if delta != run_delta:
                tone = Style(bgcolor=f"rgb({_BASE[0] + run_delta},{_BASE[1] + run_delta},{_BASE[2] + run_delta})")
                segments.append(Segment(" " * (x - run_start), tone))
                run_start, run_delta = x, delta
        return Strip(segments, width)


class Teletype(Static):
    """A window that acts as a terminal: data prints line by line at the
    house cadence, a block cursor riding the print head. The cursor
    exists only while the machine prints. The surface never fakes
    latency — context already known is handed in as ``lead`` and lands
    instantly; only arriving lines are paced. Interrupting a print
    (worker cancelled) keeps exactly the lines that landed — honest
    truncation, cursor off.
    """

    CURSOR = "▮"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._printed = Text()
        self._printing = False

    @property
    def printing(self) -> bool:
        return self._printing

    @property
    def printed_lines(self) -> int:
        return self._printed.plain.count("\n")

    async def type_lines(
        self,
        lines: Iterable[Text],
        *,
        lead: Text | None = None,
        cadence: float | None = None,
    ) -> None:
        """Print ``lines`` one per beat. ``lead`` renders instantly."""
        pace = laws.TELETYPE_CADENCE if cadence is None else cadence
        self._printed = lead.copy() if lead is not None else Text()
        self._printing = True
        try:
            for line in lines:
                self._printed.append_text(line.copy())
                self._printed.append("\n")
                head = self._printed.copy()
                head.append(self.CURSOR, style=laws.ACCENT)
                self.update(head)
                await asyncio.sleep(pace)
        finally:
            # however the print ends — completed or interrupted — the
            # cursor lifts and only what actually landed remains
            self._printing = False
            self.update(self._printed)

    def clear(self) -> None:
        self._printed = Text()
        self._printing = False
        self.update("")


class TransitRail(Widget):
    """The line a record rides between stations, drawn: a machined rail
    across its tray with a stop post under each station above, labeled.
    The traveling plate covers the stop it currently sits at — the rail
    itself says where the work is."""

    DEFAULT_CSS = """
    TransitRail {
        background: $surface-low;
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, stops: list[tuple[str, str]], texture: str = "rollers", **kwargs) -> None:
        super().__init__(**kwargs)
        self._stops = stops  # (station widget id, engraved label)
        self._texture = texture  # "rollers" (conveyor) | "grid" (desk blotter)

    def _stop_xs(self) -> list[tuple[int, str]]:
        out: list[tuple[int, str]] = []
        for sid, label in self._stops:
            try:
                region = self.screen.query_one(f"#{sid}").region
            except Exception:
                continue
            out.append((max(region.x - self.region.x + 2, 0), label))
        return out

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        stops = self._stop_xs()
        if y == 0:
            cells = [("─", Style(color=laws.EDGE_BRIGHT))] * width
            cells[0] = ("╾", Style(color=laws.STEEL_MID))
            cells[-1] = ("╼", Style(color=laws.STEEL_MID))
            for x, _label in stops:
                if 0 <= x < width:
                    cells[x] = ("╥", Style(color=laws.STEEL_MID, bold=True))
            return Strip([Segment(ch, style) for ch, style in cells], width)
        if y == 1:
            cells = [(" ", Style())] * width
            for x, label in stops:
                for i, ch in enumerate(label):
                    if 0 <= x + i < width:
                        cells[x + i] = (ch, Style(color=laws.STEEL_DIM))
            return Strip([Segment(ch, style) for ch, style in cells], width)
        if y >= 2 and y % 2 == 0:
            if self._texture == "grid":
                # the desk blotter — a dot lattice, the unknowns map's
                # own material carried down to the bed
                cells = []
                for x in range(width):
                    ch = "·" if x % 3 == 1 else " "
                    cells.append(Segment(ch, Style(color=laws.EDGE)))
                return Strip(cells, width)
            # the ribbed conveyor bed the plate rides on
            return Strip([Segment("─" * width, Style(color=laws.EDGE))], width)
        return Strip([]).adjust_cell_length(width, Style())


class Engraving(Widget):
    """A header cut into the machine: letterspaced caps over a bright rule."""

    DEFAULT_CSS = """
    Engraving {
        background: $surface;
        width: 100%;
        height: 2;
        margin-bottom: 1;
    }
    """

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title.upper()

    @property
    def spaced(self) -> str:
        return " ".join(self._title)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        if y == 0:
            text = self.spaced[:width]
            return Strip(
                [Segment(text, Style(color=laws.STEEL_MID, bold=True))]
            ).adjust_cell_length(width, Style())
        if y == 1:
            lit = min(len(self.spaced) + 1, width)
            segments = [
                Segment("╾" + "─" * max(lit - 1, 0), Style(color=laws.EDGE_BRIGHT)),
                Segment("─" * max(width - lit - 1, 0) + ("╼" if width > lit else ""), Style(color=laws.EDGE)),
            ]
            return Strip(segments).adjust_cell_length(width, Style())
        return Strip([])
