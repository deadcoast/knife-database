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
from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
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


class BenchScreen(TipsMixin, Screen):
    BINDINGS = [
        ("escape", "clear_bench", "Clear bench"),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("the bench — two blades, measured"),
        "calipers": Tip(
            "the calipers read the deltas",
            "◀ ▶ point at the cheaper blade\nΔ price · Δ length in mm\n= match · ≠ differ\n\n"
            "'incomparable' means the database\nis missing that measurement —\nhonest gaps, never guesses",
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
        yield Masthead("THE BENCH")
        with Horizontal(id="bench"):
            yield Plate(id="bench-left", classes="bench-plate")
            with Vertical(id="calipers"):
                yield Engraving("calipers")
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
        """The calipers take the measurement — staged on a new pair."""
        read = self.query_one("#calipers-read", Static)
        if len(self.slots) == 0:
            self._measured = ()
            read.update(Text("empty bench\n\nin the rack, press b on a\nknife to send it here", style=laws.STEEL_DIM))
            return
        if len(self.slots) == 1:
            self._measured = ()
            read.update(Text("one blade placed\n\nsend a second from the\nrack to compare", style=laws.STEEL_DIM))
            return

        pair = tuple(k.id for k in self.slots)
        lines = self._caliper_lines(*self.slots)
        if pair == self._measured:
            full = Text()
            for rendered in lines:
                full.append_text(rendered)
            read.update(full)
            return
        staged = Text()
        for rendered in lines:
            staged.append_text(rendered)
            read.update(staged.copy())
            await asyncio.sleep(0.18)
        self._measured = pair

    def _caliper_lines(self, a: KnifeView, b: KnifeView) -> list[Text]:
        lines: list[Text] = []

        def line(label: str, rendered: Text) -> None:
            row = Text()
            row.append(f"{label.upper():<{laws.LABEL_WIDTH}}", style=laws.STEEL_DIM)
            row.append_text(rendered)
            row.append("\n")
            lines.append(row)

        if a.price is not None and b.price is not None:
            delta = abs(a.price - b.price)
            cheaper = "◀" if a.price <= b.price else "▶"
            marker = Text()
            marker.append(cheaper, style=laws.PASS)
            marker.append(f"  Δ ${delta:,.2f}", style=laws.ACCENT)
            line("price", marker)
        else:
            line("price", Text("incomparable — missing price", style=laws.STEEL_DIM))

        mm_a, mm_b = blade_mm(a), blade_mm(b)
        if mm_a is not None and mm_b is not None:
            longer = "◀" if mm_a >= mm_b else "▶"
            marker = Text()
            marker.append(longer, style=laws.STEEL_MID)
            marker.append(f"  Δ {abs(mm_a - mm_b):.0f} mm", style=laws.ACCENT)
            line("length", marker)
        else:
            line("length", Text("incomparable — missing length", style=laws.STEEL_DIM))

        for label, va, vb in (
            ("steel", a.blade_steel, b.blade_steel),
            ("lock", a.lock_type, b.lock_type),
            ("class", a.classification, b.classification),
        ):
            same = va.lower() == vb.lower()
            line(label, Text("=  match", style=laws.STEEL_DIM) if same else Text("≠  differ", style=laws.STEEL_MID))
        return lines
