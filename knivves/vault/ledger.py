"""The Ledger — the price intelligence room.

The vault's money, read like an instrument panel: valuation, the price
distribution, and the knives sitting near the $150 affordable line. Press
`s` and the vault surveys its own market — every listed knife's live page
is re-read, prices move through the collection in real time, history is
recorded on each record, and the affordable rule re-tags whatever crossed
the line. Escape cancels a running survey; whatever was observed is kept.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Footer, Static

from .. import ledger, scrape
from ..models import KnifeView, knife_views
from ..store import save_database
from . import laws
from .masthead import Masthead

if TYPE_CHECKING:
    from .app import KnivvesVault

BAR_WIDTH = 22
SUPPORTED = ("bladescanada.com", "houseofknives.ca")


class LedgerScreen(Screen):
    BINDINGS = [
        ("s", "survey", "Survey the market"),
        ("escape", "cancel_survey", "Cancel survey"),
    ]

    SURVEY_DELAY = 0.25  # politeness between fetches; tests set 0

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._surveying = False

    def compose(self) -> ComposeResult:
        yield Masthead("THE LEDGER")
        with Horizontal(id="ledger"):
            with Vertical(classes="station", id="ledger-valuation"):
                yield Static("VALUATION", classes="station-name")
                yield Static("", id="valuation-read", classes="station-body")
            with Vertical(classes="station", id="ledger-line"):
                yield Static("THE $150 LINE", classes="station-name")
                yield Static("", id="line-read", classes="station-body")
            with Vertical(classes="station", id="ledger-movers"):
                yield Static("MARKET SURVEY", classes="station-name")
                yield Static("", id="movers-read", classes="station-body")
        yield Footer()

    @property
    def vault(self) -> "KnivvesVault":
        return cast("KnivvesVault", self.app)

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.query_one(Masthead).update_stats(self.vault.knives)
        self._read_valuation()
        self._read_line()
        if not self._surveying:
            self._idle_movers()

    # ------------------------------------------------------------- panels

    def _read_valuation(self) -> None:
        knives = self.vault.knives
        v = ledger.vault_valuation(knives)
        text = Text()
        for label, value, style in (
            ("value", f"${v['total']:,.0f} CAD", laws.ACCENT),
            ("priced", f"{v['priced']} of {len(knives)}", laws.STEEL_BRIGHT),
            ("average", f"${v['average']:,.2f}", laws.STEEL_BRIGHT),
            ("afford.", f"{v['affordable']} under the line", laws.PASS),
        ):
            text.append_text(laws.field(label, value, style))
            text.append("\n")
        text.append("\n")
        buckets = ledger.price_buckets(knives)
        top = max((count for _, count in buckets), default=1) or 1
        for label, count in buckets:
            text.append(f"{label:<10}", style=laws.STEEL_DIM)
            text.append("█" * max(1 if count else 0, round(count / top * BAR_WIDTH)), style=laws.STEEL_MID)
            text.append(f" {count}\n", style=laws.STEEL_DIM)
        self.query_one("#valuation-read", Static).update(text)

    def _read_line(self) -> None:
        near = ledger.near_the_line(self.vault.knives)
        text = Text()
        text.append(
            f"the affordable rule re-tags at ${ledger.AFFORDABLE_THRESHOLD_CAD:,.0f} —\n"
            f"these sit within ${ledger.NEAR_LINE_BAND_CAD:,.0f} of it:\n\n",
            style=laws.STEEL_DIM,
        )
        if not near:
            text.append("nothing near the line", style=laws.STEEL_DIM)
        for knife in near[:10]:
            below = (knife.price or 0) < ledger.AFFORDABLE_THRESHOLD_CAD
            text.append("▾ " if below else "▴ ", style=laws.PASS if below else laws.STEEL_MID)
            name = knife.display_name
            text.append(f"{name[:26]:<27}", style=laws.STEEL_BRIGHT)
            text.append(f"{knife.price_label}\n", style=laws.ACCENT)
        self.query_one("#line-read", Static).update(text)

    def _idle_movers(self) -> None:
        surveyed = any(len(k.raw.get("price_history") or []) > 1 for k in self.vault.knives)
        text = Text()
        if surveyed:
            text.append("survey on record — press s to run a fresh one\n", style=laws.STEEL_DIM)
        else:
            text.append("no survey on record\n\n", style=laws.STEEL_DIM)
            text.append("press s — the vault re-reads every live\nlisting and records what moved", style=laws.STEEL_DIM)
        self.query_one("#movers-read", Static).update(text)

    # ------------------------------------------------------------- survey

    def action_survey(self) -> None:
        if not self._surveying:
            self.run_worker(self.survey(), exclusive=True)

    def action_cancel_survey(self) -> None:
        if self._surveying:
            self.workers.cancel_all()

    def _targets(self) -> list[KnifeView]:
        out = []
        for knife in self.vault.knives:
            retailers = knife.retailers
            url = retailers[0].get("url") if retailers else None
            if url and any(host in url for host in SUPPORTED):
                out.append(knife)
        return out

    async def survey(self) -> None:
        self._surveying = True
        movers_read = self.query_one("#movers-read", Static)
        today = date.today().isoformat()
        targets = self._targets()
        movers: list[tuple[KnifeView, float]] = []
        unchanged = unreachable = 0
        raw_by_id = {k.get("id"): k for k in self.vault.db.get("knives", []) if isinstance(k, dict)}
        try:
            for i, knife in enumerate(targets, start=1):
                movers_read.update(self._survey_frame(i, len(targets), knife, movers, unchanged, unreachable))
                record = raw_by_id.get(knife.id)
                if record is None:
                    continue
                url = knife.retailers[0]["url"]
                try:
                    listing = await asyncio.to_thread(scrape.fetch_listing, url)
                except scrape.ScrapeError:
                    unreachable += 1
                    continue
                delta = ledger.observe(record, listing.price_cad, listing.availability, today)
                ledger.retag_affordable(record)
                if delta:
                    movers.append((knife, delta))
                else:
                    unchanged += 1
                if self.SURVEY_DELAY:
                    await asyncio.sleep(self.SURVEY_DELAY)
        finally:
            # keep whatever was observed, even on cancel
            save_database(self.vault.db, self.vault.db_path)
            self.vault.knives = knife_views(self.vault.db)
            self._surveying = False
            self.query_one(Masthead).update_stats(self.vault.knives)
            self._read_valuation()
            self._read_line()
            movers_read.update(self._survey_result(len(targets), movers, unchanged, unreachable))

    def _survey_frame(
        self, i: int, total: int, knife: KnifeView,
        movers: list[tuple[KnifeView, float]], unchanged: int, unreachable: int,
    ) -> Text:
        text = Text()
        text.append(f"surveying {i}/{total}\n", style=laws.ACCENT)
        text.append(f"{knife.display_name[:34]}\n\n", style=laws.STEEL_MID)
        text.append_text(self._movers_lines(movers, limit=8))
        text.append(f"\n{unchanged} unchanged · {unreachable} unreachable", style=laws.STEEL_DIM)
        return text

    def _survey_result(
        self, total: int, movers: list[tuple[KnifeView, float]], unchanged: int, unreachable: int,
    ) -> Text:
        text = Text()
        text.append(f"survey complete — {total} listings read\n\n", style=laws.PASS)
        if movers:
            text.append_text(self._movers_lines(movers, limit=14))
        else:
            text.append("no price moved\n", style=laws.STEEL_DIM)
        text.append(f"\n{len(movers)} moved · {unchanged} unchanged · {unreachable} unreachable", style=laws.STEEL_DIM)
        return text

    def _movers_lines(self, movers: list[tuple[KnifeView, float]], limit: int) -> Text:
        text = Text()
        for knife, delta in sorted(movers, key=lambda m: -abs(m[1]))[:limit]:
            down = delta < 0
            text.append("▼ " if down else "▲ ", style=laws.PASS if down else laws.FAIL)
            text.append(f"{knife.display_name[:24]:<25}", style=laws.STEEL_BRIGHT)
            text.append(f"{'-' if down else '+'}${abs(delta):,.2f}\n", style=laws.ACCENT)
        return text
