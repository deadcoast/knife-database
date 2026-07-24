"""The Vault — page 0, the entry hall.

The machined door parts onto the building's showpiece: a brushed-steel
brand plate stamped like the door itself; the vault's state as a bank
of drawn meters, not a list; the doors as machined slabs with their
keycaps (the click is the key); the acquisition ladder; and the whole
collection drawn across the floor — the unknowns map, every blade a
column, the vault's knowledge and ignorance in one glance before a
single door is opened.
"""
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Callable, cast

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

from ...models import KnifeView
from ...research import audit_database
from ...state import VaultState, vault_state

if TYPE_CHECKING:
    from ..app import KnivvesApp
from .. import laws
from ..gauges import MeterBar
from ..masthead import Masthead
from ..surfaces import Engraving, grain_tone
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin
from .research import UnknownsMap

DOORS = [
    ("0", "home", "HOME", "overview — you are here"),
    ("1", "library", "LIBRARY", "browse, sort, classify, send"),
    ("2", "imports", "IMPORT KNIVES", "intake a listing URL or an ingestion .md"),
    ("3", "compare", "COMPARE MODELS", "two blades measured on the bench"),
    ("4", "market", "MARKET PRICES", "valuation, the $150 line, price reads"),
    ("5", "research", "RESEARCH", "fill the unknowns from their listings"),
]


class BrandPlate(Widget):
    """The building's nameplate: a band of brushed steel with the brand
    stamped into it and a machined seam beneath — the same material and
    discipline as the vault door's leaves."""

    DEFAULT_CSS = """
    BrandPlate {
        height: 5;
    }
    """

    def _stamp(self, cells: list[tuple[str, Style]], x: int, text: str, color: str, bold: bool = False) -> int:
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
        if y == 4:
            # the machined groove beneath the plate — a full-width channel
            return Strip([Segment(" " * width, Style(bgcolor="rgb(21,23,27)"))], width)
        cells: list[tuple[str, Style]] = [
            (" ", Style(bgcolor=grain_tone(x, y))) for x in range(width)
        ]
        if y == 0 or y == 3:
            # bolt studs along the top and bottom edges of the plate
            for x in range(4, width - 4, 24):
                cells[x] = ("●", Style(color=laws.EDGE_BRIGHT, bgcolor=grain_tone(x, y)))
        if y == 1:
            brand = "K N I V V E S"
            mark = "╱╱"
            x = max(4, (width - (len(brand) + len(mark) + 3)) // 2)
            x = self._stamp(cells, x, brand, laws.STEEL_BRIGHT, bold=True)
            self._stamp(cells, x + 3, mark, laws.ACCENT, bold=True)
        if y == 2:
            line = "folding knife research · canadian retail · local json"
            x = max(4, (width - len(line)) // 2)
            self._stamp(cells, x, line, laws.STEEL_DIM)
        return Strip([Segment(ch, style) for ch, style in cells], width)


class DoorRow(Static):
    """One door of the building, as hardware: a machined slab carrying
    its keycap — the click IS the key, firing the same ``action_room``
    the number binding does — and the slab lifts under the hand."""

    def __init__(self, page: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.page = page

    def on_click(self, event) -> None:
        opener = getattr(self.app, "action_room", None)
        if callable(opener):
            opener(self.page)


class HomeScreen(TipsMixin, Screen):
    CSS_PATH = "home.tcss"

    BINDINGS = [
        Binding("t", "expand_tip", "tip detail", show=False),
        Binding("escape", "dismiss_tip", "", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("home — the whole database in one glance"),
        "hall-state": Tip(
            "the collection, live",
            "meters over the same reading the\nCLI home page derives —\none source of truth\n\n"
            "unresearched counts records with\nopen gaps — door 5 fills them",
        ),
        "hall-doors": Tip(
            "the pages — keys or clicks open them",
            "every page is one keypress from\nanywhere in the building\n\n0 always returns here",
        ),
        "hall-reserve": Tip(
            "the buy list — next purchases",
            "the buy list's top rungs with the\nrunning cost\n\n"
            "the full ladder rides the library —\n1 then y",
        ),
        "hall-map": Tip(
            "the collection, drawn",
            "one column per knife,\none row per fact\n\n"
            "▪ lit — the vault knows\n· socket — a hole\n\ndoor 5 fills the holes",
        ),
    }

    @property
    def knivves(self) -> "KnivvesApp":
        return cast("KnivvesApp", self.app)

    @property
    def knives(self) -> list[KnifeView]:
        return self.knivves.knives

    def compose(self) -> ComposeResult:
        yield Masthead("HOME")
        yield BrandPlate(id="hall-brand")
        with Horizontal(id="hall"):
            with Vertical(id="hall-state", classes="hall-fixture"):
                yield Engraving("collection")
                yield MeterBar("approved", id="meter-approved")
                yield MeterBar("researched", id="meter-researched")
                yield MeterBar("priced", id="meter-priced")
                yield MeterBar("under $150", id="meter-affordable")
                yield Static("", classes="hall-fixture-body", id="hall-state-body")
            with Vertical(id="hall-doors", classes="hall-fixture"):
                yield Engraving("pages")
                with Vertical(id="hall-doors-body", classes="hall-fixture-body"):
                    for key, page, name, describes in DOORS:
                        row = DoorRow(page, id=f"door-{page}", classes="door-row")
                        row.update(self._door_text(key, name, describes))
                        yield row
            with Vertical(id="hall-reserve", classes="hall-fixture"):
                yield Engraving("buy list")
                yield Static("", classes="hall-fixture-body", id="hall-reserve-body")
            yield TipRail()
        yield UnknownsMap(id="hall-map")
        yield TipCapsule()
        yield Footer()

    def on_mount(self) -> None:
        self._reveal = laws.Reveal(self)
        self._surface()
        self.query_one("#hall-map", UnknownsMap).start_idle()
        self.show_room_tip()

    def on_screen_resume(self, event: ScreenResume) -> None:
        """Back in the hall: reflect anything filed or judged while away."""
        self._surface()
        self._power_on()

    def on_screen_suspend(self, event) -> None:
        self._reveal.arm()

    def _power_on(self) -> None:
        """REVEAL — one composed entrance: the plaques surface in a
        stagger as the door parts, and the floor powers on beneath them
        the way the research desk's instrument does."""
        fixtures = list(self.query(".hall-fixture"))
        unknowns = self.query_one("#hall-map", UnknownsMap)

        def cold() -> None:
            for fixture in fixtures:
                fixture.add_class("cold")

        steps: list[tuple[float, Callable[[], None]]] = [(0.0, cold), (0.0, unknowns.begin_reveal)]
        for i, fixture in enumerate(fixtures):
            steps.append((0.25 + i * laws.REVEAL_STAGGER * 3, partial(fixture.remove_class, "cold")))
        n = 10
        span = laws.REVEAL_SETTLE - 0.25
        for i in range(1, n + 1):
            steps.append((0.15 + span * (i / n) ** 0.5, partial(unknowns.reveal_step, i / n)))
        steps.append((laws.REVEAL_SETTLE, unknowns.end_reveal))
        self._reveal.play(steps)

    def spotlight(self, knife_id: str | None) -> None:
        """The floor answers the hand — same hook the research desk uses."""
        self.query_one("#hall-map", UnknownsMap).spotlight(knife_id)

    def action_dismiss_tip(self) -> None:
        self.dismiss_capsule()

    # ------------------------------------------------------------- plaques

    def _surface(self) -> None:
        state = vault_state(self.knivves.db, self.knives)
        self.query_one(Masthead).update_stats(self.knives)
        blades = max(state.blades, 1)
        researched = state.blades - state.unresearched
        self.query_one("#meter-approved", MeterBar).set_meter(
            state.approved / blades, f"{state.approved}/{state.blades}", laws.PASS
        )
        self.query_one("#meter-researched", MeterBar).set_meter(
            researched / blades, f"{researched}/{state.blades}"
        )
        self.query_one("#meter-priced", MeterBar).set_meter(
            state.priced / blades, f"{state.priced}/{state.blades}"
        )
        self.query_one("#meter-affordable", MeterBar).set_meter(
            state.affordable / blades, f"{state.affordable}", laws.ACCENT
        )
        self.query_one("#hall-state-body", Static).update(self._state_text(state))
        self.query_one("#hall-reserve-body", Static).update(self._reserve_text(state))
        audit = audit_database(self.knivves.db)
        columns = [
            (k.id, {g.field for g in audit.gaps_by_id.get(k.id, [])}) for k in self.knives
        ]
        self.query_one("#hall-map", UnknownsMap).set_state(columns)

    def _state_text(self, state: VaultState) -> Text:
        # every number is spoken, not derived — the provider is the
        # single reading both front doors share
        text = Text()
        text.append_text(laws.field("knives", str(state.blades)))
        if state.fresh:
            text.append(f"  ·  {state.fresh} ★new", style=f"bold {laws.FRESH}")
        text.append("\n")
        text.append_text(
            laws.field(
                "gaps",
                f"{state.unresearched} unresearched",
                laws.ACCENT if state.unresearched else laws.STEEL_DIM,
            )
        )
        text.append("\n")
        text.append_text(laws.field("avg", f"${state.average_cad:,.0f} CAD", laws.ACCENT))
        text.append("\n")
        text.append_text(
            laws.field(
                "new cache",
                f"gen {state.generation} · keeps {state.keep_generations}",
                laws.STEEL_DIM,
            )
        )
        return text

    def _door_text(self, key: str, name: str, describes: str) -> Text:
        text = Text()
        text.append(" ")
        text.append(f" {key} ", style=f"bold {laws.BG} on {laws.ACCENT}")
        text.append("  ")
        text.append(name, style=f"bold {laws.STEEL_BRIGHT}")
        text.append("\n      ")
        text.append(describes, style=laws.STEEL_DIM)
        return text

    def _reserve_text(self, state: VaultState) -> Text:
        views = state.ladder
        totals = state.ladder_totals
        text = Text()
        if not views:
            text.append("buy list is empty\n\n", style=laws.STEEL_MID)
            text.append("add one with a BuyList section:\nknivves add <file.md>", style=laws.STEEL_DIM)
            return text
        for (priority, knife), running in list(zip(views, totals))[:3]:
            text.append(f"{priority:>2} ", style=f"bold {laws.ACCENT}")
            text.append(knife.display_name[:34], style=laws.STEEL_BRIGHT)
            if knife.is_new:
                text.append("  ★new", style=laws.FRESH)
            text.append("\n   ")
            text.append(f"{knife.price_label:<14}", style=laws.STEEL_MID)
            text.append(f"Σ ${running:,.0f}", style=laws.STEEL_DIM)
            text.append("\n")
        deeper = len(views) - 3
        if deeper > 0:
            text.append(f"\n   +{deeper} more — press 1 then y,\n   or: knivves buylist", style=laws.STEEL_DIM)
        return text
