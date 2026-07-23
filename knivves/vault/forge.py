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
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from .. import ingest, scrape
from ..models import knife_views
from ..store import backup_database, make_knife_id, save_database
from . import laws
from .masthead import Masthead
from .surfaces import Engraving
from .plate import Plate
from .tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

if TYPE_CHECKING:
    from .app import KnivvesVault

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

# Gate labels: the rulebook's legal prose, machined down to stamps.
# Full wording remains in the database and the legal-screen tip capsule.
RULE_DISPLAY: dict[str, str] = {
    "automatic switchblade": "AUTOMATIC / SWITCHBLADE",
    "OTF automatic": "OTF AUTOMATIC",
    "gravity knife": "GRAVITY",
    "balisong": "BALISONG",
    "butterfly knife": "BUTTERFLY",
    "explicit centrifugal/flick knife": "CENTRIFUGAL / FLICK",
    "button/spring/device in handle that automatically opens the blade": "AUTO-OPENING DEVICE",
}


class ForgeScreen(TipsMixin, Screen):
    AUTO_FOCUS = ""  # the intake slot is entered by click, not by default
    BINDINGS = [
        ("r", "replay", "Replay demo transit"),
        ("escape", "dismiss_tip", "", ),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("import knives — records are made here"),
        "forge-intake": Tip(
            "a listing url or an ingestion .md · enter runs the line",
            "url intake:\n  bladescanada.com · houseofknives.ca\n  fields stamp as they parse ·\n"
            "  the legal gates read the db's\n  own rulebook\n\n"
            "file intake:\n  a path to an ingestion ledger —\n  sections read, the plan screens,\n  new knives file ★new in a batch\n\n"
            "duplicates are refused either way",
        ),
        "st-extract": Tip("the listing is read and stamped here"),
        "st-legal": Tip(
            "gates execute the db's rulebook",
            "the seven gates:\n  AUTOMATIC / SWITCHBLADE\n  OTF AUTOMATIC\n  GRAVITY\n  BALISONG\n"
            "  BUTTERFLY\n  CENTRIFUGAL / FLICK\n  AUTO-OPENING DEVICE\n\n"
            "'assisted opening' is legal and\nnever trips a gate\n\n"
            "a hit slams the gate, stamps the\nplate REJECTED — nothing is written",
        ),
        "st-vault": Tip("cleared records file here — for real"),
    }

    def action_dismiss_tip(self) -> None:
        self.dismiss_capsule()

    def compose(self) -> ComposeResult:
        yield Masthead("IMPORT KNIVES")
        yield Input(
            placeholder="a retailer listing URL or a path to an ingestion .md — enter runs the line",
            id="forge-intake",
        )
        with Horizontal(id="forge-line"):
            with Vertical(classes="station", id="st-extract"):
                yield Engraving("extract")
                yield Static("", id="extract-log", classes="station-body")
            with Vertical(classes="station", id="st-legal"):
                yield Engraving("legal screen")
                yield Static("", id="gates", classes="station-body")
            with Vertical(classes="station", id="st-vault"):
                yield Engraving("vault")
                yield Static("", id="filed", classes="station-body")
            yield TipRail()
        yield Plate(id="forge-plate")
        yield TipCapsule()
        yield Footer()

    @property
    def vault(self) -> "KnivvesVault":
        return cast("KnivvesVault", self.app)

    def on_mount(self) -> None:
        self.query_one(Masthead).update_stats(self.vault.knives)
        self.show_room_tip()
        self.run_worker(self.demo_transit(), exclusive=True)

    def action_replay(self) -> None:
        self.run_worker(self.demo_transit(), exclusive=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip().strip('"')
        if not value:
            return
        event.input.value = ""
        self.set_focus(None)  # free the room keys the moment the line runs
        if value.lower().endswith(".md"):
            self.run_worker(self.file_transit(value), exclusive=True)
        else:
            self.run_worker(self.live_transit(value), exclusive=True)

    # ------------------------------------------------------------- shared

    def _stations(self):
        return (
            self.query_one(Plate),
            self.query_one("#extract-log", Static),
            self.query_one("#gates", Static),
            self.query_one("#filed", Static),
        )

    def _plate_y(self) -> int:
        """Rest the plate against the bottom edge, whatever its grown height."""
        plate = self.query_one(Plate)
        height = plate.outer_size.height or 10
        return max(6, self.size.height - height - 2)

    def _settle(self) -> None:
        """Re-seat the plate after content growth so it never clips."""
        plate = self.query_one(Plate)
        plate.styles.offset = (self._plate_x, self._plate_y())

    def _reset_line(self, plate: Plate) -> None:
        for selector in ("#extract-log", "#gates", "#filed"):
            self.query_one(selector, Static).update("")
        self._plate_x = 4
        self.call_after_refresh(self._settle)

    def on_resize(self, event) -> None:
        """A resized terminal re-seats the plate — it must never clip."""
        if getattr(self, "_plate_x", None) is not None:
            self.call_after_refresh(self._settle)

    def _rules(self) -> list[str]:
        rule = self.vault.db.get("workflow_rules", {}).get("canadian_online_retailer_rule", {})
        return list(rule.get("only_reject_or_fail_if_clear_prohibited_mechanism", []))

    def _line_state(self, text: str) -> None:
        self.query_one(Masthead).set_context(text)

    def _render_gates(
        self,
        passed: list[str],
        checking: str | None = None,
        failed: tuple[str, list[str]] | None = None,
        total: int = 0,
    ) -> Text:
        text = Text()
        if total:
            if failed:
                text.append(f"GATE {len(passed) + 1}/{total} — HALT\n\n", style=laws.FAIL)
            elif checking:
                text.append(f"GATE {len(passed) + 1}/{total}\n\n", style=laws.STEEL_DIM)
            else:
                text.append(f"GATES {len(passed)}/{total}\n\n", style=laws.PASS)
        for rule in passed:
            text.append("  ✓  ", style=laws.PASS)
            text.append(f"{RULE_DISPLAY.get(rule, rule)}\n", style=laws.STEEL_DIM)
        if checking:
            text.append("  ── ", style=laws.ACCENT)
            text.append(f"{RULE_DISPLAY.get(checking, checking)}\n", style=laws.STEEL_MID)
        if failed:
            rule, hits = failed
            text.append("  ✗  ", style=laws.FAIL)
            text.append(f"{RULE_DISPLAY.get(rule, rule)}\n", style=laws.FAIL)
            text.append(f"     listing matched: {', '.join(hits)}\n", style=laws.STEEL_DIM)
        return text

    async def _travel_to(self, station_id: str, plate: Plate) -> None:
        x = self.query_one(f"#{station_id}").region.x + 2
        self._plate_x = x
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
        self._line_state("line: extract ▸")
        plate.begin("INCOMING", url.split("//")[-1][:42])

        duplicate = self._already_filed(url)
        if duplicate:
            extract_log.update(Text(f"already in the vault: {duplicate}", style=laws.ACCENT))
            plate.begin("DUPLICATE", duplicate)
            self._line_state("line: duplicate — nothing to do")
            return

        extract_log.update(Text("fetching listing…", style=laws.STEEL_DIM))
        try:
            listing = await asyncio.to_thread(scrape.fetch_listing, url)
        except scrape.ScrapeError as exc:
            extract_log.update(Text(str(exc), style=laws.FAIL))
            plate.styles.border = ("heavy", laws.FAIL)
            self._line_state("line: fault ✗")
            return

        plate.begin(listing.listing_title[:42] or "UNTITLED LISTING", listing.url.split("//")[-1][:42])
        stamps = listing.stamped_fields()
        for label, value in stamps:
            plate.stamp(label, value)
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.35)
        extract_log.update(Text(f"{len(stamps)} fields parsed", style=laws.PASS))

        self._line_state("line: legal screen ▸")
        await self._travel_to("st-legal", plate)

        title_lower = listing.listing_title.lower()
        rules = self._rules()
        passed: list[str] = []
        for rule in rules:
            gates.update(self._render_gates(passed, checking=rule, total=len(rules)))
            await asyncio.sleep(0.3)
            hits = [kw for kw in RULE_KEYWORDS.get(rule, (rule.lower(),)) if kw in title_lower]
            if hits:
                gates.update(self._render_gates(passed, failed=(rule, hits), total=len(rules)))
                plate.styles.border = ("heavy", laws.FAIL)
                plate.stamp("verdict", f"REJECTED — {RULE_DISPLAY.get(rule, rule)}")
                self.call_after_refresh(self._settle)
                filed.update(Text("not filed — prohibited mechanism identified", style=laws.FAIL))
                self._line_state("line: rejected ✗")
                return
            passed.append(rule)
        done = self._render_gates(passed, total=len(rules))
        done.append("\n  CLEAR TO PROCEED", style=laws.PASS)
        gates.update(done)
        await asyncio.sleep(0.5)

        self._line_state("line: vault ▸")
        await self._travel_to("st-vault", plate)
        view = self.vault.file_record(self._record_from(listing))
        landed = Text()
        landed.append(f"{view.display_name}\n", style=laws.STEEL_BRIGHT)
        landed.append(f"filed · {view.id}\n", style=laws.STEEL_DIM)
        landed.append("now in the rack · awaiting review", style=laws.STEEL_DIM)
        filed.update(landed)
        self._line_state("line: filed ✓")
        self.query_one(Masthead).update_stats(self.vault.knives)

    # ---------------------------------------------------------- file intake

    async def file_transit(self, raw_path: str) -> None:
        """Run an ingestion ledger down the line: sections read at EXTRACT,
        the plan screens at LEGAL SCREEN, the batch files at VAULT."""
        from pathlib import Path as _Path

        plate, extract_log, gates, filed = self._stations()
        self._reset_line(plate)
        self._line_state("line: reading ledger ▸")
        path = _Path(raw_path).expanduser()
        plate.begin("INGESTION LEDGER", path.name[:42])

        if not path.exists():
            extract_log.update(Text(f"no such file: {path}", style=laws.FAIL))
            plate.styles.border = ("heavy", laws.FAIL)
            self._line_state("line: fault ✗")
            return
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            extract_log.update(Text(str(exc), style=laws.FAIL))
            plate.styles.border = ("heavy", laws.FAIL)
            self._line_state("line: fault ✗")
            return

        doc = ingest.parse_document(text)
        if not doc.sections:
            extract_log.update(Text("no SectionIDs found — not an ingestion ledger", style=laws.FAIL))
            plate.styles.border = ("heavy", laws.FAIL)
            self._line_state("line: fault ✗")
            return

        plate.begin((doc.title or "UNTITLED LEDGER")[:42], path.name[:42])
        glyphs = {"buylist": ("⬖", laws.ACCENT), "sources": ("◈", laws.STEEL_MID)}
        log = Text()
        total = 0
        for section in doc.sections:
            plate.stamp(section.slug[:10], f"{len(section.entries)} entries")
            self.call_after_refresh(self._settle)
            glyph, style = glyphs.get(section.kind, ("▤", laws.STEEL_MID))
            log.append(f"{glyph} ", style=style)
            log.append(f"{section.name[:24]:<25}", style=laws.STEEL_BRIGHT)
            log.append(f"{len(section.entries):>4}\n", style=laws.STEEL_DIM)
            total += len(section.entries)
            extract_log.update(log)
            await asyncio.sleep(0.3)
        log.append(f"\n{len(doc.sections)} sections · {total} entries read", style=laws.PASS)
        extract_log.update(log)

        self._line_state("line: the plan screens ▸")
        await self._travel_to("st-legal", plate)
        plan = ingest.build_plan(doc, self.vault.db)
        screen = Text()
        screen.append("THE PLAN\n\n", style=laws.PASS if plan.new_records else laws.STEEL_DIM)
        for label, count, style in (
            ("to file ★new", len(plan.new_records), laws.FRESH),
            ("merge existing", len(plan.merges), laws.STEEL_MID),
            ("duplicates", len(plan.skipped), laws.STEEL_DIM),
            ("buy-list rungs", len(plan.buylist_keys), laws.ACCENT),
            ("sources", len(plan.sources), laws.STEEL_MID),
        ):
            screen.append(f"  {label:<16}", style=laws.STEEL_DIM)
            screen.append(f"{count:>4}\n", style=style if count else laws.STEEL_DIM)
        warnings = sum(1 for d in plan.diagnostics if d.severity == "warning")
        if warnings:
            screen.append(f"\n  {warnings} format warning(s) — parsed anyway", style=laws.ACCENT)
        gates.update(screen)
        await asyncio.sleep(0.7)

        self._line_state("line: filing ▸")
        await self._travel_to("st-vault", plate)
        if not plan.new_records and not plan.merges and not plan.sources:
            filed.update(Text("nothing new — every entry already lives in the vault", style=laws.STEEL_DIM))
            self._line_state("line idle · url, .md, or r")
            return
        backup_database("before-ingest", self.vault.db_path)
        report = ingest.apply_plan(plan, self.vault.db)
        save_database(self.vault.db, self.vault.db_path)
        self.vault.knives = knife_views(self.vault.db)
        landed = Text()
        landed.append(f"{report.added} filed ★new", style=f"bold {laws.FRESH}")
        landed.append(f" · {report.merged} merged\n", style=laws.STEEL_MID)
        landed.append(f"⬖ buy list {report.buylist} deep", style=laws.ACCENT if report.buylist else laws.STEEL_DIM)
        landed.append(f" · {report.sources} sources\n", style=laws.STEEL_DIM)
        if report.repairs:
            landed.append(f"{len(report.repairs)} damaged lines repaired\n", style=laws.STEEL_DIM)
        landed.append("\nnow in the library · knivves update seals the batch", style=laws.STEEL_DIM)
        filed.update(landed)
        self._line_state(f"line: filed {report.added} ✓")
        self.query_one(Masthead).update_stats(self.vault.knives)

    # ---------------------------------------------------------- demo transit

    def _sample(self):
        knives = self.vault.knives
        return next((k for k in knives if k.price and k.blade_steel != "Unknown"), knives[0])

    async def demo_transit(self) -> None:
        knife = self._sample()
        plate, extract_log, gates, filed = self._stations()
        self._reset_line(plate)
        self._line_state("line: demo ▸")
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
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.45)
        extract_log.update(Text(f"{len(stamps)} fields parsed", style=laws.PASS))

        await self._travel_to("st-legal", plate)
        rules = self._rules()
        passed: list[str] = []
        for rule in rules:
            gates.update(self._render_gates(passed, checking=rule, total=len(rules)))
            await asyncio.sleep(0.35)
            passed.append(rule)
        done = self._render_gates(passed, total=len(rules))
        done.append("\n  CLEAR TO PROCEED", style=laws.PASS)
        gates.update(done)
        await asyncio.sleep(0.6)

        await self._travel_to("st-vault", plate)
        landed = Text()
        landed.append(f"{knife.display_name}\n", style=laws.STEEL_BRIGHT)
        landed.append("demo transit · nothing was written", style=laws.STEEL_DIM)
        filed.update(landed)
        invite = Text()
        invite.append(f"{len(stamps)} fields parsed\n", style=laws.PASS)
        invite.append("paste a url above for a real intake", style=laws.STEEL_DIM)
        extract_log.update(invite)
        self._line_state("line idle · url, .md, or r")
