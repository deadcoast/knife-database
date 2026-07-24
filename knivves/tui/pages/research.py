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
from functools import partial
from typing import TYPE_CHECKING, Callable, cast

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Footer, Static

from ... import research, scrape
from ...models import KnifeView, knife_views
from ...store import backup_database, save_database
from .. import laws
from ..gauges import EIGHTHS, MeterBar, _lerp
from ..masthead import Masthead
from ..plate import Plate
from ..surfaces import Teletype, TransitRail
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
        height: 9;
        margin: 1 2 0 2;
    }
    """

    LABEL_W = 7

    scan = reactive(-1.0)  # IDLE shimmer position across the field; -1 = at rest

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._columns: list[tuple[str, set[str]]] = []
        self._index: dict[str, int] = {}
        self._wake: set[tuple[str, int]] = set()
        self._working: str | None = None
        self._reveal: float | None = None
        self._spotlight: str | None = None
        self._idle_timer = None

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

    # ---------------------------------------------------- REVEAL: power-on

    @property
    def revealing(self) -> bool:
        return self._reveal is not None

    def begin_reveal(self) -> None:
        """The instrument powers on: the field starts dark."""
        self._reveal = 0.0
        self.refresh()

    def reveal_step(self, fraction: float) -> None:
        """Columns energize left to right; the gauge sweeps with them.
        Only truth is dramatized — a column, once lit, shows its real state."""
        self._reveal = min(fraction, 1.0)
        self.refresh()

    def end_reveal(self) -> None:
        self._reveal = None
        self.refresh()

    # -------------------------------------------------- IDLE: the scan breath

    def start_idle(self) -> None:
        """Ambient life on the long cadence — felt more than seen. Stands
        down by itself while the instrument reveals or a pass works."""
        if self._idle_timer is None:
            self._idle_timer = self.set_interval(laws.IDLE_CADENCE, self._breathe)

    def _breathe(self) -> None:
        if self._working is not None or self._reveal is not None or not self._columns:
            return
        self.scan = 0.0
        self.animate("scan", value=1.0, duration=laws.IDLE_STEP, easing=laws.EASING,
                     on_complete=self._scan_done)

    def _scan_done(self) -> None:
        self.scan = -1.0

    # ------------------------------------------------- CUE: the spotlight

    def spotlight(self, knife_id: str | None) -> None:
        """A docket card under the hand lights its column (and back)."""
        if knife_id != self._spotlight:
            self._spotlight = knife_id
            self.refresh()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        idx = int(event.offset.x) - self.LABEL_W
        knife_id = self._columns[idx][0] if 0 <= idx < len(self._columns) else None
        hook = getattr(self.screen, "spotlight", None)
        if callable(hook):
            hook(knife_id)

    def on_leave(self, event: events.Leave) -> None:
        hook = getattr(self.screen, "spotlight", None)
        if callable(hook):
            hook(None)

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
            return Strip([]).adjust_cell_length(width, Style())
        if y == 0:
            return self._gauge_line(width).adjust_cell_length(width, Style())
        if 1 <= y <= 7:
            return self._field_line(width, y - 1).adjust_cell_length(width, Style())
        if y == 8:
            return self._rail_line(width).adjust_cell_length(width, Style())
        return Strip([]).adjust_cell_length(width, Style())

    def _gauge_line(self, width: int) -> Strip:
        total = self.records
        done = self.complete
        if self._reveal is not None:
            done = int(done * self._reveal)
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
        energized = shown if self._reveal is None else int(shown * self._reveal)
        scan_col = int(shown * self.scan) if 0.0 <= self.scan <= 1.0 else None
        segments = [Segment(f"{label:>6} ", Style(color=laws.STEEL_DIM))]
        for col in range(shown):
            knife_id, missing = self._columns[col]
            if col >= energized:
                # not yet energized — the power-on draws the field in
                segments.append(Segment(" ", Style()))
                continue
            spotlit = knife_id == self._spotlight
            at_wavefront = self._reveal is not None and col >= energized - 3
            if (knife_id, row) in self._wake:
                segments.append(Segment("▪", Style(color=laws.ACCENT, bold=True)))
            elif keys & missing:
                if knife_id == self._working:
                    tone = laws.ACCENT
                elif spotlit:
                    tone = laws.STEEL_BRIGHT
                elif at_wavefront:
                    # the power-on's leading edge lights even the sockets
                    tone = laws.STEEL_MID
                else:
                    tone = laws.EDGE_BRIGHT
                segments.append(Segment("·", Style(color=tone, bold=spotlit)))
            else:
                if knife_id == self._working:
                    tone = laws.ACCENT
                elif spotlit:
                    tone = laws.STEEL_BRIGHT
                elif at_wavefront:
                    # a bright bar rides the sweep — the power-on is SEEN
                    tone = laws.STEEL_BRIGHT
                elif scan_col is not None and abs(col - scan_col) <= 1:
                    # the shimmer catches only what exists — lit dots gleam
                    tone = laws.STEEL_BRIGHT
                else:
                    tone = _lerp(col / max(shown - 1, 1))
                segments.append(Segment("▪", Style(color=tone, bold=spotlit or at_wavefront)))
        return Strip(segments)

    def _rail_line(self, width: int) -> Strip:
        shown = min(len(self._columns), width - self.LABEL_W)
        energized = shown if self._reveal is None else int(shown * self._reveal)
        cells = [" "] * width
        styles = [Style(color=laws.STEEL_DIM)] * width
        hidden = len(self._columns) - shown
        # the legend stands down while a marker is up — they never share cells
        marker_up = self._working is not None or self._spotlight is not None
        if self._reveal is None and not marker_up:
            note = f"1 column = 1 knife · dark = unknown{f' · +{hidden} off screen' if hidden > 0 else ''}"
            start = max(self.LABEL_W, width - len(note) - 1)
            for i, ch in enumerate(note):
                x = start + i
                if x < width:
                    cells[x] = ch
        else:
            start = width
        # the scale ticks ride the power-on wavefront
        for col in range(0, energized, 25):
            x = self.LABEL_W + col
            if x < start - 1:
                cells[x] = "╹"
        if self._spotlight is not None and self._working is None:
            col = self._index.get(self._spotlight)
            if col is not None and col < shown:
                x = self.LABEL_W + col
                cells[x] = "▴"
                styles[x] = Style(color=laws.STEEL_BRIGHT, bold=True)
        if self._working is not None:
            col = self._index.get(self._working)
            if col is not None and col < shown:
                x = self.LABEL_W + col
                cells[x] = "▲"
                styles[x] = Style(color=laws.ACCENT, bold=True)
        return Strip([Segment(ch, style) for ch, style in zip(cells, styles)])


class DocketCard(Static):
    """One tab of the card file. Under the hand it lights its own column
    on the unknowns map — the desk is one instrument, not two panels."""

    def __init__(self, knife_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.knife_id = knife_id

    def on_enter(self, event: events.Enter) -> None:
        hook = getattr(self.screen, "spotlight", None)
        if callable(hook):
            hook(self.knife_id)

    def on_leave(self, event: events.Leave) -> None:
        hook = getattr(self.screen, "spotlight", None)
        if callable(hook):
            hook(None)


class ResearchScreen(TipsMixin, Screen):
    CSS_PATH = "research.tcss"

    BINDINGS = [
        ("s", "start_pass", "Research the docket"),
        ("r", "replay", "Replay demo"),
        ("escape", "dismiss_tip", ""),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("research — fills missing data from listings"),
        "desk-map": Tip(
            "the unknowns map — every missing fact",
            "one column per knife,\none row per fact\n\n"
            "▪ lit — the vault knows\n· socket — a hole\n▪ amber — learned by\n  the pass running now",
        ),
        "st-docket": Tip(
            "the queue — who is next, and why",
            "ordered by law:\n  buy-list rank first,\n  then ★new,\n  then most gaps\n\n"
            "each card's punch-row is\nits column on the map\n\n"
            "the unreachable shelf:\n  no supported listing —\n  kept and said,\n  never skipped silently",
        ),
        "st-read": Tip("read — the record's own listing, learned fact by fact"),
        "st-stamp": Tip(
            "save — only empty fields are written",
            "fill-only-empty law:\n  user data is never\n  overwritten\n\n"
            "rulebook hits are\nreported on the log —\nthe flag stays yours",
        ),
    }

    def action_dismiss_tip(self) -> None:
        self.dismiss_capsule()

    def compose(self) -> ComposeResult:
        yield Masthead("RESEARCH")
        desk_map = UnknownsMap(id="desk-map")
        desk_map.border_title = "MISSING DATA"
        yield desk_map
        with Horizontal(id="desk-line"):
            with Vertical(classes="station", id="st-docket") as queue_pane:
                queue_pane.border_title = "QUEUE"
                yield Vertical(id="docket", classes="station-body")
            with Vertical(classes="station", id="st-read") as read_pane:
                read_pane.border_title = "READ"
                yield Teletype(id="read-log", classes="station-body")
            with Vertical(classes="station", id="st-stamp") as save_pane:
                save_pane.border_title = "SAVE"
                yield MeterBar("complete", id="meter-complete")
                yield MeterBar("queue", id="meter-docket")
                yield Static("", id="stamped", classes="station-body")
            yield TipRail()
        with Vertical(id="desk-tray") as tray:
            tray.border_title = "RECORD IN TRANSIT"
            tray.border_subtitle = "s researches · r replays the demo"
            yield TransitRail(
                [("st-docket", "QUEUE"), ("st-read", "READ"), ("st-stamp", "SAVE")],
                id="desk-rail",
            )
        yield Plate(id="desk-plate")
        yield TipCapsule()
        yield Footer()

    @property
    def knivves(self) -> "KnivvesApp":
        return cast("KnivvesApp", self.app)

    def on_mount(self) -> None:
        self._reveal = laws.Reveal(self)
        self._pass_active = False
        self.query_one(Masthead).update_stats(self.knivves.knives)
        self.show_room_tip()
        # the first ScreenResume refreshes the desk and powers the map on
        self.query_one("#desk-map", UnknownsMap).start_idle()
        # the demo waits for the instrument to power on
        self.set_timer(
            laws.REVEAL_SETTLE + 0.15,
            lambda: self.run_worker(self.demo_transit(), exclusive=True),
        )

    def on_screen_resume(self, event) -> None:
        """Every entrance powers the instrument on — once, then stillness."""
        if getattr(self, "_pass_active", False):
            return
        self._refresh_desk()
        self._power_on()

    def on_screen_suspend(self, event) -> None:
        self._reveal.arm()

    def _power_on(self) -> None:
        """REVEAL — the map runs its self-test: columns energize left to
        right (accelerating), the gauge sweeps to its true value, the
        scale ticks ride the wavefront. Only truth is dramatized."""
        unknowns = self.query_one("#desk-map", UnknownsMap)
        steps: list[tuple[float, Callable[[], None]]] = [(0.0, unknowns.begin_reveal)]
        n = 14
        span = laws.REVEAL_SETTLE - 0.2
        for i in range(1, n + 1):
            steps.append((span * (i / n) ** 0.5, partial(unknowns.reveal_step, i / n)))
        steps.append((laws.REVEAL_SETTLE, unknowns.end_reveal))
        self._reveal.play(steps)

    def spotlight(self, knife_id: str | None) -> None:
        """CUE — card and column agree under the hand, both directions."""
        self.query_one("#desk-map", UnknownsMap).spotlight(knife_id)
        for card in self.query(DocketCard):
            card.set_class(card.knife_id == knife_id, "spotlit")

    def action_replay(self) -> None:
        self._reveal.settle()
        self.run_worker(self.demo_transit(), exclusive=True)

    def action_start_pass(self) -> None:
        self._reveal.settle()
        self.run_worker(self.live_pass(), exclusive=True)

    # ------------------------------------------------------------- the desk

    def _line_state(self, text: str) -> None:
        self.query_one(Masthead).set_context(text)

    def _plate_y(self) -> int:
        plate = self.query_one(Plate)
        height = plate.outer_size.height or 10
        try:
            base = self.query_one("#desk-tray").region.y + 1
        except Exception:
            base = self.size.height - height - 2
        return max(4, min(base, self.size.height - height - 1))

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
        try:
            tray = self.query_one("#desk-tray").region
            x = min(x, tray.x + tray.width - (plate.outer_size.width or 46) - 2)
        except Exception:
            pass
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
        self._refresh_docket(plan, active)
        records = max(audit.records, 1)
        self.query_one("#meter-complete", MeterBar).set_meter(
            audit.complete / records, f"{audit.complete}/{audit.records}", laws.PASS
        )
        self.query_one("#meter-docket", MeterBar).set_meter(
            len(plan.planned) / records, f"{len(plan.planned)} open", laws.ACCENT
        )
        self.query_one("#st-docket").border_subtitle = f"{len(plan.planned)} waiting"
        self.query_one("#desk-map", UnknownsMap).border_subtitle = (
            f"{audit.complete}/{audit.records} complete"
        )
        self._line_state(f"{len(plan.planned)} in queue · {audit.complete}/{audit.records} complete")

    def _refresh_docket(self, plan: research.PassSummary, active: str | None = None) -> None:
        # the card file rebuilt as hardware: one DocketCard per tab, each
        # answering the hand (hover lights its map column); the card being
        # worked carries the amber edge bar.
        docket = self.query_one("#docket", Vertical)
        docket.remove_children()
        widgets: list[Widget] = []
        if plan.planned:
            for rank, entry in enumerate(plan.planned[:4], start=1):
                working = entry.knife_id == active
                card = DocketCard(entry.knife_id, id=f"card-{entry.knife_id}", classes="docket-card")
                card.update(self._card_text(rank, entry, working))
                card.set_class(working, "working")
                widgets.append(card)
            if len(plan.planned) > 4:
                widgets.append(Static(
                    Text(f"    +{len(plan.planned) - 4} more", style=laws.STEEL_DIM),
                    id="docket-overflow",
                ))
        else:
            widgets.append(Static(
                Text("fully researched — no open gaps\nwith a supported listing", style=laws.PASS),
                id="docket-empty",
            ))
        if plan.unreachable:
            widgets.append(Static(self._shelf_text(plan), id="docket-shelf"))

        removal = docket.remove_children()

        async def _rebuild() -> None:
            # removal must land before the new cards mount — same ids
            await removal
            await docket.mount_all(widgets)

        self.run_worker(_rebuild(), group="docket-rebuild", exclusive=True)

    def _card_text(self, rank: int, entry: research.DocketEntry, working: bool) -> Text:
        # rank · id · its punch-row (the map column in miniature)
        text = Text()
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
        missing = {g.field for g in entry.gaps}
        for punched in _punch_row(missing):
            text.append("○" if punched else "●", style=laws.EDGE_BRIGHT if punched else laws.STEEL_DIM)
        return text

    def _shelf_text(self, plan: research.PassSummary) -> Text:
        text = Text()
        text.append(f"UNREACHABLE  {len(plan.unreachable)}\n", style=f"bold {laws.STEEL_DIM}")
        for entry in plan.unreachable[:1]:
            text.append(f" ✗ {entry.knife_id[:24]:<25}", style=laws.STEEL_MID)
            for punched in _punch_row({g.field for g in entry.gaps}):
                text.append("○" if punched else "●", style=laws.EDGE_BRIGHT if punched else laws.STEEL_DIM)
            text.append("\n")
            text.append(f"    {entry.reason[:30]}\n", style=laws.STEEL_DIM)
        if len(plan.unreachable) > 1:
            text.append(f" +{len(plan.unreachable) - 1} more unreachable\n", style=laws.STEEL_DIM)
        return text

    # ------------------------------------------------------------ live pass

    async def live_pass(self) -> None:
        db = self.knivves.db
        plan = research.run_research(db, dry_run=True)
        if not plan.planned:
            self._refresh_desk()
            self._line_state("nothing to research ✓")
            return
        self._pass_active = True
        rules = research.rulebook(db)
        by_id = {str(r.get("id")): r for r in db.get("knives") or [] if isinstance(r, dict)}
        plate = self.query_one(Plate)
        unknowns = self.query_one("#desk-map", UnknownsMap)
        self._reset_line(plate)
        unknowns.begin_pass()
        filled_total = 0
        worked = 0
        hits: list[tuple[str, str]] = []
        try:
            for entry in plan.planned:
                unknowns.mark_working(entry.knife_id)
                self._refresh_docket(plan, entry.knife_id)
                report = await self._work_one(entry, by_id[entry.knife_id], rules, plate, unknowns)
                if report is None:
                    continue
                worked += 1
                filled_total += len(report.filled)
                hits.extend((report.knife_id, rule) for rule, _ in report.rulebook_hits)
        finally:
            self._pass_active = False
        unknowns.mark_working(None)
        if filled_total:
            backup_database("before-research", self.knivves.db_path)
            save_database(db, self.knivves.db_path)
            self.knivves.knives = knife_views(db)
        stamped = self.query_one("#stamped", Static)
        summary = Text()
        summary.append(f"{worked} records researched\n", style=laws.STEEL_BRIGHT)
        summary.append(f"{filled_total} fields filled — shown in amber\n", style=laws.PASS if filled_total else laws.STEEL_DIM)
        for rid, rule in hits:
            summary.append(f"⚑ {rid[:20]} — {rule}\n", style=laws.FAIL)
            summary.append("  reported only · the flag stays yours\n", style=laws.STEEL_DIM)
        summary.append("\nsaved to the database", style=laws.STEEL_DIM)
        stamped.update(summary)
        self.query_one(Masthead).update_stats(self.knivves.knives)
        self._refresh_desk()
        self._line_state(f"{filled_total} fields saved ✓ · s again · r demo")

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
        read_log = self.query_one("#read-log", Teletype)
        stamped = self.query_one("#stamped", Static)
        await self._travel_to("st-docket", plate)
        plate.add_class("carrying")
        plate.begin(entry.knife_id, f"{len(entry.gaps)} open gap(s)")
        gap_list = ", ".join(g.field for g in entry.gaps)
        plate.stamp("gaps", gap_list if len(gap_list) <= 32 else gap_list[:31] + "…")
        self.call_after_refresh(self._settle)
        await asyncio.sleep(0.4)

        self._line_state(f"reading {entry.knife_id[:28]} ▸")
        await self._travel_to("st-read", plate)
        read_log.update(Text("pulling the listing…", style=laws.STEEL_DIM))
        try:
            listing = await asyncio.to_thread(scrape.fetch_listing, str(entry.url), FETCH_TIMEOUT)
        except scrape.ScrapeError as exc:
            read_log.update(Text(f"✗ {entry.knife_id[:24]}\n{exc}", style=laws.FAIL))
            plate.styles.border_left = ("thick", laws.FAIL)
            await asyncio.sleep(0.5)
            return None
        # the listing prints — the teletype dramatizes arrival, fact by fact
        await read_log.type_lines(
            [laws.field(label, value[:26], laws.STEEL_BRIGHT)
             for label, value in listing.stamped_fields()],
            lead=Text(f"{listing.retailer[:30]}\n\n", style=laws.STEEL_MID),
        )

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
        read_log = self.query_one("#read-log", Teletype)
        stamped = self.query_one("#stamped", Static)
        unknowns = self.query_one("#desk-map", UnknownsMap)
        self._pass_active = True
        self._reset_line(plate)
        self._line_state("demo ▸")
        unknowns.mark_working(knife.id)

        await asyncio.sleep(0.4)
        plate.add_class("carrying")
        plate.begin(knife.display_name, "demo — 2 gaps assumed")
        plate.stamp("gaps", "steel, price")
        self.call_after_refresh(self._settle)
        await asyncio.sleep(0.6)

        await self._travel_to("st-read", plate)
        await read_log.type_lines(
            [
                laws.field("steel", knife.blade_steel, laws.STEEL_BRIGHT),
                laws.field("lock", knife.lock_type[:26], laws.STEEL_BRIGHT),
                laws.field("open", knife.opening_method[:26], laws.STEEL_BRIGHT),
                laws.field("length", knife.blade_length[:26], laws.STEEL_BRIGHT),
                laws.field("price", knife.price_label, laws.STEEL_BRIGHT),
            ],
            lead=Text("the record's own listing, replayed\n— only its 2 gaps will stamp\n\n", style=laws.STEEL_DIM),
            cadence=0.45,  # the demo prints deliberately — it is being watched
        )

        await self._travel_to("st-stamp", plate)
        for label, value in (("steel", knife.blade_steel), ("price", knife.price_label)):
            plate.stamp(label, value)
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.45)
        verdict = Text()
        verdict.append("2 fields stamped\n", style=laws.PASS)
        verdict.append("demo — nothing was saved\n\n", style=laws.STEEL_DIM)
        verdict.append("press s to research for real", style=laws.STEEL_DIM)
        stamped.update(verdict)
        unknowns.mark_working(None)
        self._pass_active = False
        self._refresh_desk()
