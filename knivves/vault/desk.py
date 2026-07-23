"""The Research Desk — the room where the vault researches its own unknowns.

The docket lists every incomplete record in the order it deserves —
BuyList rank first, then ★new, then most-gaps-first — with the
unreachable shelf below it, every absence given its reason. `s` works
the docket for real: each record's plate is PULLED from the docket,
its listing is READ, and only its empty fields STAMP on — the
fill-only-empty law executing visibly, one field at a time, while the
completeness meter rises. `r` replays a deterministic no-network demo
so the motion can be judged anytime. Nothing here ever overwrites user
data, and a rulebook hit is reported on the stamp log — never written.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Footer, Static

from .. import research, scrape
from ..models import KnifeView, knife_views
from ..store import backup_database, save_database
from . import laws
from .gauges import EIGHTHS, _lerp
from .masthead import Masthead
from .plate import Plate
from .surfaces import Engraving
from .tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

if TYPE_CHECKING:
    from .app import KnivvesVault

FETCH_TIMEOUT = 12.0

# How a filled field reads on the plate, from the record it landed in.
FIELD_READERS = {
    "title": lambda k: k.display_name,
    "brand": lambda k: k.brand,
    "model": lambda k: k.model,
    "listing_title": lambda k: k.raw.get("listing_title") or "—",
    "steel": lambda k: k.blade_steel,
    "lock": lambda k: k.lock_type,
    "opening": lambda k: k.opening_method,
    "length": lambda k: k.blade_length,
    "price": lambda k: k.price_label,
    "availability": lambda k: str((k.best_retailer or {}).get("availability") or "—"),
}


class CompletenessMeter(Widget):
    """Drawn instrument: vault completeness as a machined bar, gradient-lit
    toward its tip with eighth-block sub-cell precision — every mark on it
    a real count from the database."""

    DEFAULT_CSS = """
    CompletenessMeter {
        height: 1;
        margin: 0 4;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._complete = 0
        self._records = 0

    def set_counts(self, complete: int, records: int) -> None:
        self._complete = complete
        self._records = records
        self.refresh()

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0 or y > 0 or self._records == 0:
            return Strip([])
        fraction = self._complete / self._records
        label = f"COMPLETE {self._complete}/{self._records} "
        pct = f" {fraction * 100:.0f}%"
        bar_span = max(width - len(label) - len(pct) - 1, 8)
        exact = fraction * bar_span
        full = int(exact)
        frac = exact - full
        segments = [Segment(label, Style(color=laws.STEEL_DIM))]
        for i in range(full):
            segments.append(Segment(" ", Style(bgcolor=_lerp(i / max(bar_span - 1, 1)))))
        used = full
        if frac >= 0.125 and full < bar_span:
            glyph = EIGHTHS[int(frac * 8) - 1]
            segments.append(Segment(glyph, Style(color=_lerp(full / max(bar_span - 1, 1)), bgcolor=laws.EDGE)))
            used += 1
        if used < bar_span:
            segments.append(Segment(" " * (bar_span - used), Style(bgcolor=laws.EDGE)))
        segments.append(Segment(pct, Style(color=laws.ACCENT if fraction < 1 else laws.PASS)))
        return Strip(segments, width)


class DeskScreen(TipsMixin, Screen):
    BINDINGS = [
        ("s", "start_pass", "Research the docket"),
        ("r", "replay", "Replay demo"),
        ("escape", "dismiss_tip", ""),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("research — the vault fills its own unknowns"),
        "st-docket": Tip(
            "the docket — who is next, and why",
            "ordered by law:\n  buy-list rank first,\n  then ★new,\n  then most gaps\n\n"
            "the unreachable shelf:\n  no supported listing —\n  kept and said,\n  never skipped silently",
        ),
        "st-read": Tip("read — the record's own listing, learned"),
        "st-stamp": Tip(
            "stamp — only empty fields land",
            "fill-only-empty law:\n  user data is never\n  overwritten\n\n"
            "rulebook hits are\nreported on the log —\nthe flag stays yours",
        ),
    }

    def action_dismiss_tip(self) -> None:
        self.dismiss_capsule()

    def compose(self) -> ComposeResult:
        yield Masthead("RESEARCH")
        yield CompletenessMeter(id="desk-meter")
        with Horizontal(id="desk-line"):
            with Vertical(classes="station", id="st-docket"):
                yield Engraving("the docket")
                yield Static("", id="docket", classes="station-body")
            with Vertical(classes="station", id="st-read"):
                yield Engraving("read")
                yield Static("", id="read-log", classes="station-body")
            with Vertical(classes="station", id="st-stamp"):
                yield Engraving("stamp")
                yield Static("", id="stamped", classes="station-body")
            yield TipRail()
        yield Plate(id="desk-plate")
        yield TipCapsule()
        yield Footer()

    @property
    def vault(self) -> "KnivvesVault":
        return cast("KnivvesVault", self.app)

    def on_mount(self) -> None:
        self.query_one(Masthead).update_stats(self.vault.knives)
        self.show_room_tip()
        self._refresh_desk()
        self.run_worker(self.demo_transit(), exclusive=True)

    def action_replay(self) -> None:
        self.run_worker(self.demo_transit(), exclusive=True)

    def action_start_pass(self) -> None:
        self.run_worker(self.live_pass(), exclusive=True)

    # ------------------------------------------------------------- the desk

    def _line_state(self, text: str) -> None:
        self.query_one(Masthead).set_context(text)

    def _plate_y(self) -> int:
        plate = self.query_one(Plate)
        height = plate.outer_size.height or 10
        return max(6, self.size.height - height - 2)

    def _settle(self) -> None:
        plate = self.query_one(Plate)
        plate.styles.offset = (self._plate_x, self._plate_y())

    def _reset_line(self, plate: Plate) -> None:
        for selector in ("#read-log", "#stamped"):
            self.query_one(selector, Static).update("")
        self._plate_x = 4
        self.call_after_refresh(self._settle)

    def on_resize(self, event) -> None:
        if getattr(self, "_plate_x", None) is not None:
            self.call_after_refresh(self._settle)

    async def _travel_to(self, station_id: str, plate: Plate) -> None:
        x = self.query_one(f"#{station_id}").region.x + 2
        self._plate_x = x
        laws.travel(plate, x, self._plate_y())
        await asyncio.sleep(laws.TRAVEL_DURATION + 0.15)

    def _refresh_desk(self) -> None:
        """The docket, the shelf, and the meter — all from one audit."""
        db = self.vault.db
        plan = research.run_research(db, dry_run=True)
        audit = research.audit_database(db)
        self.query_one("#desk-meter", CompletenessMeter).set_counts(audit.complete, audit.records)
        self.query_one("#docket", Static).update(self._docket_text(plan))
        self._line_state(f"desk: {len(plan.planned)} on the docket · {audit.complete}/{audit.records} complete")

    def _docket_text(self, plan: research.PassSummary) -> Text:
        # one line per record — the engraving names the station, the
        # masthead and meter carry the counts; ×N is the gap count
        text = Text()
        if plan.planned:
            for rank, entry in enumerate(plan.planned[:10], start=1):
                text.append(f"{rank:>2} ", style=laws.ACCENT)
                if entry.buy_priority:
                    text.append(f"⬖{entry.buy_priority} ", style="bold magenta")
                if entry.is_new:
                    text.append("★ ", style=laws.FRESH)
                text.append(f"{entry.knife_id[:22]:<23}", style=laws.STEEL_BRIGHT)
                text.append(f"×{len(entry.gaps)}\n", style=laws.STEEL_DIM)
            if len(plan.planned) > 10:
                text.append(f"   +{len(plan.planned) - 10} deeper\n", style=laws.STEEL_DIM)
        else:
            text.append("fully researched — no open gaps\nwith a supported listing\n", style=laws.PASS)
        if plan.unreachable:
            text.append(f"\nUNREACHABLE  {len(plan.unreachable)}\n", style=f"bold {laws.STEEL_DIM}")
            for entry in plan.unreachable[:4]:
                text.append(f" {entry.knife_id[:26]:<27}", style=laws.STEEL_MID)
                text.append(f"×{len(entry.gaps)}\n", style=laws.STEEL_DIM)
                text.append(f"   {entry.reason[:30]}\n", style=laws.STEEL_DIM)
            if len(plan.unreachable) > 4:
                text.append(f" +{len(plan.unreachable) - 4} more on the shelf\n", style=laws.STEEL_DIM)
        return text

    # ------------------------------------------------------------ live pass

    async def live_pass(self) -> None:
        db = self.vault.db
        plan = research.run_research(db, dry_run=True)
        if not plan.planned:
            self._refresh_desk()
            self._line_state("desk: nothing to research ✓")
            return
        rules = research.rulebook(db)
        by_id = {str(r.get("id")): r for r in db.get("knives") or [] if isinstance(r, dict)}
        plate = self.query_one(Plate)
        self._reset_line(plate)
        filled_total = 0
        worked = 0
        hits: list[tuple[str, str]] = []
        for entry in plan.planned:
            report = await self._work_one(entry, by_id[entry.knife_id], rules, plate)
            if report is None:
                continue
            worked += 1
            filled_total += len(report.filled)
            hits.extend((report.knife_id, rule) for rule, _ in report.rulebook_hits)
        if filled_total:
            backup_database("before-research", self.vault.db_path)
            save_database(db, self.vault.db_path)
            self.vault.knives = knife_views(db)
        stamped = self.query_one("#stamped", Static)
        summary = Text()
        summary.append(f"{worked} records researched\n", style=laws.STEEL_BRIGHT)
        summary.append(f"{filled_total} fields filled — only empty ones\n", style=laws.PASS if filled_total else laws.STEEL_DIM)
        for rid, rule in hits:
            summary.append(f"⚑ {rid[:20]} — {rule}\n", style=laws.FAIL)
            summary.append("  reported only · the flag stays yours\n", style=laws.STEEL_DIM)
        summary.append("\nthe database holds the fills", style=laws.STEEL_DIM)
        stamped.update(summary)
        self.query_one(Masthead).update_stats(self.vault.knives)
        self._refresh_desk()
        self._line_state(f"desk: {filled_total} fills filed ✓ · s again · r demo")

    async def _work_one(
        self,
        entry: research.DocketEntry,
        record: dict,
        rules: list[str],
        plate: Plate,
    ) -> research.ResearchReport | None:
        """One record over the desk: PULL from the docket, READ its
        listing, STAMP only the empty fields. Returns None on a fault."""
        read_log = self.query_one("#read-log", Static)
        stamped = self.query_one("#stamped", Static)
        await self._travel_to("st-docket", plate)
        plate.begin(entry.knife_id, f"{len(entry.gaps)} open gap(s)")
        plate.stamp("gaps", ", ".join(g.field for g in entry.gaps)[:32])
        self.call_after_refresh(self._settle)
        await asyncio.sleep(0.4)

        self._line_state(f"desk: reading {entry.knife_id[:28]} ▸")
        await self._travel_to("st-read", plate)
        read_log.update(Text("pulling the listing…", style=laws.STEEL_DIM))
        try:
            listing = await asyncio.to_thread(scrape.fetch_listing, str(entry.url), FETCH_TIMEOUT)
        except scrape.ScrapeError as exc:
            read_log.update(Text(f"✗ {entry.knife_id[:24]}\n{exc}", style=laws.FAIL))
            plate.styles.border = ("heavy", laws.FAIL)
            await asyncio.sleep(0.5)
            return None
        learned = Text()
        learned.append(f"{listing.retailer[:30]}\n\n", style=laws.STEEL_MID)
        for label, value in listing.stamped_fields():
            learned.append_text(laws.field(label, value[:26], laws.STEEL_BRIGHT))
            learned.append("\n")
        read_log.update(learned)
        await asyncio.sleep(0.4)

        await self._travel_to("st-stamp", plate)
        report = research.research_record(record, listing, rules=rules)
        view = KnifeView(record)
        for field, _host in report.filled:
            reader = FIELD_READERS.get(field)
            plate.stamp(field, str(reader(view))[:32] if reader else "filled")
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.3)
        stamped.update(Text(f"{len(report.filled)} field(s) stamped — empty ones only", style=laws.PASS))
        await asyncio.sleep(0.3)
        return report

    # ---------------------------------------------------------- demo transit

    def _sample(self) -> KnifeView:
        knives = self.vault.knives
        return next((k for k in knives if k.price and k.blade_steel != "Unknown"), knives[0])

    async def demo_transit(self) -> None:
        """Deterministic, no network, no writes: a complete record replays
        the desk as if its steel and price were unknown — the motion can
        be judged identically anytime."""
        knife = self._sample()
        plate = self.query_one(Plate)
        read_log = self.query_one("#read-log", Static)
        stamped = self.query_one("#stamped", Static)
        self._reset_line(plate)
        self._line_state("desk: demo ▸")

        await asyncio.sleep(0.4)
        plate.begin(knife.display_name, "demo — 2 gaps assumed")
        plate.stamp("gaps", "steel, price")
        self.call_after_refresh(self._settle)
        await asyncio.sleep(0.6)

        await self._travel_to("st-read", plate)
        learned = Text()
        learned.append("the record's own listing, replayed\n\n", style=laws.STEEL_DIM)
        learned.append_text(laws.field("steel", knife.blade_steel, laws.STEEL_BRIGHT))
        learned.append("\n")
        learned.append_text(laws.field("price", knife.price_label, laws.STEEL_BRIGHT))
        read_log.update(learned)
        await asyncio.sleep(0.7)

        await self._travel_to("st-stamp", plate)
        for label, value in (("steel", knife.blade_steel), ("price", knife.price_label)):
            plate.stamp(label, value)
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.45)
        verdict = Text()
        verdict.append("2 fields stamped\n", style=laws.PASS)
        verdict.append("demo transit — nothing was written\n\n", style=laws.STEEL_DIM)
        verdict.append("s researches the docket for real", style=laws.STEEL_DIM)
        stamped.update(verdict)
        self._refresh_desk()
