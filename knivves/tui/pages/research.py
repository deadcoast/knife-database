"""The Research Desk — the room where the vault researches its own unknowns.

The centerpiece is the UNKNOWNS MAP: the entire database drawn as a
dot-matrix field, one column per knife, one row per fact. A lit dot is
a thing the vault knows; a dark socket is a hole in a record. The map
is the collection's ignorance made visible in one glance — and when a
pass runs it fills LIVE, column by column, each learned fact burning
an amber wake so the screen shows exactly what this pass discovered
versus what was already known.

Below it, the docket is a card file: every incomplete record as a tab
carrying its own punch-row — the same seven sockets as the map, in
miniature — ordered by law (BuyList rank, then ★new, then most gaps),
with the unreachable shelf and its reasons underneath. `s` works the
file for real: each card's plate is PULLED, its listing is READ fact
by fact, and only its empty fields STAMP on — user data is never
overwritten, and a rulebook hit is reported, never written. `r`
replays a deterministic no-network demo; the map never lies during it
(nothing was written, so nothing lights).
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

from ... import research, scrape
from ...models import KnifeView, knife_views
from ...store import backup_database, save_database
from .. import laws
from ..gauges import EIGHTHS, _lerp
from ..masthead import Masthead
from ..plate import Plate
from ..surfaces import Engraving
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

if TYPE_CHECKING:
    from .app import KnivvesApp

FETCH_TIMEOUT = 12.0

# The seven facts the map tracks — row label, and which audit gap keys
# punch that row's socket. TITLE folds the naming gaps into one row.
FIELD_ROWS: list[tuple[str, frozenset[str]]] = [
    ("STEEL", frozenset({"steel"})),
    ("LOCK", frozenset({"lock"})),
    ("OPEN", frozenset({"opening"})),
    ("LEN", frozenset({"length"})),
    ("PRICE", frozenset({"price"})),
    ("STOCK", frozenset({"availability"})),
    ("TITLE", frozenset({"title", "brand", "model", "listing_title"})),
]

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


def _punch_row(missing: set[str]) -> list[bool]:
    """The seven sockets for one record: True = punched (missing)."""
    return [bool(keys & missing) for _, keys in FIELD_ROWS]


class UnknownsMap(Widget):
    """The database's ignorance, drawn: one column per record, one row per
    fact. Lit dot = known (steel ramp, brightening across the field);
    dark socket = missing. Cells filled by the current pass burn accent —
    the amber wake — until the next pass begins. Row 0 is the machined
    completeness gauge; the bottom rail carries scale ticks and the
    working-column marker."""

    DEFAULT_CSS = """
    UnknownsMap {
        height: 10;
        margin: 1 2 0 2;
    }
    """

    LABEL_W = 7

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._columns: list[tuple[str, set[str]]] = []
        self._index: dict[str, int] = {}
        self._wake: set[tuple[str, int]] = set()
        self._working: str | None = None

    # ------------------------------------------------------------------ api

    @property
    def records(self) -> int:
        return len(self._columns)

    @property
    def complete(self) -> int:
        return sum(1 for _, missing in self._columns if not missing)

    @property
    def wake(self) -> int:
        return len(self._wake)

    def set_state(self, columns: list[tuple[str, set[str]]]) -> None:
        """The field re-derived from the database. The wake survives —
        it belongs to the pass, not the audit."""
        self._columns = columns
        self._index = {knife_id: i for i, (knife_id, _) in enumerate(columns)}
        self.refresh()

    def begin_pass(self) -> None:
        self._wake.clear()
        self.refresh()

    def mark_working(self, knife_id: str | None) -> None:
        self._working = knife_id
        self.refresh()

    def mark_filled(self, knife_id: str, field_key: str) -> None:
        """A fact landed: the socket lights and joins the amber wake."""
        col = self._index.get(knife_id)
        if col is None:
            return
        _, missing = self._columns[col]
        missing.discard(field_key)
        for row, (_, keys) in enumerate(FIELD_ROWS):
            if field_key in keys:
                self._wake.add((knife_id, row))
        self.refresh()

    # --------------------------------------------------------------- render

    def render_line(self, y: int) -> Strip:
        # strips must be exactly width cells: a short strip shifts every
        # widget sharing the screen line
        width = self.size.width
        if width <= 0:
            return Strip([])
        if not self._columns:
            return Strip([]).adjust_cell_length(width)
        if y == 0:
            return self._gauge_line(width).adjust_cell_length(width)
        if y == 1:
            return Strip([]).adjust_cell_length(width)
        if 2 <= y <= 8:
            return self._field_line(width, y - 2).adjust_cell_length(width)
        if y == 9:
            return self._rail_line(width).adjust_cell_length(width)
        return Strip([]).adjust_cell_length(width)

    def _gauge_line(self, width: int) -> Strip:
        total = self.records
        done = self.complete
        fraction = done / total if total else 0.0
        label = f"COMPLETE {done}/{total} "
        pct = f" {fraction * 100:.0f}%"
        span = max(width - len(label) - len(pct) - 1, 8)
        exact = fraction * span
        full = int(exact)
        frac = exact - full
        segments = [Segment(label, Style(color=laws.STEEL_DIM))]
        for i in range(full):
            segments.append(Segment(" ", Style(bgcolor=_lerp(i / max(span - 1, 1)))))
        used = full
        if frac >= 0.125 and full < span:
            glyph = EIGHTHS[int(frac * 8) - 1]
            segments.append(Segment(glyph, Style(color=_lerp(full / max(span - 1, 1)), bgcolor=laws.EDGE)))
            used += 1
        if used < span:
            segments.append(Segment(" " * (span - used), Style(bgcolor=laws.EDGE)))
        segments.append(Segment(pct, Style(color=laws.ACCENT if fraction < 1 else laws.PASS)))
        return Strip(segments)

    def _field_line(self, width: int, row: int) -> Strip:
        label, keys = FIELD_ROWS[row]
        shown = min(len(self._columns), width - self.LABEL_W)
        segments = [Segment(f"{label:>6} ", Style(color=laws.STEEL_DIM))]
        for col in range(shown):
            knife_id, missing = self._columns[col]
            if (knife_id, row) in self._wake:
                segments.append(Segment("▪", Style(color=laws.ACCENT, bold=True)))
            elif keys & missing:
                dark = laws.ACCENT if knife_id == self._working else laws.EDGE_BRIGHT
                segments.append(Segment("·", Style(color=dark)))
            else:
                tone = laws.ACCENT if knife_id == self._working else _lerp(col / max(shown - 1, 1))
                segments.append(Segment("▪", Style(color=tone)))
        return Strip(segments)

    def _rail_line(self, width: int) -> Strip:
        shown = min(len(self._columns), width - self.LABEL_W)
        cells = [" "] * width
        styles = [Style(color=laws.STEEL_DIM)] * width
        hidden = len(self._columns) - shown
        note = f"1 column = 1 knife · dark socket = unknown{f' · +{hidden} beyond the edge' if hidden > 0 else ''}"
        start = max(self.LABEL_W, width - len(note) - 1)
        for i, ch in enumerate(note):
            x = start + i
            if x < width:
                cells[x] = ch
        for col in range(0, shown, 25):
            x = self.LABEL_W + col
            if x < start - 1:
                cells[x] = "╹"
        if self._working is not None:
            col = self._index.get(self._working)
            if col is not None and col < shown:
                x = self.LABEL_W + col
                cells[x] = "▲"
                styles[x] = Style(color=laws.ACCENT, bold=True)
        return Strip([Segment(ch, style) for ch, style in zip(cells, styles)])


class ResearchScreen(TipsMixin, Screen):
    CSS_PATH = "research.tcss"

    BINDINGS = [
        ("s", "start_pass", "Research the docket"),
        ("r", "replay", "Replay demo"),
        ("escape", "dismiss_tip", ""),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("research — the vault fills its own unknowns"),
        "desk-map": Tip(
            "the unknowns map — every hole in the vault",
            "one column per knife,\none row per fact\n\n"
            "▪ lit — the vault knows\n· socket — a hole\n▪ amber — learned by\n  the pass running now",
        ),
        "st-docket": Tip(
            "the card file — who is next, and why",
            "ordered by law:\n  buy-list rank first,\n  then ★new,\n  then most gaps\n\n"
            "each card's punch-row is\nits column on the map\n\n"
            "the unreachable shelf:\n  no supported listing —\n  kept and said,\n  never skipped silently",
        ),
        "st-read": Tip("read — the record's own listing, learned fact by fact"),
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
        yield UnknownsMap(id="desk-map")
        with Horizontal(id="desk-line"):
            with Vertical(classes="station", id="st-docket"):
                yield Engraving("the card file")
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
    def knivves(self) -> "KnivvesApp":
        return cast("KnivvesApp", self.app)

    def on_mount(self) -> None:
        self.query_one(Masthead).update_stats(self.knivves.knives)
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

    def _refresh_desk(self, active: str | None = None) -> None:
        """Docket, shelf, map, and masthead — all from one audit."""
        db = self.knivves.db
        plan = research.run_research(db, dry_run=True)
        audit = research.audit_database(db)
        columns: list[tuple[str, set[str]]] = []
        seen: set[str] = set()
        for entry in list(plan.planned) + list(plan.unreachable):
            columns.append((entry.knife_id, {g.field for g in entry.gaps}))
            seen.add(entry.knife_id)
        for knife in self.knivves.knives:
            if knife.id not in seen:
                columns.append((knife.id, {g.field for g in audit.gaps_by_id.get(knife.id, [])}))
        self.query_one("#desk-map", UnknownsMap).set_state(columns)
        self.query_one("#docket", Static).update(self._docket_text(plan, active))
        self._line_state(f"desk: {len(plan.planned)} on the docket · {audit.complete}/{audit.records} complete")

    def _docket_text(self, plan: research.PassSummary, active: str | None = None) -> Text:
        # one card per line: rank · id · its punch-row (the map column in
        # miniature). The card being worked carries the amber edge bar.
        text = Text()
        if plan.planned:
            for rank, entry in enumerate(plan.planned[:10], start=1):
                missing = {g.field for g in entry.gaps}
                working = entry.knife_id == active
                text.append("▌" if working else " ", style=laws.ACCENT)
                text.append(f"{rank:>2} ", style=laws.ACCENT)
                if entry.buy_priority:
                    text.append(f"⬖{entry.buy_priority} ", style="bold magenta")
                if entry.is_new:
                    text.append("★ ", style=laws.FRESH)
                text.append(
                    f"{entry.knife_id[:20]:<21}",
                    style=f"bold {laws.STEEL_BRIGHT}" if working else laws.STEEL_BRIGHT,
                )
                for punched in _punch_row(missing):
                    text.append("○" if punched else "●", style=laws.EDGE_BRIGHT if punched else laws.STEEL_DIM)
                text.append("\n")
            if len(plan.planned) > 10:
                text.append(f"    +{len(plan.planned) - 10} deeper\n", style=laws.STEEL_DIM)
        else:
            text.append("fully researched — no open gaps\nwith a supported listing\n", style=laws.PASS)
        if plan.unreachable:
            text.append(f"\nUNREACHABLE  {len(plan.unreachable)}\n", style=f"bold {laws.STEEL_DIM}")
            for entry in plan.unreachable[:4]:
                text.append(f" ✗ {entry.knife_id[:24]:<25}", style=laws.STEEL_MID)
                for punched in _punch_row({g.field for g in entry.gaps}):
                    text.append("○" if punched else "●", style=laws.EDGE_BRIGHT if punched else laws.STEEL_DIM)
                text.append("\n")
                text.append(f"    {entry.reason[:30]}\n", style=laws.STEEL_DIM)
            if len(plan.unreachable) > 4:
                text.append(f" +{len(plan.unreachable) - 4} more on the shelf\n", style=laws.STEEL_DIM)
        return text

    # ------------------------------------------------------------ live pass

    async def live_pass(self) -> None:
        db = self.knivves.db
        plan = research.run_research(db, dry_run=True)
        if not plan.planned:
            self._refresh_desk()
            self._line_state("desk: nothing to research ✓")
            return
        rules = research.rulebook(db)
        by_id = {str(r.get("id")): r for r in db.get("knives") or [] if isinstance(r, dict)}
        plate = self.query_one(Plate)
        unknowns = self.query_one("#desk-map", UnknownsMap)
        self._reset_line(plate)
        unknowns.begin_pass()
        filled_total = 0
        worked = 0
        hits: list[tuple[str, str]] = []
        for entry in plan.planned:
            unknowns.mark_working(entry.knife_id)
            self.query_one("#docket", Static).update(self._docket_text(plan, entry.knife_id))
            report = await self._work_one(entry, by_id[entry.knife_id], rules, plate, unknowns)
            if report is None:
                continue
            worked += 1
            filled_total += len(report.filled)
            hits.extend((report.knife_id, rule) for rule, _ in report.rulebook_hits)
        unknowns.mark_working(None)
        if filled_total:
            backup_database("before-research", self.knivves.db_path)
            save_database(db, self.knivves.db_path)
            self.knivves.knives = knife_views(db)
        stamped = self.query_one("#stamped", Static)
        summary = Text()
        summary.append(f"{worked} records researched\n", style=laws.STEEL_BRIGHT)
        summary.append(f"{filled_total} facts learned — the amber wake\n", style=laws.PASS if filled_total else laws.STEEL_DIM)
        for rid, rule in hits:
            summary.append(f"⚑ {rid[:20]} — {rule}\n", style=laws.FAIL)
            summary.append("  reported only · the flag stays yours\n", style=laws.STEEL_DIM)
        summary.append("\nthe database holds the fills", style=laws.STEEL_DIM)
        stamped.update(summary)
        self.query_one(Masthead).update_stats(self.knivves.knives)
        self._refresh_desk()
        self._line_state(f"desk: {filled_total} fills filed ✓ · s again · r demo")

    async def _work_one(
        self,
        entry: research.DocketEntry,
        record: dict,
        rules: list[str],
        plate: Plate,
        unknowns: UnknownsMap,
    ) -> research.ResearchReport | None:
        """One card over the desk: PULL from the file, READ its listing
        fact by fact, STAMP only the empty fields — the map lighting as
        each one lands. Returns None on a fault."""
        read_log = self.query_one("#read-log", Static)
        stamped = self.query_one("#stamped", Static)
        await self._travel_to("st-docket", plate)
        plate.begin(entry.knife_id, f"{len(entry.gaps)} open gap(s)")
        gap_list = ", ".join(g.field for g in entry.gaps)
        plate.stamp("gaps", gap_list if len(gap_list) <= 32 else gap_list[:31] + "…")
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
            await asyncio.sleep(0.12)

        await self._travel_to("st-stamp", plate)
        report = research.research_record(record, listing, rules=rules)
        view = KnifeView(record)
        for field, _host in report.filled:
            reader = FIELD_READERS.get(field)
            plate.stamp(field, str(reader(view))[:32] if reader else "filled")
            unknowns.mark_filled(entry.knife_id, field)
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.25)
        stamped.update(Text(f"{len(report.filled)} field(s) stamped — empty ones only", style=laws.PASS))
        await asyncio.sleep(0.3)
        return report

    # ---------------------------------------------------------- demo transit

    def _sample(self) -> KnifeView:
        knives = self.knivves.knives
        return next((k for k in knives if k.price and k.blade_steel != "Unknown"), knives[0])

    async def demo_transit(self) -> None:
        """Deterministic, no network, no writes: a complete record replays
        the desk as if its steel and price were unknown. The map stays
        truthful — nothing was written, so nothing lights."""
        knife = self._sample()
        plate = self.query_one(Plate)
        read_log = self.query_one("#read-log", Static)
        stamped = self.query_one("#stamped", Static)
        unknowns = self.query_one("#desk-map", UnknownsMap)
        self._reset_line(plate)
        self._line_state("desk: demo ▸")
        unknowns.mark_working(knife.id)

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
        read_log.update(learned)
        await asyncio.sleep(0.35)
        learned.append_text(laws.field("price", knife.price_label, laws.STEEL_BRIGHT))
        read_log.update(learned)
        await asyncio.sleep(0.55)

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
        unknowns.mark_working(None)
        self._refresh_desk()
