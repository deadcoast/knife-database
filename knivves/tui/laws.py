"""The house laws — design constants every page of the building obeys.

The application reads as one building because no page is allowed its own
vocabulary. Three laws, enforced here as the only source of truth:

1. One palette. Machined darks, steel text, classification colors, and a
   single amber accent. No page introduces a color. The palette is the
   registered ``knivves`` Theme — every stylesheet speaks it as
   ``$variables``; no ``.tcss`` may carry a raw color.
2. One field grammar. Every labeled value everywhere renders through
   ``field()`` — the plate, the gates, the masthead, the bench.
3. One motion law, in three tiers. Objects travel, they never teleport
   and never fade. REVEAL: once, on page open, the page's one hero
   instrument performs — through ``Reveal``. IDLE: after settle,
   ambient and long-cadence — felt more than seen. CUE: the machine
   answers the hand — hover/focus transitions declared in TCSS through
   ``$cue-duration``. Every travel moves through ``travel()`` with the
   same easing.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Iterable

from rich.text import Text
from textual.css.scalar import ScalarOffset
from textual.theme import Theme
from textual.widget import Widget

# -- law 1: the palette ------------------------------------------------------

BG = "#14171a"
SURFACE = "#1d2126"
SURFACE_LOW = "#171a1e"     # recessed machined tone — zebra rows
SURFACE_HIGH = "#262b31"    # raised machined tone — a surface under the hand
SURFACE_RAISED = "#2a3038"  # the seated cursor row
EDGE = "#31363c"
EDGE_BRIGHT = "#525a62"

STEEL_BRIGHT = "#dde6ee"
STEEL_BODY = "#c2cdd6"      # the body text everywhere — between bright and mid
STEEL_MID = "#8b96a0"
STEEL_DIM = "#5c6670"

ACCENT = "#d7a455"          # the only accent in the building
FRESH = "#5fd3bc"           # cold mint — the glint of a fresh edge; ★new wears it in every room
PASS = "#79b473"
FAIL = "#c05b4d"

CLASS_COLORS = {
    "approved": PASS,
    "rejected": FAIL,
    "unclassified": STEEL_DIM,
}

# -- law 2: the field grammar ------------------------------------------------

LABEL_WIDTH = 10


def field(label: str, value: str, value_style: str = STEEL_BRIGHT) -> Text:
    """One labeled value, in the grammar every page speaks."""
    text = Text()
    text.append(f"{label.upper():<{LABEL_WIDTH}}", style=STEEL_DIM)
    text.append(value, style=value_style)
    return text


# -- law 3: the motion law ---------------------------------------------------

EASING = "in_out_cubic"
TRAVEL_DURATION = 0.55

# the tiers
REVEAL_SETTLE = 1.1     # the whole opening performance lands inside this
REVEAL_STAGGER = 0.06   # per-element offset in a reveal cascade
IDLE_CADENCE = 7.0      # seconds between ambient breaths, page-idle only
IDLE_STEP = 1.6         # one ambient breath, edge to edge
CUE_DURATION = 0.18     # response under the hand — TCSS speaks it as $cue-duration
TELETYPE_CADENCE = 0.12  # one printed line per beat on a teletype surface


def travel(widget: Widget, x: int, y: int, duration: float = TRAVEL_DURATION) -> None:
    """Move an object to (x, y). The only sanctioned way anything moves."""
    target = ScalarOffset.from_offset((x, y))
    widget.styles.animate("offset", value=target, duration=duration, easing=EASING)


class Reveal:
    """A page's one opening performance, run once per entrance.

    The page hands ``play`` its steps — ``(delay_seconds, callable)``
    pairs — when it resumes. Replays are refused until ``arm()`` is
    called (do that when the page is left). ``settle()`` jumps to the
    end: every remaining step lands immediately — a reveal never blocks
    the hand, and it never runs during a live pass (the page guards
    that; the runner guards the rest).

    The performance is one sequenced worker, not a bank of one-shot
    timers: Textual timers skip a firing they missed (``skip=True``,
    no override from ``set_timer``), so under load a timer-driven
    cascade silently loses its tail. A sequence runs late, never less.
    """

    def __init__(self, screen: Widget) -> None:
        self._screen = screen
        self._played = False
        self._pending: list[Callable[[], None]] = []
        self._worker = None

    @property
    def played(self) -> bool:
        return self._played

    @property
    def settled(self) -> bool:
        return self._played and not self._pending

    def play(self, steps: Iterable[tuple[float, Callable[[], None]]]) -> bool:
        """Run the performance if this entrance hasn't seen it yet."""
        if self._played:
            return False
        self._played = True
        ordered = sorted(steps, key=lambda pair: pair[0])
        timed: list[tuple[float, Callable[[], None]]] = []
        for delay, step in ordered:
            if delay <= 0:
                step()
            else:
                timed.append((delay, step))
        self._pending = [step for _, step in timed]
        if timed:
            self._worker = self._screen.run_worker(
                self._perform(timed), group="reveal", exclusive=True
            )
        return True

    async def _perform(self, timed: list[tuple[float, Callable[[], None]]]) -> None:
        clock = 0.0
        for delay, step in timed:
            await asyncio.sleep(max(delay - clock, 0.0))
            clock = delay
            if step in self._pending:
                self._pending.remove(step)
                step()

    def settle(self) -> None:
        """Jump to settled: stop the clock, land every remaining step now."""
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
        pending, self._pending = self._pending, []
        for step in pending:
            step()

    def arm(self) -> None:
        """Re-arm for the next entrance (call when the page is left)."""
        self.settle()
        self._played = False


# -- the theme: the laws, registered -----------------------------------------
# Built last because it speaks for everything above. laws.py stays the
# single Python source of truth; the Theme carries it into every
# stylesheet as $variables.

THEME_VARIABLES = {
    "edge": EDGE,
    "edge-bright": EDGE_BRIGHT,
    "steel-bright": STEEL_BRIGHT,
    "steel-body": STEEL_BODY,
    "steel-mid": STEEL_MID,
    "steel-dim": STEEL_DIM,
    "fresh": FRESH,
    "pass": PASS,
    "fail": FAIL,
    "surface-low": SURFACE_LOW,
    "surface-high": SURFACE_HIGH,
    "surface-raised": SURFACE_RAISED,
    "cue-duration": f"{int(CUE_DURATION * 1000)}ms",
    "cue-easing": EASING,
}

KNIVVES_THEME = Theme(
    name="knivves",
    primary=ACCENT,
    accent=ACCENT,
    warning=ACCENT,
    error=FAIL,
    success=PASS,
    foreground=STEEL_BODY,
    background=BG,
    surface=SURFACE,
    panel=SURFACE,
    dark=True,
    variables=THEME_VARIABLES,
)
