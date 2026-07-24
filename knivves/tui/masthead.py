"""The Masthead — the building's constant frame, machined.

A single custom-rendered widget: brushed-steel grain drawn cell by cell
with the chrome text stamped into it — brand, room, room-state context,
live vault statistics. No child widgets, no layers: the masthead owns
every cell it paints, the same discipline as the vault door's leaves.
"""
from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget

from ..models import KnifeView
from . import laws
from .surfaces import grain_tone

Run = tuple[str, str, bool]  # text, color, bold


class Masthead(Widget):
    DEFAULT_CSS = """
    Masthead {
        height: 3;
        border-bottom: heavy $edge;
    }
    """

    def __init__(self, room: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._room = room
        self._room_context = ""
        self._stats: list[Run] = []

    # ------------------------------------------------------------------ api

    @property
    def context(self) -> str:
        return self._room_context

    def set_context(self, text: str) -> None:
        """Room-state readout beside the room name (sort, line state…)."""
        self._room_context = text
        self.refresh()

    def update_stats(self, knives: list[KnifeView]) -> None:
        prices = [k.price for k in knives if k.price is not None]
        avg = sum(prices) / len(prices) if prices else 0
        approved = sum(1 for k in knives if k.classification == "approved")
        fresh = sum(1 for k in knives if k.is_new)
        dot: Run = ("  ·  ", laws.STEEL_DIM, False)
        self._stats = [
            (f"{len(knives)} knives", laws.STEEL_MID, False),
            dot,
            (f"{approved} approved", laws.CLASS_COLORS["approved"], False),
            dot,
            (f"avg ${avg:,.0f} CAD", laws.STEEL_MID, False),
        ]
        if fresh:
            self._stats.extend([dot, (f"{fresh} new", laws.FRESH, True)])
        self.refresh()

    # --------------------------------------------------------------- render

    def _stamp(self, cells: list[tuple[str, Style]], x: int, run: Run, y: int) -> int:
        text, color, bold = run
        for i, ch in enumerate(text):
            pos = x + i
            if 0 <= pos < len(cells):
                _, base = cells[pos]
                cells[pos] = (ch, Style(color=color, bgcolor=base.bgcolor, bold=bold))
        return x + len(text)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        cells: list[tuple[str, Style]] = [
            (" ", Style(bgcolor=grain_tone(x, y))) for x in range(width)
        ]
        if y == 0:
            x = 2
            x = self._stamp(cells, x, ("KNIVVES", laws.STEEL_BRIGHT, True), y)
            x = self._stamp(cells, x + 2, (f"· {self._room}", laws.ACCENT, False), y)
            if self._room_context:
                self._stamp(cells, x + 2, (self._room_context, laws.STEEL_DIM, False), y)
            stats_len = sum(len(text) for text, _, _ in self._stats)
            sx = max(x + 4, width - 2 - stats_len)
            for run in self._stats:
                sx = self._stamp(cells, sx, run, y)
        return Strip([Segment(ch, style) for ch, style in cells], width)
