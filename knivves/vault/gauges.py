"""Instruments — custom-rendered gauges for the Ledger.

Not styled text: drawn hardware. Each instrument renders its own cells
line by line, obeying the house palette and the honesty rule — every mark
on a scale is a real number from the database.

- PriceScale: a machined horizontal scale from $0 to the collection's
  ceiling; the average price rides it as a needle, and the $150 affordable
  rule is cut into the scale in accent.
- GradientBars: the price distribution as gradient-lit bars, brightening
  toward their tips, with eighth-block sub-cell precision at the ends.
"""
from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget

from . import laws

EIGHTHS = "▏▎▍▌▋▊▉█"
LABEL_W = 10

_DARK = (58, 64, 70)
_BRIGHT = (165, 176, 186)


def _lerp(t: float) -> str:
    r = int(_DARK[0] + (_BRIGHT[0] - _DARK[0]) * t)
    g = int(_DARK[1] + (_BRIGHT[1] - _DARK[1]) * t)
    b = int(_DARK[2] + (_BRIGHT[2] - _DARK[2]) * t)
    return f"rgb({r},{g},{b})"


class GradientBars(Widget):
    """The price distribution, drawn: each bar lit brighter toward its tip."""

    DEFAULT_CSS = """
    GradientBars {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._buckets: list[tuple[str, int]] = []

    def update_bars(self, buckets: list[tuple[str, int]]) -> None:
        self._buckets = buckets
        self.styles.height = len(buckets)
        self.refresh()

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if y >= len(self._buckets) or width <= LABEL_W + 6:
            return Strip([])
        label, count = self._buckets[y]
        top = max((c for _, c in self._buckets), default=1) or 1
        bar_span = width - LABEL_W - 5
        exact = (count / top) * bar_span
        full = int(exact)
        frac = exact - full

        segments = [Segment(f"{label:<{LABEL_W}}", Style(color=laws.STEEL_DIM))]
        for i in range(full):
            segments.append(Segment(" ", Style(bgcolor=_lerp(i / max(bar_span - 1, 1)))))
        used = full
        if frac >= 0.125 and full < bar_span:
            glyph = EIGHTHS[min(7, int(frac * 8))]
            segments.append(Segment(glyph, Style(color=_lerp(full / max(bar_span - 1, 1)))))
            used += 1
        segments.append(Segment(" " * (bar_span - used), Style()))
        biggest = count == top and count > 0
        segments.append(
            Segment(f" {count:>3}", Style(color=laws.ACCENT if biggest else laws.STEEL_DIM))
        )
        return Strip(segments).adjust_cell_length(width)


class PriceScale(Widget):
    """The collection's money on a machined scale: avg needle, $150 cut."""

    DEFAULT_CSS = """
    PriceScale {
        width: 100%;
        height: 4;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._prices: list[float] = []
        self._threshold = 150.0

    def update_scale(self, prices: list[float], threshold: float) -> None:
        self._prices = sorted(prices)
        self._threshold = threshold
        self.refresh()

    # ------------------------------------------------------------- helpers

    def _ceiling(self) -> float:
        top = max(self._prices, default=100.0)
        step = 250.0
        return max(step, ((top // step) + 1) * step)

    def _x_of(self, value: float, width: int) -> int:
        return min(width - 1, int((value / self._ceiling()) * (width - 1)))

    # -------------------------------------------------------------- render

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width < 20 or not self._prices:
            return Strip([])
        avg = sum(self._prices) / len(self._prices)
        x_avg = self._x_of(avg, width)
        x_line = self._x_of(self._threshold, width)

        if y == 0:
            label = f"avg ${avg:,.0f}"
            cells = [" "] * width
            cells[x_avg] = "▼"
            start = x_avg + 2 if x_avg + 2 + len(label) < width else x_avg - len(label) - 1
            row = "".join(cells)
            row = row[:start] + label + row[start + len(label):]
            segments = []
            for i, ch in enumerate(row[:width]):
                if ch == "▼":
                    segments.append(Segment(ch, Style(color=laws.STEEL_BRIGHT, bold=True)))
                elif ch != " ":
                    segments.append(Segment(ch, Style(color=laws.STEEL_MID)))
                else:
                    segments.append(Segment(" "))
            return Strip(segments).adjust_cell_length(width)

        if y == 1:
            segments = []
            for x in range(width):
                if x == x_line:
                    segments.append(Segment(" ", Style(bgcolor=laws.ACCENT)))
                elif x == x_avg:
                    segments.append(Segment(" ", Style(bgcolor=laws.STEEL_BRIGHT)))
                else:
                    segments.append(Segment(" ", Style(bgcolor=_lerp(0.08 + 0.10 * (x / width)))))
            return Strip(segments).adjust_cell_length(width)

        if y == 2:
            cells = [" "] * width
            for quarter in range(5):
                cells[self._x_of(self._ceiling() * quarter / 4, width)] = "╹"
            segments = []
            for x, ch in enumerate(cells):
                if x == x_line and ch == " ":
                    segments.append(Segment("╹", Style(color=laws.ACCENT)))
                else:
                    segments.append(Segment(ch, Style(color=laws.STEEL_DIM)))
            return Strip(segments).adjust_cell_length(width)

        if y == 3:
            left = "$0"
            right = f"${self._ceiling():,.0f}"
            mark = f"${self._threshold:,.0f}"
            cells = [" "] * width
            cells[:len(left)] = left
            cells[width - len(right):] = right
            mark_start = max(len(left) + 1, min(x_line - len(mark) // 2, width - len(right) - len(mark) - 1))
            cells[mark_start:mark_start + len(mark)] = mark
            segments = []
            x = 0
            row = "".join(cells)
            for x, ch in enumerate(row[:width]):
                in_mark = mark_start <= x < mark_start + len(mark)
                segments.append(Segment(ch, Style(color=laws.ACCENT if in_mark else laws.STEEL_DIM)))
            return Strip(segments).adjust_cell_length(width)

        return Strip([])
