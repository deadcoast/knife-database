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
        background: $surface;
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
        return Strip(segments).adjust_cell_length(width, Style())


class SplitBand(Widget):
    """One machined band split into labeled segments — each segment's
    width is its share of the whole, its count stamped into the fill.
    The collection's classification split, read at a glance."""

    DEFAULT_CSS = """
    SplitBand {
        background: $surface;
        height: 2;
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._segments: list[tuple[str, int, str]] = []  # label, count, color

    def set_segments(self, segments: list[tuple[str, int, str]]) -> None:
        self._segments = [s for s in segments]
        self.refresh()

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        total = sum(count for _, count, _ in self._segments)
        if width <= 0 or not total:
            return Strip([]).adjust_cell_length(max(width, 0), Style())
        spans: list[tuple[str, int, str]] = []
        used = 0
        for i, (label, count, color) in enumerate(self._segments):
            span = round(count / total * width) if i < len(self._segments) - 1 else width - used
            span = max(span, 1) if count else 0
            spans.append((label, span, color))
            used += span
        segments = []
        if y == 0:
            for label, span, color in spans:
                if not span:
                    continue
                mark = f" {label}"[:span]
                mark = mark + " " * (span - len(mark))
                segments.append(Segment(mark, Style(color=laws.BG, bgcolor=color, bold=True)))
        else:
            for label, span, color in spans:
                if not span:
                    continue
                count = next(c for lab, c, col in self._segments if lab == label)
                mark = f" {count}"[:span]
                mark = mark + " " * (span - len(mark))
                segments.append(Segment(mark, Style(color=color, bgcolor=laws.SURFACE_LOW)))
        return Strip(segments).adjust_cell_length(width, Style())


class MeterBar(Widget):
    """A machined meter row: engraved label on the left, a gradient fill
    riding a recessed channel, the reading stamped bright on the right.
    One fact per meter — a bank of these reads as an instrument panel,
    not a list."""

    DEFAULT_CSS = """
    MeterBar {
        background: $surface;
        height: 1;
        margin-bottom: 1;
    }
    """

    LABEL_W = 11

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._label = label.upper()
        self._fraction = 0.0
        self._reading = ""
        self._tone: str | None = None

    def set_meter(self, fraction: float, reading: str, tone: str | None = None) -> None:
        """Fill to ``fraction`` (0..1); ``tone`` overrides the steel ramp."""
        self._fraction = max(0.0, min(fraction, 1.0))
        self._reading = reading
        self._tone = tone
        self.refresh()

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0 or y != 0:
            return Strip([]).adjust_cell_length(max(width, 0), Style())
        reading = f" {self._reading}"
        rail_w = max(width - self.LABEL_W - len(reading), 6)
        filled = int(self._fraction * rail_w)
        segments = [Segment(f"{self._label:<{self.LABEL_W}}"[: self.LABEL_W], Style(color=laws.STEEL_DIM))]
        for x in range(rail_w):
            if x < filled:
                tone = self._tone or _lerp(x / max(rail_w - 1, 1))
                segments.append(Segment(" ", Style(bgcolor=tone)))
            else:
                segments.append(Segment(" ", Style(bgcolor=laws.SURFACE_LOW)))
        segments.append(Segment(reading, Style(color=laws.STEEL_BRIGHT, bold=True)))
        return Strip(segments).adjust_cell_length(width, Style())


class PriceScale(Widget):
    """The collection's money on a machined scale: avg needle, $150 cut."""

    DEFAULT_CSS = """
    PriceScale {
        background: $surface;
        width: 100%;
        height: 4;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._prices: list[float] = []
        self._threshold = 150.0
        self._reveal_f: float | None = None

    def update_scale(self, prices: list[float], threshold: float) -> None:
        self._prices = sorted(prices)
        self._threshold = threshold
        self.refresh()

    # REVEAL — the scale draws itself left to right; the needle, the
    # labels, and the $150 cut land only when the drawing is done.

    def begin_reveal(self) -> None:
        self._reveal_f = 0.0
        self.refresh()

    def reveal_step(self, fraction: float) -> None:
        self._reveal_f = min(fraction, 1.0)
        self.refresh()

    def end_reveal(self) -> None:
        self._reveal_f = None
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
        drawing = self._reveal_f is not None
        drawn = width if not drawing else int(width * (self._reveal_f or 0.0))

        if drawing and y in (0, 3):
            # needle, labels, and the mark land when the drawing is done
            return Strip([]).adjust_cell_length(width, Style())

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
                    segments.append(Segment(" ", Style()))
            return Strip(segments).adjust_cell_length(width, Style())

        if y == 1:
            segments = []
            for x in range(width):
                if drawing and x >= drawn:
                    segments.append(Segment(" ", Style()))
                elif x == x_line and not drawing:
                    segments.append(Segment(" ", Style(bgcolor=laws.ACCENT)))
                elif x == x_avg and not drawing:
                    segments.append(Segment(" ", Style(bgcolor=laws.STEEL_BRIGHT)))
                else:
                    segments.append(Segment(" ", Style(bgcolor=_lerp(0.08 + 0.10 * (x / width)))))
            return Strip(segments).adjust_cell_length(width, Style())

        if y == 2:
            cells = [" "] * width
            for quarter in range(5):
                cells[self._x_of(self._ceiling() * quarter / 4, width)] = "╹"
            segments = []
            for x, ch in enumerate(cells):
                if drawing and x >= drawn:
                    segments.append(Segment(" ", Style()))
                elif x == x_line and ch == " " and not drawing:
                    segments.append(Segment("╹", Style(color=laws.ACCENT)))
                else:
                    segments.append(Segment(ch, Style(color=laws.STEEL_DIM)))
            return Strip(segments).adjust_cell_length(width, Style())

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
            return Strip(segments).adjust_cell_length(width, Style())

        return Strip([])
