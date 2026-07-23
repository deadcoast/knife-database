"""The Bench — the compare room.

Two Plates on a workbench with calipers between them. Knives arrive by
being sent from the Rack (`b` on the highlighted row): the record-object
travels between rooms — the same Plate class, per the house law of object
permanence.

Choreography, not simultaneity: a seated plate never re-animates; a
replaced plate departs toward its edge before its successor travels in.
When a new pair forms, the calipers visibly take the measurement — the
readings appear line by line, then hold. The masthead carries the bench
state beside the room name.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Footer, Static

from ..models import KnifeView

if TYPE_CHECKING:
    from .app import KnivvesVault
from . import laws
from .masthead import Masthead
from .surfaces import Engraving
from .plate import Plate
from .tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

IN_TO_MM = 25.4


def blade_mm(knife: KnifeView) -> float | None:
    """Blade length in millimetres from the record's stored string."""
    raw = knife.blade_length
    if raw == "Unknown":
        return None
    mm = re.search(r"(\d+(?:\.\d+)?)\s*mm", raw, re.I)
    if mm:
        return float(mm.group(1))
    inches = re.search(r"(\d+(?:\.\d+)?)", raw)
    if inches:
        return float(inches.group(1)) * IN_TO_MM
    return None


@dataclass
class Beam:
    """One numeric measurement: two values held between caliper jaws on
    a shared scale. A missing side leaves the jaws open — honest."""

    label: str
    va: float | None
    vb: float | None
    fmt: str  # "money" | "mm"

    @property
    def missing(self) -> bool:
        return self.va is None or self.vb is None

    @property
    def delta(self) -> float | None:
        if self.va is None or self.vb is None:
            return None
        return abs(self.va - self.vb)

    def text(self, value: float) -> str:
        return f"${value:,.2f}" if self.fmt == "money" else f"{value:.0f} mm"

    @property
    def delta_text(self) -> str:
        return f"Δ {self.text(self.delta)}" if self.delta is not None else ""


@dataclass
class Link:
    """One categorical comparison: a joined linkage when the values
    match, a broken one when they differ."""

    label: str
    va: str
    vb: str

    @property
    def same(self) -> bool:
        return self.va.lower() == self.vb.lower()


class Calipers(Widget):
    """The room's namesake, drawn: for each numeric fact one machined
    beam — both knives' values as jaws on one shared scale, the jaws
    closing onto the work, the Δ engraved in the measured span. The
    cheaper price reads pass-green; the longer blade reads bright.
    Categorical facts are linkages: ● joined on a match, ╳ broken on a
    differ. An open jaw means the database is missing that measurement."""

    DEFAULT_CSS = """
    Calipers {
        height: auto;
        margin-bottom: 1;
    }
    """

    LABEL_W = 7

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.beams: list[Beam] = []
        self.links: list[Link] = []
        self.measured: tuple[str, ...] = ()
        self._progress: list[float] = []
        self._links_shown = 0

    # ------------------------------------------------------------------ api

    def set_pair(self, a: KnifeView, b: KnifeView) -> None:
        self.beams = [
            Beam("price", a.price, b.price, "money"),
            Beam("length", blade_mm(a), blade_mm(b), "mm"),
        ]
        self.links = [
            Link("steel", a.blade_steel, b.blade_steel),
            Link("lock", a.lock_type, b.lock_type),
            Link("class", a.classification, b.classification),
        ]
        self.measured = (a.id, b.id)
        self._progress = [0.0] * len(self.beams)
        self._links_shown = 0
        self.refresh(layout=True)

    def clear(self) -> None:
        self.beams = []
        self.links = []
        self.measured = ()
        self._progress = []
        self._links_shown = 0
        self.refresh(layout=True)

    def settle(self) -> None:
        """A pair already read holds its measurement — no re-animation."""
        self._progress = [1.0] * len(self.beams)
        self._links_shown = len(self.links)
        self.refresh()

    async def take_measurement(self) -> None:
        """The jaws close beam by beam, then the linkages engage."""
        for index in range(len(self.beams)):
            for step in range(1, 6):
                self._progress[index] = step / 5
                self.refresh()
                await asyncio.sleep(0.07)
            await asyncio.sleep(0.12)
        for shown in range(1, len(self.links) + 1):
            self._links_shown = shown
            self.refresh()
            await asyncio.sleep(0.15)

    # --------------------------------------------------------------- render

    def get_content_height(self, container, viewport, width: int) -> int:
        if not self.beams:
            return 0
        return len(self.beams) * 3 + len(self.links)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        strip = self._render_row(y, width)
        return strip.adjust_cell_length(width)

    def _render_row(self, y: int, width: int) -> Strip:
        beam_rows = len(self.beams) * 3
        if y < beam_rows:
            index, row = divmod(y, 3)
            if row == 0:
                return self._rail_row(self.beams[index], self._progress[index], width)
            if row == 1:
                return self._values_row(self.beams[index], self._progress[index], width)
            return Strip([])
        link_index = y - beam_rows
        if link_index < self._links_shown:
            return self._link_row(self.links[link_index], width)
        return Strip([])

    def _rail_row(self, beam: Beam, progress: float, width: int) -> Strip:
        rail_w = max(width - self.LABEL_W, 8)
        segments = [Segment(f"{beam.label.upper():<{self.LABEL_W}}", Style(color=laws.STEEL_DIM))]
        if beam.missing:
            segments.append(Segment("╌" * rail_w, Style(color=laws.EDGE_BRIGHT)))
            return Strip(segments)
        scale = max(beam.va, beam.vb) * 1.06 or 1.0
        ja = round(beam.va / scale * (rail_w - 1))
        jb = round(beam.vb / scale * (rail_w - 1))
        left_target, right_target = min(ja, jb), max(ja, jb)
        # the jaws travel in from the rail ends onto the work
        jaw_l = round(progress * left_target)
        jaw_r = (rail_w - 1) - round(progress * ((rail_w - 1) - right_target))
        cells: list[tuple[str, Style]] = [("─", Style(color=laws.EDGE_BRIGHT))] * rail_w
        closed = progress >= 1.0
        if closed and jaw_r > jaw_l + 1:
            for x in range(jaw_l + 1, jaw_r):
                cells[x] = ("━", Style(color=laws.ACCENT))
        jaw_style = Style(color=laws.STEEL_BRIGHT, bold=True)
        cells[jaw_l] = ("▐", jaw_style)
        cells[jaw_r] = ("▌" if jaw_r != jaw_l else "█", jaw_style)
        segments.extend(Segment(ch, style) for ch, style in cells)
        return Strip(segments)

    def _values_row(self, beam: Beam, progress: float, width: int) -> Strip:
        if beam.missing:
            note = f"incomparable — missing {beam.label}"
            return Strip([
                Segment(" " * self.LABEL_W),
                Segment(note, Style(color=laws.STEEL_DIM)),
            ])
        if progress < 1.0:
            return Strip([])
        if beam.fmt == "money":
            # the cheaper blade wears the buy signal
            style_a = Style(color=laws.PASS if beam.va <= beam.vb else laws.STEEL_MID, bold=beam.va <= beam.vb)
            style_b = Style(color=laws.PASS if beam.vb < beam.va else laws.STEEL_MID, bold=beam.vb < beam.va)
        else:
            # the longer blade reads bright
            style_a = Style(color=laws.STEEL_BRIGHT if beam.va >= beam.vb else laws.STEEL_MID)
            style_b = Style(color=laws.STEEL_BRIGHT if beam.vb > beam.va else laws.STEEL_MID)
        lane = max(width - self.LABEL_W, 8)
        text_a = beam.text(beam.va)
        text_b = beam.text(beam.vb)
        delta = beam.delta_text
        if len(text_a) + len(text_b) + len(delta) + 2 > lane and beam.fmt == "money":
            # a tight lane reads in whole dollars — never clipped digits
            text_a = f"${beam.va:,.0f}"
            text_b = f"${beam.vb:,.0f}"
            delta = f"Δ ${beam.delta:,.0f}"
        gap = lane - len(text_a) - len(text_b) - len(delta)
        pad_l = max(gap // 2, 1)
        pad_r = max(gap - pad_l, 1)
        return Strip([
            Segment(" " * self.LABEL_W),
            Segment(text_a, style_a),
            Segment(" " * pad_l),
            Segment(delta, Style(color=laws.ACCENT, bold=True)),
            Segment(" " * pad_r),
            Segment(text_b, style_b),
        ])

    def _link_row(self, link: Link, width: int) -> Strip:
        lane = max(width - self.LABEL_W, 12)
        side_w = (lane - 5) // 2

        def fit(value: str) -> str:
            return value if len(value) <= side_w else value[: side_w - 1] + "…"

        va = fit(link.va).rjust(side_w)
        vb = fit(link.vb).ljust(side_w)
        if link.same:
            joint, joint_style = "──●──", Style(color=laws.PASS)
            value_style = Style(color=laws.STEEL_DIM)
        else:
            joint, joint_style = "─╴╳╶─", Style(color=laws.STEEL_BRIGHT, bold=True)
            value_style = Style(color=laws.STEEL_BRIGHT)
        return Strip([
            Segment(f"{link.label.upper():<{self.LABEL_W}}", Style(color=laws.STEEL_DIM)),
            Segment(va, value_style),
            Segment(joint, joint_style),
            Segment(vb, value_style),
        ])


class BenchScreen(TipsMixin, Screen):
    BINDINGS = [
        ("escape", "clear_bench", "Clear bench"),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("compare models — two blades, measured"),
        "calipers": Tip(
            "the calipers take the measurement",
            "each beam holds both values\nbetween jaws on one scale —\nthe Δ is the span between\nthe jaw tips\n\n"
            "cheaper price reads green ·\nlonger blade reads bright\n● linked = match · ╳ = differ\n\n"
            "an open jaw means the database\nis missing that measurement —\nhonest gaps, never guesses",
        ),
        "bench-left": Tip("sent from the rack with b"),
        "bench-right": Tip("a third arrival replaces the older plate"),
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.slots: list[KnifeView] = []
        self._seated: list[str] = []          # ids currently on the bench, by slot
        self._measured: tuple[str, ...] = ()  # the last pair the calipers read

    def compose(self) -> ComposeResult:
        yield Masthead("COMPARE MODELS")
        with Horizontal(id="bench"):
            yield Plate(id="bench-left", classes="bench-plate")
            with Vertical(id="calipers"):
                yield Engraving("calipers")
                yield Calipers(id="calipers-instrument")
                yield Static("", id="calipers-read", classes="station-body")
            yield Plate(id="bench-right", classes="bench-plate")
            yield TipRail()
        yield TipCapsule()
        yield Footer()

    @property
    def vault(self) -> "KnivvesVault":
        return cast("KnivvesVault", self.app)

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.query_one(Masthead).update_stats(self.vault.knives)
        self.show_room_tip()
        self._drain_queue()
        self.run_worker(self._choreograph(), exclusive=True)

    # ------------------------------------------------------------- intake

    def _drain_queue(self) -> None:
        queue = self.vault.bench_queue
        while queue:
            knife = queue.pop(0)
            if any(k.id == knife.id for k in self.slots):
                continue
            if len(self.slots) >= 2:
                self.slots.pop(0)
            self.slots.append(knife)

    def action_clear_bench(self) -> None:
        if self.dismiss_capsule():
            return
        self.slots = []
        self.run_worker(self._choreograph(), exclusive=True)

    # -------------------------------------------------------- choreography

    async def _choreograph(self) -> None:
        """Move only what changed: seated plates hold, replacements depart
        before successors arrive, arrivals travel in from their edge."""
        left = self.query_one("#bench-left", Plate)
        right = self.query_one("#bench-right", Plate)
        for index, (plate, edge_x) in enumerate(((left, -60), (right, 60))):
            target = self.slots[index] if index < len(self.slots) else None
            seated = self._seated[index] if index < len(self._seated) else None
            if target is None:
                if plate.display:
                    laws.travel(plate, edge_x, 0, duration=0.3)
                    await asyncio.sleep(0.35)
                    plate.display = False
            elif seated == target.id:
                plate.display = True
                plate.set_knife(target)  # silent data refresh, no motion
            else:
                if seated is not None and plate.display:
                    laws.travel(plate, edge_x, 0, duration=0.3)
                    await asyncio.sleep(0.35)
                plate.display = True
                plate.set_knife(target)
                plate.styles.offset = (edge_x, 0)
                laws.travel(plate, 0, 0, duration=0.4)
                await asyncio.sleep(0.45)
        self._seated = [k.id for k in self.slots]
        self._bench_state()
        await self._measure()

    def _bench_state(self) -> None:
        if len(self.slots) == 2:
            a, b = self.slots
            state = f"{a.brand} vs {b.brand}"
        elif len(self.slots) == 1:
            state = "one blade placed"
        else:
            state = "bench empty"
        self.query_one(Masthead).set_context(state)

    # ------------------------------------------------------------ calipers

    async def _measure(self) -> None:
        """The instrument takes the measurement — staged on a new pair."""
        read = self.query_one("#calipers-read", Static)
        instrument = self.query_one(Calipers)
        if len(self.slots) == 0:
            self._measured = ()
            instrument.clear()
            read.update(Text("empty bench\n\nin the rack, press b on a\nknife to send it here", style=laws.STEEL_DIM))
            return
        if len(self.slots) == 1:
            self._measured = ()
            instrument.clear()
            read.update(Text("one blade placed\n\nsend a second from the\nrack to compare", style=laws.STEEL_DIM))
            return

        read.update("")
        pair = tuple(k.id for k in self.slots)
        instrument.set_pair(*self.slots)
        if pair == self._measured:
            instrument.settle()  # an already-read pair holds, no re-animation
            return
        await instrument.take_measurement()
        self._measured = pair
