"""Machined surfaces — drawn material, not styled boxes.

- BrushedSteel: a rendered metal skin. Deterministic grain (no randomness:
  the same surface every launch) with faint glints, drawn line by line.
  Used as the masthead's under-layer.
- Engraving: a station header cut into the surface — letterspaced caps
  over a machined rule, bright beneath the title, falling off dim.
"""
from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget

from . import laws

_BASE = (29, 33, 38)


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


class Engraving(Widget):
    """A header cut into the machine: letterspaced caps over a bright rule."""

    DEFAULT_CSS = """
    Engraving {
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
            ).adjust_cell_length(width)
        if y == 1:
            lit = min(len(self.spaced) + 1, width)
            segments = [
                Segment("╾" + "─" * max(lit - 1, 0), Style(color=laws.EDGE_BRIGHT)),
                Segment("─" * max(width - lit - 1, 0) + ("╼" if width > lit else ""), Style(color=laws.EDGE)),
            ]
            return Strip(segments).adjust_cell_length(width)
        return Strip([])
