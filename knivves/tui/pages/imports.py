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
from functools import partial
from typing import TYPE_CHECKING, Callable, cast

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Footer, Input, Static

from ... import ingest, scrape
from ...models import knife_views
from ...research import RULE_KEYWORDS
from ...store import backup_database, make_knife_id, save_database
from .. import laws
from ..gauges import MeterBar
from ..masthead import Masthead
from ..surfaces import Engraving, Teletype
from ..plate import Plate
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

if TYPE_CHECKING:
    from .app import KnivvesApp

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

# Bolt engravings: the same rules cut short enough for a bolt's label plate.
BOLT_LABELS: dict[str, str] = {
    "automatic switchblade": "AUTO/SWITCHBLADE",
    "OTF automatic": "OTF AUTO",
    "gravity knife": "GRAVITY",
    "balisong": "BALISONG",
    "butterfly knife": "BUTTERFLY",
    "explicit centrifugal/flick knife": "CENTRIF/FLICK",
    "button/spring/device in handle that automatically opens the blade": "AUTO-OPEN DEVICE",
}


class GateBank(Widget):
    """The legal screen as hardware: the rulebook is a seven-bolt lock —
    the same bolts the vault door throws, one per rule, drawn across the
    line. A rule that clears RETRACTS its bolt into the housing; a hit
    throws the bolt in FAIL red and the lock stays shut. All bolts
    retracted = the lock is open and the plate may pass."""

    DEFAULT_CSS = """
    GateBank {
        height: auto;
        margin-bottom: 1;
    }
    """

    LABEL_W = 17

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rules: list[str] = []
        self._state: list[float] = []
        self._probing: int | None = None
        self._slammed: int | None = None
        self._hits: list[str] = []

    # ------------------------------------------------------------------ api

    @property
    def total(self) -> int:
        return len(self._rules)

    @property
    def open_count(self) -> int:
        return sum(1 for value in self._state if value >= 1.0)

    @property
    def slammed(self) -> int | None:
        return self._slammed

    def set_rules(self, rules: list[str]) -> None:
        self._rules = list(rules)
        self.reset()

    def reset(self) -> None:
        self._state = [0.0] * len(self._rules)
        self._probing = None
        self._slammed = None
        self._hits = []
        self.refresh()

    def probe(self, index: int) -> None:
        self._probing = index
        self.refresh()

    def slam(self, index: int, hits: list[str]) -> None:
        self._probing = None
        self._slammed = index
        self._state[index] = 0.0
        self._hits = hits
        self.refresh()

    async def retract(self, index: int, duration: float = 0.3) -> None:
        """The bolt slides into its housing — the only way a rule clears."""
        steps = 6
        for step in range(1, steps + 1):
            self._state[index] = step / steps
            self.refresh()
            await asyncio.sleep(duration / steps)
        self._probing = None
        self.refresh()

    # --------------------------------------------------------------- render

    def get_content_height(self, container, viewport, width: int) -> int:
        return len(self._rules) + 1

    def render_line(self, y: int) -> Strip:
        # every strip must be exactly width cells — a short strip shifts
        # every widget sharing the screen line (learned the hard way)
        width = self.size.width
        if width <= 0:
            return Strip([])
        if not self._rules:
            return Strip([]).adjust_cell_length(width, Style())
        if y == 0:
            return self._status_line(width).adjust_cell_length(width, Style())
        index = y - 1
        if index >= len(self._rules):
            return Strip([]).adjust_cell_length(width, Style())
        return self._bolt_line(width, index).adjust_cell_length(width, Style())

    def _status_line(self, width: int) -> Strip:
        if self._slammed is not None:
            hit = ", ".join(self._hits)
            text, color = f"LOCK THROWN ✗ matched: {hit}", laws.FAIL
        elif self.open_count == self.total:
            text, color = "LOCK OPEN — CLEAR TO PROCEED", laws.PASS
        elif self._probing is not None:
            text, color = f"BOLT {self._probing + 1}/{self.total} UNDER TEST", laws.ACCENT
        else:
            text, color = f"{self.total}-BOLT LOCK — thrown", laws.STEEL_DIM
        return Strip([Segment(text[:width], Style(color=color, bold=True))])

    def _bolt_line(self, width: int, index: int) -> Strip:
        rule = self._rules[index]
        label = BOLT_LABELS.get(rule, rule.upper())[: self.LABEL_W - 1]
        track_w = max(width - self.LABEL_W - 1, 6)
        state = self._state[index]
        slammed = self._slammed == index
        probing = self._probing == index
        if slammed:
            label_style = Style(color=laws.FAIL, bold=True)
            bolt_style = Style(color=laws.FAIL, bold=True)
        elif probing:
            label_style = Style(color=laws.ACCENT, bold=True)
            bolt_style = Style(color=laws.ACCENT)
        elif state >= 1.0:
            label_style = Style(color=laws.STEEL_DIM)
            bolt_style = Style(color=laws.STEEL_MID)
        else:
            label_style = Style(color=laws.STEEL_MID)
            bolt_style = Style(color=laws.STEEL_MID)
        bolt_len = round((1.0 - state) * track_w)
        segments = [Segment(f"{label:<{self.LABEL_W}}", label_style)]
        if bolt_len:
            segments.append(Segment("▓" * bolt_len, bolt_style))
        if track_w - bolt_len > 0:
            segments.append(Segment("╌" * (track_w - bolt_len), Style(color=laws.EDGE_BRIGHT)))
        housing = Style(color=laws.PASS if state >= 1.0 and not slammed else laws.EDGE_BRIGHT, bold=True)
        segments.append(Segment("▐", housing))
        return Strip(segments)


class TapeReader(Widget):
    """The extractor as hardware: the raw listing title runs through the
    room as a tape, and the exact substrings the parser pulled fields
    from light in accent as they land — the parse itself, visible."""

    DEFAULT_CSS = """
    TapeReader {
        height: 4;
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tape = ""
        self._spans: list[tuple[int, int]] = []

    # ------------------------------------------------------------------ api

    @property
    def lit_count(self) -> int:
        return len(self._spans)

    def set_tape(self, text: str) -> None:
        self._tape = text
        self._spans = []
        self.refresh()

    def light(self, start: int, length: int) -> None:
        self._spans.append((start, length))
        self.refresh()

    def clear(self) -> None:
        self._tape = ""
        self._spans = []
        self.refresh()

    # --------------------------------------------------------------- render

    def render_line(self, y: int) -> Strip:
        return self._render_row(y).adjust_cell_length(max(self.size.width, 0), Style())

    def _render_row(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        lane = width - 2
        if y in (0, 1):
            chunk = self._tape[y * lane : (y + 1) * lane]
            lit = set()
            for start, length in self._spans:
                lit.update(range(start, start + length))
            segments = [Segment("▐", Style(color=laws.EDGE_BRIGHT))]
            for i, ch in enumerate(chunk):
                pos = y * lane + i
                if pos in lit:
                    segments.append(Segment(ch, Style(color=laws.ACCENT, bold=True, underline=True, bgcolor=laws.SURFACE)))
                else:
                    segments.append(Segment(ch, Style(color=laws.STEEL_MID, bgcolor=laws.SURFACE)))
            if len(chunk) < lane:
                segments.append(Segment(" " * (lane - len(chunk)), Style(bgcolor=laws.SURFACE)))
            segments.append(Segment("▌", Style(color=laws.EDGE_BRIGHT)))
            return Strip(segments)
        if y == 2:
            if not self._tape:
                note = "tape empty — awaiting a listing"
            else:
                note = f"{len(self._spans)} span(s) lit from the tape"
            return Strip([Segment(note[:width], Style(color=laws.STEEL_DIM))])
        return Strip([])


class ParseRegister(Widget):
    """The extractor's register: one slot per fact the parser can pull.
    A slot lights amber when its value came off the tape itself, steel
    when it was learned elsewhere on the page, and stays a dark socket
    when the listing never gave it up — the parse, honest, in one bank."""

    SLOTS = ["source", "brand", "model", "steel", "lock", "open", "length", "price", "stock"]
    ALIASES = {"opening": "open", "availability": "stock", "len": "length", "retailer": "source"}

    DEFAULT_CSS = """
    ParseRegister {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._values: dict[str, tuple[str, bool]] = {}

    def reset(self) -> None:
        self._values = {}
        self.refresh()

    def stamp(self, label: str, value: str, from_tape: bool) -> None:
        key = self.ALIASES.get(label.lower(), label.lower())
        self._values[key] = (value, from_tape)
        self.refresh()

    def get_content_height(self, container, viewport, width: int) -> int:
        return len(self.SLOTS)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0 or y >= len(self.SLOTS):
            return Strip([]).adjust_cell_length(max(width, 0), Style())
        slot = self.SLOTS[y]
        held = self._values.get(slot)
        segments = [Segment(f"{slot.upper():>7} ", Style(color=laws.STEEL_DIM))]
        if held is None:
            segments.append(Segment("·", Style(color=laws.EDGE_BRIGHT)))
            segments.append(Segment(" ╌╌╌╌╌╌╌╌╌╌╌╌", Style(color=laws.EDGE)))
        else:
            value, from_tape = held
            glyph_tone = laws.ACCENT if from_tape else laws.STEEL_MID
            segments.append(Segment("▪", Style(color=glyph_tone, bold=from_tape)))
            segments.append(Segment(f" {value[: max(width - 10, 4)]}", Style(color=laws.STEEL_BRIGHT)))
        return Strip(segments).adjust_cell_length(width, Style())


def _find_span(tape: str, value: str) -> tuple[int, int] | None:
    """Where a parsed value actually came from on the tape, if it did.
    Only real matches light — a field learned off-tape stays unlit."""
    low = tape.lower()
    candidates = [value]
    stripped = value.replace("$", "").replace(" CAD", "").replace(",", "")
    if stripped != value:
        candidates.append(stripped)
    if "(" in value and value.endswith(")"):
        candidates.append(value[value.rindex("(") + 1 : -1])
    for candidate in candidates:
        candidate = candidate.strip()
        if len(candidate) < 3:
            continue
        found = low.find(candidate.lower())
        if found >= 0:
            return found, len(candidate)
    return None


class ImportsScreen(TipsMixin, Screen):
    CSS_PATH = "imports.tcss"

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
        "st-extract": Tip(
            "the tape is read — fields are stamped here",
            "the raw listing title runs\nas a tape; the substrings\nthe parser actually used\nlight in amber\n\n"
            "a field learned off-tape\n(price, stock) stays unlit —\nthe tape never lies",
        ),
        "st-legal": Tip(
            "the rulebook is a seven-bolt lock",
            "one bolt per rule — the same\nbolts the vault door throws\n\n"
            "a rule that clears RETRACTS\nits bolt · a hit throws it\nred and nothing files\n\n"
            "'assisted opening' is legal\nand never throws a bolt",
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
                yield TapeReader(id="tape")
                yield Static("", id="extract-log", classes="station-body")
                yield ParseRegister(id="parse-register")
            with Vertical(classes="station", id="st-legal"):
                yield Engraving("legal screen")
                yield GateBank(id="gatebank")
                yield Static("", id="gates", classes="station-body")
                yield Teletype(id="legal-log", classes="station-body")
            with Vertical(classes="station", id="st-vault"):
                yield Engraving("vault")
                yield Static("", id="filed", classes="station-body")
                yield MeterBar("★new", id="meter-window")
                yield Static("", id="vault-tally", classes="station-body")
            yield TipRail()
        yield Plate(id="forge-plate")
        yield TipCapsule()
        yield Footer()

    @property
    def knivves(self) -> "KnivvesApp":
        return cast("KnivvesApp", self.app)

    def on_mount(self) -> None:
        self._reveal = laws.Reveal(self)
        self._session_filed = 0
        self._session_refused = 0
        self._session_rejected = 0
        self.query_one(Masthead).update_stats(self.knivves.knives)
        self.query_one(GateBank).set_rules(self._rules())
        self._vault_readout()
        # the rulebook prints itself below the lock — the law, on paper
        rules = self._rules()
        self.run_worker(
            self.query_one("#legal-log", Teletype).type_lines(
                [
                    Text(f"{i} ", style=laws.ACCENT).append_text(
                        Text(BOLT_LABELS.get(rule, rule.upper()), style=laws.STEEL_MID)
                    )
                    for i, rule in enumerate(rules, start=1)
                ],
                lead=Text("the rulebook — one bolt per rule:\n\n", style=laws.STEEL_DIM),
                cadence=0.2,
            ),
            group="legal-log",
            exclusive=True,
        )
        self.show_room_tip()
        self.run_worker(self.demo_transit(), exclusive=True)

    def _vault_readout(self) -> None:
        """The vault station's tally — this session's traffic, counted."""
        knives = self.knivves.knives
        blades = max(len(knives), 1)
        fresh = sum(1 for k in knives if k.is_new)
        self.query_one("#meter-window", MeterBar).set_meter(
            fresh / blades, f"{fresh}/{len(knives)}", laws.FRESH if fresh else None
        )
        tally = Text()
        tally.append_text(laws.field("in vault", str(len(knives))))
        tally.append("\n")
        tally.append_text(laws.field(
            "filed", f"{self._session_filed} this session",
            laws.PASS if self._session_filed else laws.STEEL_DIM,
        ))
        tally.append("\n")
        tally.append_text(laws.field("refused", f"{self._session_refused} duplicate(s)", laws.STEEL_DIM))
        tally.append("\n")
        tally.append_text(laws.field(
            "rejected", f"{self._session_rejected} by the lock",
            laws.FAIL if self._session_rejected else laws.STEEL_DIM,
        ))
        self.query_one("#vault-tally", Static).update(tally)

    def on_screen_resume(self, event) -> None:
        self._power_on()

    def on_screen_suspend(self, event) -> None:
        self._reveal.arm()

    def _power_on(self) -> None:
        """REVEAL — the intake line lights station by station, in work order,
        while the material makes its way to the first machine."""
        stations = [self.query_one(f"#{sid}") for sid in ("st-extract", "st-legal", "st-vault")]

        def cold() -> None:
            for station in stations:
                station.add_class("cold")

        steps: list[tuple[float, Callable[[], None]]] = [(0.0, cold)]
        for i, station in enumerate(stations):
            steps.append((0.25 + i * laws.REVEAL_STAGGER * 3, partial(station.remove_class, "cold")))
        self._reveal.play(steps)

    def action_replay(self) -> None:
        self._reveal.settle()
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
        self.query_one(GateBank).reset()
        self.query_one(TapeReader).clear()
        self.query_one(ParseRegister).reset()
        self._plate_x = 4
        self.call_after_refresh(self._settle)

    def on_resize(self, event) -> None:
        """A resized terminal re-seats the plate — it must never clip."""
        if getattr(self, "_plate_x", None) is not None:
            self.call_after_refresh(self._settle)

    def _rules(self) -> list[str]:
        rule = self.knivves.db.get("workflow_rules", {}).get("canadian_online_retailer_rule", {})
        return list(rule.get("only_reject_or_fail_if_clear_prohibited_mechanism", []))

    def _line_state(self, text: str) -> None:
        self.query_one(Masthead).set_context(text)

    async def _run_lock(self, title_text: str) -> tuple[str, list[str]] | None:
        """Throw the listing at the lock: every rule probes its bolt — a
        clear rule retracts it, a hit slams it. Returns the (rule, hits)
        that threw the lock, or None when it opened."""
        bank = self.query_one(GateBank)
        gates = self.query_one("#gates", Static)
        log = self.query_one("#legal-log", Teletype)
        rules = self._rules()
        bank.set_rules(rules)
        low = title_text.lower()
        checked = Text("the check, rule by rule:\n\n", style=laws.STEEL_DIM)
        log.update(checked)
        for index, rule in enumerate(rules):
            bank.probe(index)
            await asyncio.sleep(0.22)
            hits = [kw for kw in RULE_KEYWORDS.get(rule, (rule.lower(),)) if kw in low]
            label = BOLT_LABELS.get(rule, rule.upper())
            if hits:
                bank.slam(index, hits)
                checked.append(f"✗ {label} — matched: {', '.join(hits)}\n", style=laws.FAIL)
                log.update(checked)
                gates.update(Text(
                    f"✗ {RULE_DISPLAY.get(rule, rule)} — listing matched: {', '.join(hits)}",
                    style=laws.FAIL,
                ))
                return rule, hits
            checked.append("● ", style=laws.PASS)
            checked.append(f"{label:<17}", style=laws.STEEL_MID)
            checked.append("no match\n", style=laws.STEEL_DIM)
            log.update(checked)
            await bank.retract(index)
        gates.update(Text("the lock is open — CLEAR TO PROCEED", style=laws.PASS))
        return None

    async def _travel_to(self, station_id: str, plate: Plate) -> None:
        x = self.query_one(f"#{station_id}").region.x + 2
        self._plate_x = x
        laws.travel(plate, x, self._plate_y())
        await asyncio.sleep(laws.TRAVEL_DURATION + 0.15)

    # ---------------------------------------------------------- live intake

    def _already_filed(self, url: str) -> str | None:
        for knife in self.knivves.knives:
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
        plate.add_class("carrying")
        plate.begin("INCOMING", url.split("//")[-1][:42])

        duplicate = self._already_filed(url)
        if duplicate:
            extract_log.update(Text(f"already in the vault: {duplicate}", style=laws.ACCENT))
            plate.begin("DUPLICATE", duplicate)
            self._session_refused += 1
            self._vault_readout()
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
        tape = self.query_one(TapeReader)
        register = self.query_one(ParseRegister)
        tape.set_tape(listing.listing_title)
        stamps = listing.stamped_fields()
        for label, value in stamps:
            span = _find_span(listing.listing_title, value)
            if span:
                tape.light(*span)
            register.stamp(label, value, span is not None)
            plate.stamp(label, value)
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.35)
        extract_log.update(Text(f"{len(stamps)} fields parsed · {tape.lit_count} from the tape", style=laws.PASS))

        self._line_state("line: legal screen ▸")
        await self._travel_to("st-legal", plate)

        thrown = await self._run_lock(listing.listing_title)
        if thrown is not None:
            rule, _hits = thrown
            plate.styles.border = ("heavy", laws.FAIL)
            plate.stamp("verdict", f"REJECTED — {RULE_DISPLAY.get(rule, rule)}")
            self.call_after_refresh(self._settle)
            filed.update(Text("not filed — prohibited mechanism identified", style=laws.FAIL))
            self._session_rejected += 1
            self._vault_readout()
            self._line_state("line: rejected ✗")
            return
        await asyncio.sleep(0.5)

        self._line_state("line: vault ▸")
        await self._travel_to("st-vault", plate)
        view = self.knivves.file_record(self._record_from(listing))
        landed = Text()
        landed.append(f"{view.display_name}\n", style=laws.STEEL_BRIGHT)
        landed.append(f"filed · {view.id}\n", style=laws.STEEL_DIM)
        landed.append("now in the rack · awaiting review", style=laws.STEEL_DIM)
        filed.update(landed)
        self._session_filed += 1
        self._vault_readout()
        self._line_state("line: filed ✓")
        self.query_one(Masthead).update_stats(self.knivves.knives)

    # ---------------------------------------------------------- file intake

    async def file_transit(self, raw_path: str) -> None:
        """Run an ingestion ledger down the line: sections read at EXTRACT,
        the plan screens at LEGAL SCREEN, the batch files at VAULT."""
        from pathlib import Path as _Path

        plate, extract_log, gates, filed = self._stations()
        self._reset_line(plate)
        self._line_state("line: reading ledger ▸")
        path = _Path(raw_path).expanduser()
        plate.add_class("carrying")
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
        plan = ingest.build_plan(doc, self.knivves.db)
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
        backup_database("before-ingest", self.knivves.db_path)
        report = ingest.apply_plan(plan, self.knivves.db)
        save_database(self.knivves.db, self.knivves.db_path)
        self.knivves.knives = knife_views(self.knivves.db)
        landed = Text()
        landed.append(f"{report.added} filed ★new", style=f"bold {laws.FRESH}")
        landed.append(f" · {report.merged} merged\n", style=laws.STEEL_MID)
        landed.append(f"⬖ buy list {report.buylist} deep", style=laws.ACCENT if report.buylist else laws.STEEL_DIM)
        landed.append(f" · {report.sources} sources\n", style=laws.STEEL_DIM)
        if report.repairs:
            landed.append(f"{len(report.repairs)} damaged lines repaired\n", style=laws.STEEL_DIM)
        landed.append("\nnow in the library · knivves update seals the batch", style=laws.STEEL_DIM)
        filed.update(landed)
        self._session_filed += report.added
        self._vault_readout()
        self._line_state(f"line: filed {report.added} ✓")
        self.query_one(Masthead).update_stats(self.knivves.knives)

    # ---------------------------------------------------------- demo transit

    def _sample(self):
        knives = self.knivves.knives
        return next((k for k in knives if k.price and k.blade_steel != "Unknown"), knives[0])

    async def demo_transit(self) -> None:
        knife = self._sample()
        plate, extract_log, gates, filed = self._stations()
        self._reset_line(plate)
        self._line_state("line: demo ▸")
        plate.add_class("carrying")
        plate.begin("INCOMING", "")
        extract_log.update(Text("reading listing…", style=laws.STEEL_DIM))
        await asyncio.sleep(0.6)

        plate.begin(knife.display_name, knife.id)
        demo_tape = str(knife.raw.get("listing_title") or knife.display_name)
        tape = self.query_one(TapeReader)
        register = self.query_one(ParseRegister)
        tape.set_tape(demo_tape)
        best = knife.best_retailer or {}
        stamps = [
            ("source", str(best.get("retailer") or "—")),
            ("brand", knife.brand),
            ("model", knife.model),
            ("steel", knife.blade_steel),
            ("price", knife.price_label),
        ]
        for label, value in stamps:
            span = _find_span(demo_tape, value)
            if span:
                tape.light(*span)
            register.stamp(label, value, span is not None)
            plate.stamp(label, value)
            self.call_after_refresh(self._settle)
            await asyncio.sleep(0.45)
        extract_log.update(Text(f"{len(stamps)} fields parsed · {tape.lit_count} from the tape", style=laws.PASS))

        await self._travel_to("st-legal", plate)
        await self._run_lock(demo_tape)
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
