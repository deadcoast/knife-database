"""The Forge Line — the intake room.

Paste a supported retailer URL into the intake slot and the vault does its
own research, visibly: a blank Plate appears at EXTRACT and the listing's
actually-parsed fields stamp on as they arrive; the plate travels to LEGAL
SCREEN where the database's prohibited-mechanism rulebook executes — each
gate genuinely evaluates the listing text, and a hit slams the gate and
stamps the plate REJECTED; a cleared plate travels on and files into the
real database, appearing in the Rack immediately.

`r` replays a deterministic transit on an existing record (no network) so
the motion itself can be judged identically anytime.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from .. import scrape
from ..store import make_knife_id
from . import laws
from .masthead import Masthead
from .plate import Plate

if TYPE_CHECKING:
    from .app import KnivvesVault

PLATE_HEIGHT = 12  # cells reserved beneath the stations for the traveling plate

# Keywords that make a rulebook line trip on a listing title. Deliberately
# precise: "assisted opening" is legal and must never trip a gate.
RULE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "automatic switchblade": ("switchblade", "automatic knife"),
    "OTF automatic": ("otf",),
    "gravity knife": ("gravity knife",),
    "balisong": ("balisong",),
    "butterfly knife": ("butterfly",),
    "explicit centrifugal/flick knife": ("centrifugal", "flick knife"),
    "button/spring/device in handle that automatically opens the blade": (
        "auto opening", "push button open",
    ),
}


class ForgeScreen(Screen):
    AUTO_FOCUS = ""  # the intake slot is entered by click, not by default
    BINDINGS = [("r", "replay", "Replay demo transit")]

    def compose(self) -> ComposeResult:
        yield Masthead("THE FORGE LINE")
        yield Input(
            placeholder="paste a retailer listing URL — enter runs the line  ·  bladescanada.com / houseofknives.ca",
            id="forge-intake",
        )
        with Horizontal(id="forge-line"):
            with Vertical(classes="station", id="st-extract"):
                yield Static("EXTRACT", classes="station-name")
                yield Static("", id="extract-log", classes="station-body")
            with Vertical(classes="station", id="st-legal"):
                yield Static("LEGAL SCREEN", classes="station-name")
                yield Static("", id="gates", classes="station-body")
            with Vertical(classes="station", id="st-vault"):
                yield Static("VAULT", classes="station-name")
                yield Static("", id="filed", classes="station-body")
        yield Plate(id="forge-plate")
        yield Footer()

    @property
    def vault(self) -> "KnivvesVault":
        return cast("KnivvesVault", self.app)

    def on_mount(self) -> None:
        self.query_one(Masthead).update_stats(self.vault.knives)
        self.run_worker(self.demo_transit(), exclusive=True)

    def action_replay(self) -> None:
        self.run_worker(self.demo_transit(), exclusive=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        url = event.value.strip()
        if url:
            event.input.value = ""
            self.set_focus(None)  # free the room keys the moment the line runs
            self.run_worker(self.live_transit(url), exclusive=True)

    # ------------------------------------------------------------- shared

    def _stations(self):
        return (
            self.query_one(Plate),
            self.query_one("#extract-log", Static),
            self.query_one("#gates", Static),
            self.query_one("#filed", Static),
        )

    def _plate_y(self) -> int:
        """Keep the traveling plate above the footer at any terminal height."""
        return max(8, self.size.height - PLATE_HEIGHT - 5)

    def _reset_line(self, plate: Plate) -> None:
        for selector in ("#extract-log", "#gates", "#filed"):
            self.query_one(selector, Static).update("")
        plate.styles.offset = (4, self._plate_y())

    def _rules(self) -> list[str]:
        rule = self.vault.db.get("workflow_rules", {}).get("canadian_online_retailer_rule", {})
        return list(rule.get("only_reject_or_fail_if_clear_prohibited_mechanism", []))

    def _render_gates(
        self,
        passed: list[str],
        checking: str | None = None,
        failed: tuple[str, list[str]] | None = None,
    ) -> Text:
        text = Text()
        for rule in passed:
            text.append("  ✓  ", style=laws.PASS)
            text.append(f"{rule}\n", style=laws.STEEL_DIM)
        if checking:
            text.append("  ── ", style=laws.ACCENT)
            text.append(f"{checking}\n", style=laws.STEEL_MID)
        if failed:
            rule, hits = failed
            text.append("  ✗  ", style=laws.FAIL)
            text.append(f"{rule}\n", style=laws.FAIL)
            text.append(f"     listing matched: {', '.join(hits)}\n", style=laws.STEEL_DIM)
        return text

    async def _travel_to(self, station_id: str, plate: Plate) -> None:
        x = self.query_one(f"#{station_id}").region.x + 2
        laws.travel(plate, x, self._plate_y())
        await asyncio.sleep(laws.TRAVEL_DURATION + 0.15)

    # ---------------------------------------------------------- live intake

    def _already_filed(self, url: str) -> str | None:
        for knife in self.vault.knives:
            if knife.source_input == url:
                return knife.id
            for retailer in knife.retailers:
                if retailer.get("url") == url:
                    return knife.id
        return None

    def _record_from(self, listing: scrape.Listing) -> dict:
        today = date.today().isoformat()
        price = listing.price_cad
        brand = listing.brand or "Unknown"
        model = listing.model or listing.listing_title or "Unknown"
        assist = "assisted" if listing.assisted else ("manual" if listing.opening_method else "unknown")
        return {
            "id": make_knife_id(brand, model),
            "brand": brand,
            "model": model,
            "user_classification": None,
            "user_tags": ["affordable"] if price is not None and price < 150 else [],
            "research_status": "canadian_retailer_verified",
            "acquisition_status": "approved_for_further_research",
            "mechanism": {
                "opening_method": listing.opening_method,
                "lock_type": listing.lock_type,
                "assist_type": assist,
                "blade_length": listing.blade_length,
                "blade_steel": listing.blade_steel,
                "clear_prohibited_mechanism_found": False,
            },
            "canadian_online_retailers": [{
                "retailer": listing.retailer,
                "url": listing.url,
                "listed_price_cad": price,
                "availability": listing.availability,
                "source_date": today,
            }],
            "source_input": listing.url,
            "listing_title": listing.listing_title,
            "price_history": (
                [{"date": today, "price_cad": price}] if price is not None else []
            ),
            "notes": f"Filed via Forge Line intake {today}.",
        }

    async def live_transit(self, url: str) -> None:
        plate, extract_log, gates, filed = self._stations()
        self._reset_line(plate)
        plate.begin("INCOMING", url.split("//")[-1][:42])

        duplicate = self._already_filed(url)
        if duplicate:
            extract_log.update(Text(f"already in the vault: {duplicate}", style=laws.ACCENT))
            plate.begin("DUPLICATE", duplicate)
            return

        extract_log.update(Text("fetching listing…", style=laws.STEEL_DIM))
        try:
            listing = await asyncio.to_thread(scrape.fetch_listing, url)
        except scrape.ScrapeError as exc:
            extract_log.update(Text(str(exc), style=laws.FAIL))
            plate.styles.border = ("heavy", laws.FAIL)
            return

        plate.begin(listing.listing_title[:42] or "UNTITLED LISTING", listing.url.split("//")[-1][:42])
        stamps = listing.stamped_fields()
        for label, value in stamps:
            plate.stamp(label, value)
            await asyncio.sleep(0.35)
        extract_log.update(Text(f"{len(stamps)} fields parsed", style=laws.PASS))

        await self._travel_to("st-legal", plate)

        title_lower = listing.listing_title.lower()
        passed: list[str] = []
        for rule in self._rules():
            gates.update(self._render_gates(passed, checking=rule))
            await asyncio.sleep(0.3)
            hits = [kw for kw in RULE_KEYWORDS.get(rule, (rule.lower(),)) if kw in title_lower]
            if hits:
                gates.update(self._render_gates(passed, failed=(rule, hits)))
                plate.styles.border = ("heavy", laws.FAIL)
                plate.stamp("verdict", f"REJECTED — {rule}")
                filed.update(Text("not filed — prohibited mechanism identified", style=laws.FAIL))
                return
            passed.append(rule)
        done = self._render_gates(passed)
        done.append("\n  CLEAR TO PROCEED", style=laws.PASS)
        gates.update(done)
        await asyncio.sleep(0.5)

        await self._travel_to("st-vault", plate)
        view = self.vault.file_record(self._record_from(listing))
        landed = Text()
        landed.append(f"{view.display_name}\n", style=laws.STEEL_BRIGHT)
        landed.append(f"filed · {view.id}\n", style=laws.STEEL_DIM)
        landed.append("now in the rack · awaiting review", style=laws.STEEL_DIM)
        filed.update(landed)
        self.query_one(Masthead).update_stats(self.vault.knives)

    # ---------------------------------------------------------- demo transit

    def _sample(self):
        knives = self.vault.knives
        return next((k for k in knives if k.price and k.blade_steel != "Unknown"), knives[0])

    async def demo_transit(self) -> None:
        knife = self._sample()
        plate, extract_log, gates, filed = self._stations()
        self._reset_line(plate)
        plate.begin("INCOMING", "")
        extract_log.update(Text("reading listing…", style=laws.STEEL_DIM))
        await asyncio.sleep(0.6)

        plate.begin(knife.display_name, knife.id)
        best = knife.best_retailer or {}
        stamps = [
            ("source", str(best.get("retailer") or "—")),
            ("brand", knife.brand),
            ("model", knife.model),
            ("steel", knife.blade_steel),
            ("price", knife.price_label),
        ]
        for label, value in stamps:
            plate.stamp(label, value)
            await asyncio.sleep(0.45)
        extract_log.update(Text(f"{len(stamps)} fields parsed", style=laws.PASS))

        await self._travel_to("st-legal", plate)
        passed: list[str] = []
        for rule in self._rules():
            gates.update(self._render_gates(passed, checking=rule))
            await asyncio.sleep(0.35)
            passed.append(rule)
        done = self._render_gates(passed)
        done.append("\n  CLEAR TO PROCEED", style=laws.PASS)
        gates.update(done)
        await asyncio.sleep(0.6)

        await self._travel_to("st-vault", plate)
        landed = Text()
        landed.append(f"{knife.display_name}\n", style=laws.STEEL_BRIGHT)
        landed.append("demo transit · nothing was written", style=laws.STEEL_DIM)
        filed.update(landed)
