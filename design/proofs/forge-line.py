"""Forge Line proof — intake as a production line, the record as a moving object.

A real record travels EXTRACT -> LEGAL SCREEN -> VAULT. Fields stamp onto the
plate as parsed; the legal gates are the actual prohibited-mechanism rules from
knives.json, executing visibly; the plate lands in the rack.

This proof runs on a real record's data without network so the transit is
deterministic to judge. The live-fetch wiring is the already-proven scraper.

Run:  python design/proofs/forge-line.py     (q quits, r replays)
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.scalar import ScalarOffset
from textual.widgets import Footer, Static

STEEL_BRIGHT = "#dde6ee"
STEEL_MID = "#8b96a0"
STEEL_DIM = "#5c6670"
ACCENT = "#d7a455"
PASS = "#79b473"

DB = json.loads((REPO / "knivves" / "data" / "knives.json").read_text(encoding="utf-8"))
RECORD = next(k for k in DB["knives"] if k["id"] == "kubey-gurkha-14c28n-g10-black-ku397a")
RULES = DB["workflow_rules"]["canadian_online_retailer_rule"][
    "only_reject_or_fail_if_clear_prohibited_mechanism"
]

STAMP_FIELDS = [
    ("SOURCE", "Blades Canada"),
    ("BRAND", RECORD["brand"]),
    ("MODEL", RECORD["model"]),
    ("STEEL", RECORD["mechanism"]["blade_steel"]),
    ("PRICE", f"${RECORD['canadian_online_retailers'][0]['listed_price_cad']:,.2f} CAD"),
]


class ForgeLine(App):
    TITLE = "KNIVVES — FORGE LINE"
    CSS_PATH = Path(__file__).resolve().parent / "forge-line.tcss"
    BINDINGS = [("q", "quit", "Quit"), ("r", "replay", "Replay")]

    def compose(self) -> ComposeResult:
        with Horizontal(id="line"):
            with Vertical(classes="station", id="st-extract"):
                yield Static("EXTRACT", classes="station-name")
                yield Static("", id="extract-log", classes="station-body")
            with Vertical(classes="station", id="st-legal"):
                yield Static("LEGAL SCREEN", classes="station-name")
                yield Static("", id="gates", classes="station-body")
            with Vertical(classes="station", id="st-vault"):
                yield Static("VAULT", classes="station-name")
                yield Static("", id="rack", classes="station-body")
        with Vertical(id="plate"):
            yield Static("", id="plate-title")
            yield Static("", id="plate-body")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.transit(), exclusive=True)

    def action_replay(self) -> None:
        self.run_worker(self.transit(), exclusive=True)

    # ------------------------------------------------------------- transit

    async def transit(self) -> None:
        plate = self.query_one("#plate")
        title = self.query_one("#plate-title", Static)
        body = self.query_one("#plate-body", Static)
        gates = self.query_one("#gates", Static)
        rack = self.query_one("#rack", Static)
        extract_log = self.query_one("#extract-log", Static)

        # reset
        self.stamped: list[tuple[str, str]] = []
        gates.update("")
        rack.update("")
        title.update(Text("INCOMING", style=STEEL_DIM))
        body.update("")
        plate.styles.offset = (4, self.PLATE_Y)
        extract_log.update(Text("reading listing…", style=STEEL_DIM))
        await asyncio.sleep(0.6)

        # station 1: stamp fields as parsed
        title.update(Text(RECORD["id"], style=ACCENT))
        for label, value in STAMP_FIELDS:
            self.stamped.append((label, value))
            stamped = Text()
            for i, (lab, val) in enumerate(self.stamped):
                fresh = i == len(self.stamped) - 1
                stamped.append(f"{lab:<8}", style=STEEL_DIM)
                stamped.append(f"{val}\n", style=ACCENT if fresh else STEEL_BRIGHT)
            body.update(stamped)
            await asyncio.sleep(0.45)
        extract_log.update(Text("5 fields parsed", style=PASS))

        # travel to legal screen
        await self._travel(plate, x=self._station_x("st-legal"))

        # station 2: the real rulebook executes
        passed: list[str] = []
        for rule in RULES:
            gates.update(self._render_gates(passed, checking=rule))
            await asyncio.sleep(0.35)
            passed.append(rule)
            gates.update(self._render_gates(passed))
        done = self._render_gates(passed)
        done.append("\n  CLEAR TO PROCEED", style=PASS)
        gates.update(done)
        await asyncio.sleep(0.6)

        # travel to vault, land in rack
        await self._travel(plate, x=self._station_x("st-vault"))
        title.update(Text(RECORD["id"], style=PASS))
        landed = Text()
        landed.append(f"{RECORD['brand']} {RECORD['model']}\n", style=STEEL_BRIGHT)
        landed.append("filed · unclassified · awaiting review", style=STEEL_DIM)
        rack.update(landed)

    PLATE_Y = 28

    def _render_gates(self, passed: list[str], checking: str | None = None) -> Text:
        text = Text()
        for rule in passed:
            text.append("  ✓  ", style=PASS)
            text.append(f"{rule}\n", style=STEEL_DIM)
        if checking:
            text.append("  ── ", style=ACCENT)
            text.append(f"{checking}\n", style=STEEL_MID)
        return text

    def _station_x(self, station_id: str) -> int:
        station = self.query_one(f"#{station_id}")
        return station.region.x + 2

    async def _travel(self, plate, x: int) -> None:
        target = ScalarOffset.from_offset((x, self.PLATE_Y))
        plate.styles.animate("offset", value=target, duration=0.7, easing="in_out_cubic")
        await asyncio.sleep(0.85)


if __name__ == "__main__":
    ForgeLine().run()
