"""The Vault — page 0, the entry hall.

The machined door parts onto this room: the vault's state on one plaque,
every door with its key on the next, the acquisition ladder's top rungs
on the third. One glance answers what's inside, what's fresh, what's
unknown, and where every door is — the TUI twin of the CLI welcome page,
derived from the same backend reads.
"""
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Callable, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Footer, Static

from ...models import KnifeView
from ...state import VaultState, vault_state

if TYPE_CHECKING:
    from ..app import KnivvesApp
from .. import laws
from ..masthead import Masthead
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

DOORS = [
    ("0", "vault", "VAULT", "the entry hall — you are here"),
    ("1", "library", "LIBRARY", "browse, sort, classify, send"),
    ("2", "imports", "IMPORT KNIVES", "intake a listing URL or an ingestion .md"),
    ("3", "compare", "COMPARE MODELS", "two blades measured on the bench"),
    ("4", "market", "MARKET PRICES", "valuation, the $150 line, price reads"),
    ("5", "research", "RESEARCH", "fill the unknowns from their listings"),
]


class DoorRow(Static):
    """One door of the building, as hardware: the click IS the key —
    it fires the same ``action_room`` the number binding does — and the
    row lifts under the hand through the cue law in vault.tcss."""

    def __init__(self, page: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.page = page

    def on_click(self, event) -> None:
        opener = getattr(self.app, "action_room", None)
        if callable(opener):
            opener(self.page)


class VaultScreen(TipsMixin, Screen):
    CSS_PATH = "vault.tcss"

    BINDINGS = [
        Binding("t", "expand_tip", "tip detail", show=False),
        Binding("escape", "dismiss_tip", "", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("the entry hall — every door in one glance"),
        "hall-state": Tip(
            "the vault's state, live",
            "blades, freshness, judgments, gaps —\nthe same reads the CLI home page\nderives, one source of truth\n\n"
            "unresearched counts records with\nopen gaps — door 5 fills them",
        ),
        "hall-doors": Tip(
            "the doors — number keys open them",
            "every page is one keypress from\nanywhere in the building\n\n0 always returns here",
        ),
        "hall-reserve": Tip(
            "the next acquisitions",
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
        yield Masthead("ENTRY HALL")
        with Horizontal(id="hall"):
            with Vertical(id="hall-state", classes="hall-fixture"):
                yield Static("VAULT STATE", classes="hall-fixture-name")
                yield Static("", classes="hall-fixture-body", id="hall-state-body")
            with Vertical(id="hall-doors", classes="hall-fixture"):
                yield Static("THE DOORS", classes="hall-fixture-name")
                with Vertical(id="hall-doors-body", classes="hall-fixture-body"):
                    for key, page, name, describes in DOORS:
                        row = DoorRow(page, id=f"door-{page}", classes="door-row")
                        row.update(self._door_text(key, name, describes))
                        yield row
            with Vertical(id="hall-reserve", classes="hall-fixture"):
                yield Static("NEXT ACQUISITIONS", classes="hall-fixture-name")
                yield Static("", classes="hall-fixture-body", id="hall-reserve-body")
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

    def on_screen_suspend(self, event) -> None:
        self._reveal.arm()

    def _power_on(self) -> None:
        """REVEAL — the hall's plaques surface one by one as the door parts."""
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

    # ------------------------------------------------------------- plaques

    def _surface(self) -> None:
        state = vault_state(self.knivves.db, self.knives)
        self.query_one(Masthead).update_stats(self.knives)
        self.query_one("#hall-state-body", Static).update(self._state_text(state))
        self.query_one("#hall-reserve-body", Static).update(self._reserve_text(state))

    def _state_text(self, state: VaultState) -> Text:
        # every number is spoken, not derived — the provider is the
        # single reading both front doors share
        text = Text()
        text.append_text(laws.field("blades", str(state.blades)))
        text.append("\n")
        text.append_text(laws.field("★new", str(state.fresh), laws.FRESH if state.fresh else laws.STEEL_DIM))
        text.append("\n")
        text.append_text(laws.field("approved", str(state.approved), laws.CLASS_COLORS["approved"]))
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
                "window",
                f"gen {state.generation} · keeps {state.keep_generations}",
                laws.STEEL_DIM,
            )
        )
        return text

    def _door_text(self, key: str, name: str, describes: str) -> Text:
        text = Text()
        text.append(f" {key} ", style=f"bold {laws.ACCENT}")
        text.append("▸ ", style=laws.STEEL_DIM)
        text.append(f"{name:<15}", style=f"bold {laws.STEEL_BRIGHT}")
        text.append(describes, style=laws.STEEL_MID)
        return text

    def _reserve_text(self, state: VaultState) -> Text:
        views = state.ladder
        totals = state.ladder_totals
        text = Text()
        if not views:
            text.append("the reserve is empty\n\n", style=laws.STEEL_MID)
            text.append("ingest a ledger with a BuyList\nsection:  knivves add <file.md>", style=laws.STEEL_DIM)
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
            text.append(f"\n   +{deeper} deeper — the ladder rides\n   the library: 1 then y", style=laws.STEEL_DIM)
        return text
