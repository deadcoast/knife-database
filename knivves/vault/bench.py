"""The Bench — the compare room.

Two Plates on a workbench with calipers between them. Knives arrive by
being sent from the Rack (`b` on the highlighted row): the record-object
travels between rooms — the same Plate class, per the house law of object
permanence. The calipers read the deltas: cheaper blade marked, blade
length difference in millimetres, spec matches and mismatches.

A third knife sent to a full bench replaces the older occupant.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Footer, Static

from ..models import KnifeView

if TYPE_CHECKING:
    from .app import KnivvesVault
from . import laws
from .masthead import Masthead
from .plate import Plate

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


class BenchScreen(Screen):
    BINDINGS = [("escape", "clear_bench", "Clear bench")]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.slots: list[KnifeView] = []

    def compose(self) -> ComposeResult:
        yield Masthead("THE BENCH")
        with Horizontal(id="bench"):
            yield Plate(id="bench-left", classes="bench-plate")
            with Vertical(id="calipers"):
                yield Static("CALIPERS", classes="station-name")
                yield Static("", id="calipers-read", classes="station-body")
            yield Plate(id="bench-right", classes="bench-plate")
        yield Footer()

    @property
    def vault(self) -> "KnivvesVault":
        return cast("KnivvesVault", self.app)

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.query_one(Masthead).update_stats(self.vault.knives)
        self._drain_queue()
        self._refit()

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
        self.slots = []
        self._refit()

    # ------------------------------------------------------------- render

    def _refit(self) -> None:
        left = self.query_one("#bench-left", Plate)
        right = self.query_one("#bench-right", Plate)
        for plate, index, edge_x in ((left, 0, -60), (right, 1, 60)):
            if index < len(self.slots):
                plate.display = True
                plate.set_knife(self.slots[index])
                plate.styles.offset = (edge_x, 0)
                laws.travel(plate, 0, 0, duration=0.4)
            else:
                plate.display = False
        self._read_calipers()

    def _read_calipers(self) -> None:
        read = self.query_one("#calipers-read", Static)
        if len(self.slots) == 0:
            read.update(Text("empty bench\n\nin the rack, press b on a\nknife to send it here", style=laws.STEEL_DIM))
            return
        if len(self.slots) == 1:
            read.update(Text("one blade placed\n\nsend a second from the\nrack to compare", style=laws.STEEL_DIM))
            return

        a, b = self.slots
        text = Text()

        def line(label: str, rendered: Text) -> None:
            text.append(f"{label.upper():<{laws.LABEL_WIDTH}}", style=laws.STEEL_DIM)
            text.append_text(rendered)
            text.append("\n")

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

        read.update(text)
