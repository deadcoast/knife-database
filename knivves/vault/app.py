"""KNIVVES VAULT — the application shell.

The Vault is a place: rooms (screens) inside one building (shared masthead,
palette, motion law). Press 1 for the Rack, 2 for the Forge Line. The data
layer is the untouched knivves backend (store + models).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from ..models import KnifeView, knife_views
from ..store import add_knife, load_database, save_database
from .bench import BenchScreen
from .door import BOOT_HOLD, open_door
from .forge import ForgeScreen
from .ledger import LedgerScreen
from .rack import RackScreen


class KnivvesVault(App):
    TITLE = "KNIVVES VAULT"
    CSS_PATH = Path(__file__).resolve().parent / "vault.tcss"
    SCREENS = {
        "rack": RackScreen,
        "forge": ForgeScreen,
        "bench": BenchScreen,
        "ledger": LedgerScreen,
    }
    BINDINGS = [
        ("1", "room('rack')", "The Rack"),
        ("2", "room('forge')", "The Forge Line"),
        ("3", "room('bench')", "The Bench"),
        ("4", "room('ledger')", "The Ledger"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.db_path = db_path
        self.db = load_database(db_path)
        self.knives = knife_views(self.db)
        self.bench_queue: list[KnifeView] = []

    def send_to_bench(self, knife: KnifeView) -> None:
        """A record-object leaves its room for the bench; follow it there."""
        self.bench_queue.append(knife)
        self.action_room("bench")

    def file_record(self, record: dict) -> KnifeView:
        """File a new record into the vault: database write, views refreshed."""
        add_knife(self.db, record)
        save_database(self.db, self.db_path)
        self.knives = knife_views(self.db)
        return KnifeView(record)

    def classify(self, knife_id: str, classification: str | None) -> KnifeView | None:
        """The decision: approve, reject, or clear. Writes the database."""
        for record in self.db.get("knives", []):
            if isinstance(record, dict) and record.get("id") == knife_id:
                record["user_classification"] = classification
                save_database(self.db, self.db_path)
                self.knives = knife_views(self.db)
                return KnifeView(record)
        return None

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """The building's rooms and operations, reachable from the palette."""
        yield from super().get_system_commands(screen)
        yield SystemCommand("The Rack", "Browse the collection", lambda: self.action_room("rack"))
        yield SystemCommand("The Forge Line", "Intake a retailer listing", lambda: self.action_room("forge"))
        yield SystemCommand("The Bench", "Compare two blades", lambda: self.action_room("bench"))
        yield SystemCommand("The Ledger", "Price intelligence", lambda: self.action_room("ledger"))
        yield SystemCommand(
            "Survey the market",
            "Re-read every live listing and record what moved",
            self._palette_survey,
        )

    def _palette_survey(self) -> None:
        self.action_room("ledger")
        self.call_after_refresh(self._start_survey)

    def _start_survey(self) -> None:
        screen = self.screen
        action = getattr(screen, "action_survey", None)
        if callable(action):
            action()

    def on_mount(self) -> None:
        self.push_screen("rack")
        open_door(self.get_screen("rack"), brand="KNIVVES  ╱╱  VAULT", hold=BOOT_HOLD)

    def action_room(self, name: str) -> None:
        screen_type = self.SCREENS.get(name)
        if screen_type is None or isinstance(self.screen, screen_type):
            return
        incoming = self.get_screen(name)
        self.switch_screen(name)
        open_door(incoming)
