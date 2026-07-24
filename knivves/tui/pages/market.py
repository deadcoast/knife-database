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
from functools import partial
from typing import TYPE_CHECKING, Callable, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Footer, Static

from ... import ledger, scrape
from ...models import KnifeView, knife_views
from ...store import save_database
from .. import laws
from ..gauges import GradientBars, MeterBar, PriceScale
from ..masthead import Masthead
from ..surfaces import Engraving
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

if TYPE_CHECKING:
    from .app import KnivvesApp

BAR_WIDTH = 22
SUPPORTED = scrape.SUPPORTED_HOSTS


class MarketScreen(TipsMixin, Screen):
    CSS_PATH = "market.tcss"

    BINDINGS = [
        ("s", "survey", "Update prices"),
        ("escape", "cancel_survey", "Cancel price read"),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("market prices — the collection's money"),
        "ledger-valuation": Tip(
            "the collection's financial shape",
            "value sums each knife's best price ·\nthe histogram is the price\ndistribution across the collection",
        ),
        "ledger-line": Tip(
            "the $150 affordable rule, visualized",
            "affordable is the only auto tag —\nassigned when a knife's best price\nsits under $150\n\n"
            "▾ under the line · ▴ within reach\n\nsurveys re-tag line-crossers\nautomatically",
        ),
        "ledger-movers": Tip(
            "s surveys every live listing",
            "each survey appends to every\nrecord's price history ·\nmovers sort by magnitude\n\n"
            "▼ drop (good for buyers) · ▲ rise\n\nesc cancels — observations made\nbefore the cancel are kept",
        ),
    }

    SURVEY_DELAY = 0.25  # politeness between fetches; tests set 0

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._surveying = False

    def compose(self) -> ComposeResult:
        yield Masthead("MARKET PRICES")
        with Horizontal(id="ledger"):
            with Vertical(classes="station", id="ledger-valuation") as valuation_pane:
                valuation_pane.border_title = "VALUATION"
                yield Static("", id="valuation-read", classes="station-body")
                yield PriceScale(id="price-scale")
                yield GradientBars(id="price-bars")
                yield Engraving("heaviest holdings")
                yield Static("", id="valuation-top", classes="station-body")
            with Vertical(id="ledger-right"):
                with Vertical(classes="station", id="ledger-line") as line_pane:
                    line_pane.border_title = "THE $150 LINE"
                    yield Static("", id="line-read", classes="station-body")
                with Vertical(classes="station", id="ledger-movers") as survey_pane:
                    survey_pane.border_title = "MARKET SURVEY"
                    yield MeterBar("history", id="meter-history")
                    yield MeterBar("priced", id="meter-priced")
                    yield Static("", id="movers-read", classes="station-body")
            yield TipRail()
        yield TipCapsule()
        yield Footer()

    @property
    def knivves(self) -> "KnivvesApp":
        return cast("KnivvesApp", self.app)

    def on_mount(self) -> None:
        self._reveal = laws.Reveal(self)

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.query_one(Masthead).update_stats(self.knivves.knives)
        self.show_room_tip()
        self._read_valuation()
        self._read_line()
        if not self._surveying:
            self._idle_movers()
            self.query_one(Masthead).set_context(self._survey_status())
            self.query_one("#ledger-movers").border_subtitle = self._survey_status()
        self._power_on()
        # panes measure short before first layout — re-cut the lists once
        # real heights exist so they fill the room they actually have
        def _recut() -> None:
            self._read_line()
            if not self._surveying:
                self._idle_movers()

        self.set_timer(0.15, _recut)

    def on_screen_suspend(self, event) -> None:
        self._reveal.arm()

    def _power_on(self) -> None:
        """REVEAL — the price scale draws itself left to right; the avg
        needle, the endpoints, and the $150 line cut in last."""
        scale = self.query_one(PriceScale)
        steps: list[tuple[float, Callable[[], None]]] = [(0.0, scale.begin_reveal)]
        n = 10
        for i in range(1, n + 1):
            steps.append((0.25 + 0.55 * (i / n) ** 0.5, partial(scale.reveal_step, i / n)))
        steps.append((laws.REVEAL_SETTLE, scale.end_reveal))
        self._reveal.play(steps)

    def _survey_status(self) -> str:
        """Idle readout: when the market was last read, if ever."""
        dates = [
            str(r.get("source_date"))
            for k in self.knivves.knives
            if len(k.raw.get("price_history") or []) > 1
            for r in k.retailers
            if r.get("source_date")
        ]
        return f"last survey {max(dates)}" if dates else "no survey on record"

    # ------------------------------------------------------------- panels

    def _read_valuation(self) -> None:
        knives = self.knivves.knives
        v = ledger.vault_valuation(knives)
        prices = sorted(k.price for k in knives if k.price is not None)
        median = prices[len(prices) // 2] if prices else 0.0
        text = Text()
        for label, value, style in (
            ("value", f"${v['total']:,.0f} CAD", laws.ACCENT),
            ("priced", f"{v['priced']} of {len(knives)}", laws.STEEL_BRIGHT),
            ("average", f"${v['average']:,.2f}", laws.STEEL_BRIGHT),
            ("median", f"${median:,.2f}", laws.STEEL_BRIGHT),
            ("afford.", f"{v['affordable']} under the line", laws.PASS),
        ):
            text.append_text(laws.field(label, value, style))
            text.append("\n")
        self.query_one("#valuation-read", Static).update(text)
        self.query_one(PriceScale).update_scale(prices, ledger.AFFORDABLE_THRESHOLD_CAD)
        self.query_one(GradientBars).update_bars(ledger.price_buckets(knives))
        heaviest = sorted(
            (k for k in knives if k.price is not None), key=lambda k: -k.price
        )[:6]
        top = Text()
        for knife in heaviest:
            name = knife.display_name
            name = name[:21] + "…" if len(name) > 22 else name
            top.append(f"{name:<23}", style=laws.STEEL_BRIGHT)
            top.append(f"{'$' + format(knife.price, ',.0f'):>9}\n", style=laws.ACCENT)
        self.query_one("#valuation-top", Static).update(top)
        self.query_one("#ledger-valuation").border_subtitle = f"{v['priced']} priced"

    def _read_line(self) -> None:
        """The $150 line drawn as a two-sided ladder: blades over the line
        descending onto it, the amber rule cut across the panel, blades
        under it hanging below — the rule as geography, not a list."""
        threshold = ledger.AFFORDABLE_THRESHOLD_CAD
        near = ledger.near_the_line(self.knivves.knives)
        above = sorted((k for k in near if (k.price or 0) >= threshold), key=lambda k: k.price or 0, reverse=True)
        below = sorted((k for k in near if (k.price or 0) < threshold), key=lambda k: k.price or 0, reverse=True)

        def rung(text: Text, knife, over: bool) -> None:
            price = knife.price or 0
            distance = abs(price - threshold)
            name = knife.display_name
            name = name[:25] + "…" if len(name) > 26 else name
            text.append(" ▴ " if over else " ▾ ", style=laws.STEEL_MID if over else laws.PASS)
            text.append(f"{name:<27}", style=laws.STEEL_BRIGHT)
            text.append(f"{price:>5,.0f}", style=laws.ACCENT)
            text.append(f"  Δ${distance:,.0f}\n", style=laws.STEEL_DIM)

        knives = self.knivves.knives
        over_count = sum(1 for k in knives if (k.price or 0) >= threshold and k.price is not None)
        under_count = sum(1 for k in knives if k.price is not None and k.price < threshold)
        # the ladder grows with the room — rungs fill the pane's real
        # CONTENT height (size excludes border and padding)
        pane_h = self.query_one("#ledger-line").size.height or 14
        per_side = max(4, (pane_h - 4) // 2)
        text = Text()
        text.append(f"the rule re-tags at ${threshold:,.0f}", style=laws.STEEL_DIM)
        text.append(f"   ▴ {over_count} priced over · ▾ {under_count} under\n\n", style=laws.STEEL_DIM)
        if not above:
            text.append("   nothing riding above the line\n", style=laws.STEEL_DIM)
        for knife in above[:per_side]:
            rung(text, knife, over=True)
        text.append("━━━━━━━ ", style=laws.ACCENT)
        text.append(f"${threshold:,.0f}", style=f"bold {laws.ACCENT}")
        text.append(" ━" + "━" * 28 + "\n", style=laws.ACCENT)
        for knife in below[:per_side]:
            rung(text, knife, over=False)
        if not below:
            text.append("   nothing hanging under the line\n", style=laws.STEEL_DIM)
        self.query_one("#line-read", Static).update(text)
        self.query_one("#ledger-line").border_subtitle = (
            f"{len(near)} knives within ${ledger.NEAR_LINE_BAND_CAD:,.0f} of the line"
        )
        knives = self.knivves.knives
        blades = max(len(knives), 1)
        deep = sum(1 for k in knives if len(k.raw.get("price_history") or []) > 1)
        priced = sum(1 for k in knives if k.price is not None)
        self.query_one("#meter-history", MeterBar).set_meter(deep / blades, f"{deep}/{len(knives)}")
        self.query_one("#meter-priced", MeterBar).set_meter(priced / blades, f"{priced}/{len(knives)}")

    def _history_movers(self) -> list[tuple[KnifeView, float]]:
        """The last survey's movement, read straight from the records —
        the delta between each knife's final two history entries."""
        movers: list[tuple[KnifeView, float]] = []
        for knife in self.knivves.knives:
            history = knife.raw.get("price_history") or []
            if len(history) < 2:
                continue
            try:
                prev, last = float(history[-2]["price_cad"]), float(history[-1]["price_cad"])
            except (KeyError, TypeError, ValueError):
                continue
            if last != prev:
                movers.append((knife, last - prev))
        return sorted(movers, key=lambda m: -abs(m[1]))

    def _idle_movers(self) -> None:
        surveyed = any(len(k.raw.get("price_history") or []) > 1 for k in self.knivves.knives)
        targets = len(self._targets())
        pane_h = self.query_one("#ledger-movers").size.height or 16
        text = Text()
        text.append_text(laws.field("last read", self._survey_status().replace("last survey ", ""), laws.STEEL_BRIGHT))
        text.append("\n")
        text.append_text(laws.field("reachable", f"{targets} live listings", laws.STEEL_BRIGHT))
        text.append("\n")
        text.append_text(laws.field("hosts", " · ".join(sorted(SUPPORTED))[:40], laws.STEEL_DIM))
        text.append("\n\n")
        text.append(" s ", style=f"bold {laws.BG} on {laws.ACCENT}")
        if surveyed:
            text.append("  runs a fresh survey · esc cancels\n\n", style=laws.STEEL_MID)
            movers = self._history_movers()
            if movers:
                text.append("what the last survey moved:\n", style=laws.STEEL_DIM)
                text.append_text(self._movers_lines(movers, limit=max(6, pane_h - 9)))
            else:
                text.append("no price moved on the last survey\n", style=laws.STEEL_DIM)
        else:
            text.append("  reads every live listing and\n    records what moved\n\n", style=laws.STEEL_MID)
            text.append("each survey appends to every\nrecord's price history — movers\nland here, sorted by magnitude\n", style=laws.STEEL_DIM)
            text.append("\nesc cancels · observations kept", style=laws.STEEL_DIM)
        self.query_one("#movers-read", Static).update(text)

    def on_resize(self, event) -> None:
        """The instruments re-cut to the room's real size."""
        if not self._surveying:
            self._read_valuation()
            self._read_line()
            self._idle_movers()

    # ------------------------------------------------------------- survey

    def action_survey(self) -> None:
        if not self._surveying:
            self._reveal.settle()
            self.run_worker(self.survey(), exclusive=True)

    def action_cancel_survey(self) -> None:
        if self.dismiss_capsule():
            return
        if self._surveying:
            self.workers.cancel_all()

    def _targets(self) -> list[KnifeView]:
        out = []
        for knife in self.knivves.knives:
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
        raw_by_id = {k.get("id"): k for k in self.knivves.db.get("knives", []) if isinstance(k, dict)}
        cancelled = False
        try:
            for i, knife in enumerate(targets, start=1):
                movers_read.update(self._survey_frame(i, len(targets), knife, movers, unchanged, unreachable))
                self.query_one(Masthead).set_context(f"surveying {i}/{len(targets)}")
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
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            # keep whatever was observed, even on cancel
            save_database(self.knivves.db, self.knivves.db_path)
            self.knivves.knives = knife_views(self.knivves.db)
            self._surveying = False
            self.query_one(Masthead).update_stats(self.knivves.knives)
            self._read_valuation()
            self._read_line()
            movers_read.update(self._survey_result(len(targets), movers, unchanged, unreachable))
            self.query_one(Masthead).set_context(
                "survey stopped — observations kept"
                if cancelled
                else f"survey complete · {len(movers)} moved"
            )

    def _survey_frame(
        self, i: int, total: int, knife: KnifeView,
        movers: list[tuple[KnifeView, float]], unchanged: int, unreachable: int,
    ) -> Text:
        pane_h = self.query_one("#ledger-movers").size.height or 20
        text = Text()
        text.append(f"surveying {i}/{total}\n", style=laws.ACCENT)
        text.append(f"{knife.display_name[:28]}\n\n", style=laws.STEEL_MID)
        text.append_text(self._movers_lines(movers, limit=max(8, pane_h - 9)))
        text.append(f"\n{unchanged} unchanged · {unreachable} unreachable", style=laws.STEEL_DIM)
        return text

    def _survey_result(
        self, total: int, movers: list[tuple[KnifeView, float]], unchanged: int, unreachable: int,
    ) -> Text:
        pane_h = self.query_one("#ledger-movers").size.height or 20
        text = Text()
        text.append(f"survey complete — {total} listings read\n\n", style=laws.PASS)
        if movers:
            text.append_text(self._movers_lines(movers, limit=max(10, pane_h - 8)))
        else:
            text.append("no price moved\n", style=laws.STEEL_DIM)
        text.append(f"\n{len(movers)} moved · {unchanged} unchanged · {unreachable} unreachable", style=laws.STEEL_DIM)
        return text

    def _movers_lines(self, movers: list[tuple[KnifeView, float]], limit: int) -> Text:
        text = Text()
        for knife, delta in sorted(movers, key=lambda m: -abs(m[1]))[:limit]:
            down = delta < 0
            name = knife.display_name
            name = name[:17] + "…" if len(name) > 18 else name
            text.append("▼ " if down else "▲ ", style=laws.PASS if down else laws.FAIL)
            text.append(f"{name:<19}", style=laws.STEEL_BRIGHT)
            text.append(f"{'-' if down else '+'}${abs(delta):,.2f}\n", style=laws.ACCENT)
        return text
