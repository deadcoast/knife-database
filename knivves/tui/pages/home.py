"""Home — page 0, the entry hall.

The machined door parts onto the building's showpiece: the brand stamped
at nameplate size into a raised steel plaque; the collection as a full
column of drawn instruments — meters, the classification split, the
price distribution; the pages as six machined slabs each carrying a live
reading; and the buy list beside the newest arrivals. The room is
composed to the frame: every column runs masthead to footer.
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

from ... import ledger
from ...models import KnifeView
from ...state import VaultState, vault_state

if TYPE_CHECKING:
    from ..app import KnivvesApp
from .. import laws
from ..gauges import GradientBars, MeterBar, SplitBand
from ..masthead import Masthead
from ..surfaces import _BASE, _grain, Engraving, grain_tone, stamp_rows
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

DOORS = [
    ("0", "home", "HOME", "overview — you are here"),
    ("1", "library", "LIBRARY", "browse, sort, classify, send"),
    ("2", "imports", "IMPORT KNIVES", "intake a URL or an ingestion .md"),
    ("3", "compare", "COMPARE MODELS", "two blades measured on the bench"),
    ("4", "market", "MARKET PRICES", "valuation and the $150 line"),
    ("5", "research", "RESEARCH", "fill unknowns from their listings"),
]


class BrandPlate(Widget):
    """The building's nameplate: the brand stamped three rows tall into a
    raised plaque of brushed steel — lit top edge, thrown shadow, corner
    bolts — with machined rules cut into the flanking band."""

    DEFAULT_CSS = """
    BrandPlate {
        height: 7;
    }
    """

    TAGLINE = "folding knife research · canadian retail · local json"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows = stamp_rows("KNIVVES")

    def _raised(self, x: int, y: int) -> str:
        delta = _grain(x, y) + 7
        return f"rgb({_BASE[0] + delta},{_BASE[1] + delta},{_BASE[2] + delta})"

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        brand_w = len(self._rows[0])
        plaque_w = min(max(brand_w, len(self.TAGLINE)) + 10, max(width - 8, 20))
        x0 = max(4, (width - plaque_w) // 2)
        x1 = x0 + plaque_w - 1
        cells: list[tuple[str, Style]] = [
            (" ", Style(bgcolor=grain_tone(x, y))) for x in range(width)
        ]

        def put(x: int, ch: str, color: str, bold: bool = False) -> None:
            if 0 <= x < width:
                cells[x] = (ch, Style(color=color, bgcolor=self._raised(x, y), bold=bold))

        if y in (0, 6):
            # a crisp machined rim, not a bar: heavy box frame, lit on
            # top, shadowed on the bottom
            tone = laws.BEVEL_LIGHT if y == 0 else laws.BEVEL_SHADOW
            left, mid, right = ("┏", "━", "┓") if y == 0 else ("┗", "━", "┛")
            cells[x0] = (left, Style(color=tone, bgcolor=grain_tone(x0, y)))
            for x in range(x0 + 1, x1):
                cells[x] = (mid, Style(color=tone, bgcolor=grain_tone(x, y)))
            cells[x1] = (right, Style(color=tone, bgcolor=grain_tone(x1, y)))
            return Strip([Segment(ch, style) for ch, style in cells], width)

        for x in range(x0, x1 + 1):
            cells[x] = (" ", Style(bgcolor=self._raised(x, y)))
        cells[x0] = ("┃", Style(color=laws.BEVEL_LIGHT, bgcolor=grain_tone(x0, y)))
        cells[x1] = ("┃", Style(color=laws.BEVEL_SHADOW, bgcolor=grain_tone(x1, y)))
        if y in (1, 5):
            put(x0 + 2, "●", laws.EDGE_BRIGHT)
            put(x1 - 2, "●", laws.EDGE_BRIGHT)
        if 2 <= y <= 4:
            row = self._rows[y - 2]
            bx = x0 + (plaque_w - brand_w) // 2
            for i, ch in enumerate(row):
                if ch != " ":
                    put(bx + i, ch, laws.STEEL_BRIGHT, bold=True)
            if y == 4:
                # the maker's mark rides the letter baseline
                put(bx + brand_w + 2, "╱", laws.ACCENT, bold=True)
                put(bx + brand_w + 3, "╱", laws.ACCENT, bold=True)
            if y == 3:
                # flank rules run from an engraved tip INTO the frame
                if x0 - 1 > 5:
                    cells[4] = ("╾", Style(color=laws.STEEL_MID, bgcolor=grain_tone(4, y)))
                    for x in range(5, x0):
                        cells[x] = ("─", Style(color=laws.EDGE_BRIGHT, bgcolor=grain_tone(x, y)))
                if x1 + 1 < width - 5:
                    for x in range(x1 + 1, width - 4):
                        cells[x] = ("─", Style(color=laws.EDGE_BRIGHT, bgcolor=grain_tone(x, y)))
                    cells[width - 5] = ("╼", Style(color=laws.STEEL_MID, bgcolor=grain_tone(width - 5, y)))
        if y == 5:
            tx = x0 + max((plaque_w - len(self.TAGLINE)) // 2, 2)
            for i, ch in enumerate(self.TAGLINE[: plaque_w - 4]):
                put(tx + i, ch, laws.STEEL_DIM)
        return Strip([Segment(ch, style) for ch, style in cells], width)


class DoorRow(Static):
    """One page of the building, as hardware: a machined slab carrying
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
            "every page is one keypress from\nanywhere in the building\n\n0 always returns here\n\n"
            "each slab carries a live reading\nfrom the database",
        ),
        "hall-reserve": Tip(
            "the buy list — next purchases",
            "the buy list's top rungs with the\nrunning cost\n\n"
            "the full ladder rides the library —\n1 then y",
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
            with Vertical(id="hall-state", classes="hall-fixture") as collection_pane:
                collection_pane.border_title = "COLLECTION"
                yield MeterBar("approved", id="meter-approved")
                yield MeterBar("researched", id="meter-researched")
                yield MeterBar("priced", id="meter-priced")
                yield MeterBar("under $150", id="meter-affordable")
                yield Static("", classes="hall-fixture-body", id="hall-state-body")
                yield Engraving("classes")
                yield SplitBand(id="hall-classes")
                yield Engraving("prices")
                yield GradientBars(id="hall-prices")
                yield Engraving("common steels", id="hall-steels-title")
                yield Static("", id="hall-steels-body")
            with Vertical(id="hall-doors", classes="hall-fixture") as pages_pane:
                pages_pane.border_title = "PAGES"
                pages_pane.border_subtitle = "keys or clicks"
                with Vertical(id="hall-doors-body", classes="hall-fixture-body"):
                    for key, page, name, describes in DOORS:
                        yield DoorRow(page, id=f"door-{page}", classes="door-row")
            with Vertical(id="hall-reserve", classes="hall-fixture") as buylist_pane:
                buylist_pane.border_title = "BUY LIST"
                yield Static("", classes="hall-fixture-body", id="hall-reserve-body")
                yield Engraving("new arrivals")
                yield Static("", id="hall-fresh-body")
                yield Engraving("commands")
                yield Static("", id="hall-commands-body")
            yield TipRail()
        yield TipCapsule()
        yield Footer()

    def on_mount(self) -> None:
        self._reveal = laws.Reveal(self)
        self._surface()
        self.show_room_tip()

    def on_screen_resume(self, event: ScreenResume) -> None:
        """Back in the hall: reflect anything filed or judged while away."""
        self._surface()
        self._power_on()
        # re-cut the lists once real pane heights exist
        self.set_timer(0.15, self._surface)

    def on_screen_suspend(self, event) -> None:
        self._reveal.arm()

    def _power_on(self) -> None:
        """REVEAL — the panes surface in a stagger as the door parts."""
        fixtures = list(self.query(".hall-fixture"))

        def cold() -> None:
            for fixture in fixtures:
                fixture.add_class("cold")

        steps: list[tuple[float, Callable[[], None]]] = [(0.0, cold)]
        for i, fixture in enumerate(fixtures):
            steps.append((0.25 + i * laws.REVEAL_STAGGER * 3, partial(fixture.remove_class, "cold")))
        self._reveal.play(steps)

    def action_dismiss_tip(self) -> None:
        self.dismiss_capsule()

    def on_resize(self, event) -> None:
        """The hall re-cuts its lists to the room's real size."""
        self._surface()

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
        rejected = sum(1 for k in self.knives if k.classification == "rejected")
        unclassified = state.blades - state.approved - rejected
        self.query_one("#hall-classes", SplitBand).set_segments([
            ("approved", state.approved, laws.PASS),
            ("open", unclassified, laws.STEEL_DIM),
            ("rejected", rejected, laws.FAIL),
        ])
        self.query_one("#hall-prices", GradientBars).update_bars(
            ledger.price_buckets(self.knives)
        )
        # the steels section exists only where the column has room for it
        room = (self.query_one("#hall-state").size.height or 0) >= 35
        self.query_one("#hall-steels-title").display = room
        self.query_one("#hall-steels-body").display = room
        if room:
            self.query_one("#hall-steels-body", Static).update(self._steels_text())
        for key, page, name, describes in DOORS:
            row = self.query_one(f"#door-{page}", DoorRow)
            row.update(self._door_text(key, name, describes, self._door_reading(page, state)))
        self.query_one("#hall-reserve-body", Static).update(self._reserve_text(state))
        self.query_one("#hall-fresh-body", Static).update(self._fresh_text(state))
        self.query_one("#hall-commands-body", Static).update(self._commands_text())
        self.query_one("#hall-state").border_subtitle = f"{state.blades} knives"

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

    def _door_reading(self, page: str, state: VaultState) -> str:
        """The live number each slab carries — read from the database."""
        if page == "library":
            return f"{state.blades} records"
        if page == "imports":
            return f"{state.fresh} ★new" if state.fresh else f"gen {state.generation}"
        if page == "compare":
            seats = len(self.knivves.compare_queue)
            try:
                seats = max(seats, len(getattr(self.knivves.get_screen("compare"), "slots", [])))
            except Exception:
                pass
            return f"{seats}/2 chosen" if seats else "nothing chosen"
        if page == "market":
            return f"avg ${state.average_cad:,.0f}"
        if page == "research":
            return f"{state.unresearched} gaps open"
        return "0 returns here from anywhere"

    def _door_text(self, key: str, name: str, describes: str, reading: str = "") -> Text:
        text = Text()
        text.append(f" {key} ", style=f"bold {laws.BG} on {laws.ACCENT}")
        text.append("  ")
        text.append(name, style=f"bold {laws.STEEL_BRIGHT}")
        text.append("\n     ")
        text.append(describes, style=laws.STEEL_DIM)
        text.append("\n     ")
        reading_tone = laws.STEEL_DIM if key == "0" else laws.ACCENT
        text.append(reading, style=reading_tone)
        return text

    def _reserve_text(self, state: VaultState) -> Text:
        views = state.ladder
        totals = state.ladder_totals
        text = Text()
        if not views:
            for rank in (1, 2, 3):
                text.append(f"{rank:>2} ", style=laws.STEEL_DIM)
                text.append("╌" * 18, style=laws.EDGE)
                text.append("\n")
            text.append("\nempty\n", style=laws.STEEL_DIM)
            text.append("a BuyList section fills it\n", style=laws.STEEL_DIM)
            text.append("knivves add <file.md>", style=laws.STEEL_MID)
            return text
        for (priority, knife), running in list(zip(views, totals))[:3]:
            text.append(f"{priority:>2} ", style=f"bold {laws.ACCENT}")
            text.append(knife.display_name[:30], style=laws.STEEL_BRIGHT)
            if knife.is_new:
                text.append("  ★new", style=laws.FRESH)
            text.append("\n   ")
            text.append(f"{knife.price_label:<14}", style=laws.STEEL_MID)
            text.append(f"Σ ${running:,.0f}", style=laws.STEEL_DIM)
            text.append("\n")
        deeper = len(views) - 3
        if deeper > 0:
            text.append(f"\n   +{deeper} more — press 1 then y", style=laws.STEEL_DIM)
        return text

    def _fresh_text(self, state: VaultState) -> Text:
        """The newest records in the cache — ★new until the next update."""
        fresh = [k for k in self.knives if k.is_new]
        text = Text()
        if not fresh:
            text.append(f"none in this cache (gen {state.generation})\n", style=laws.STEEL_DIM)
            text.append(f"knivves update opens gen {state.generation + 1}", style=laws.STEEL_DIM)
            return text
        cap = max(4, (self.query_one("#hall-reserve").size.height or 30) - 22)
        for knife in fresh[:cap]:
            text.append("★ ", style=laws.FRESH)
            text.append(f"{knife.display_name[:24]:<25}", style=laws.STEEL_BRIGHT)
            text.append(f"{knife.price_label}\n", style=laws.STEEL_MID)
        if len(fresh) > cap:
            text.append(f"  +{len(fresh) - cap} more ★new in the library", style=laws.STEEL_DIM)
        return text

    def _steels_text(self) -> Text:
        """The collection's most common blade steels — counted, adaptive."""
        counts: dict[str, int] = {}
        for knife in self.knives:
            steel = knife.blade_steel
            if steel and steel != "Unknown":
                counts[steel] = counts.get(steel, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: -kv[1])
        cap = max(2, (self.query_one("#hall-state").size.height or 35) - 33)
        text = Text()
        if not ranked:
            text.append("no steels on record yet —\ndoor 5 fills them", style=laws.STEEL_DIM)
            return text
        top = ranked[0][1] or 1
        for steel, count in ranked[:cap]:
            text.append(f"{steel[:18]:<19}", style=laws.STEEL_BRIGHT)
            text.append("▪" * max(1, round(count / top * 8)), style=laws.STEEL_MID)
            text.append(f" {count}\n", style=laws.STEEL_DIM)
        return text

    def _commands_text(self) -> Text:
        text = Text()
        for command, does in (
            ("knivves add <file.md>", "intake an ingestion file"),
            ("knivves update", "seal the batch · next gen"),
            ("knivves buylist", "the full ladder, printed"),
        ):
            text.append(f"{command}\n", style=laws.STEEL_MID)
            text.append(f"  {does}\n", style=laws.STEEL_DIM)
        return text
