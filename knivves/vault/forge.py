"""The Forge Line — the intake room.

A record enters the vault as a physical process: a blank Plate appears at
EXTRACT and its fields stamp on as parsed; it travels to LEGAL SCREEN where
the database's actual prohibited-mechanism rulebook executes gate by gate;
cleared, it travels on and files into the vault.

This room currently runs a deterministic transit on a real record so the
motion can be judged identically on every replay. Live URL intake wires the
proven scraper into the same transit — the room's next fitting.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static

from . import laws

if TYPE_CHECKING:
    from .app import KnivvesVault
from .masthead import Masthead
from .plate import Plate

PLATE_Y = 26


class ForgeScreen(Screen):
    BINDINGS = [("r", "replay", "Replay transit")]

    def compose(self) -> ComposeResult:
        yield Masthead("THE FORGE LINE")
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
        self.run_worker(self.transit(), exclusive=True)

    def action_replay(self) -> None:
        self.run_worker(self.transit(), exclusive=True)

    # ------------------------------------------------------------- transit

    def _sample(self):
        knives = self.vault.knives
        return next((k for k in knives if k.price and k.blade_steel != "Unknown"), knives[0])

    def _rules(self) -> list[str]:
        rule = self.vault.db.get("workflow_rules", {}).get("canadian_online_retailer_rule", {})
        return list(rule.get("only_reject_or_fail_if_clear_prohibited_mechanism", []))

    async def transit(self) -> None:
        knife = self._sample()
        plate = self.query_one(Plate)
        gates = self.query_one("#gates", Static)
        filed = self.query_one("#filed", Static)
        extract_log = self.query_one("#extract-log", Static)

        gates.update("")
        filed.update("")
        plate.styles.offset = (4, PLATE_Y)
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
            gates.update(self._render_gates(passed))
        done = self._render_gates(passed)
        done.append("\n  CLEAR TO PROCEED", style=laws.PASS)
        gates.update(done)
        await asyncio.sleep(0.6)

        await self._travel_to("st-vault", plate)
        landed = Text()
        landed.append(f"{knife.display_name}\n", style=laws.STEEL_BRIGHT)
        landed.append("filed · awaiting review", style=laws.STEEL_DIM)
        filed.update(landed)

    def _render_gates(self, passed: list[str], checking: str | None = None) -> Text:
        text = Text()
        for rule in passed:
            text.append("  ✓  ", style=laws.PASS)
            text.append(f"{rule}\n", style=laws.STEEL_DIM)
        if checking:
            text.append("  ── ", style=laws.ACCENT)
            text.append(f"{checking}\n", style=laws.STEEL_MID)
        return text

    async def _travel_to(self, station_id: str, plate: Plate) -> None:
        x = self.query_one(f"#{station_id}").region.x + 2
        laws.travel(plate, x, PLATE_Y)
        await asyncio.sleep(laws.TRAVEL_DURATION + 0.15)
