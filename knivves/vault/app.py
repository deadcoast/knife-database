"""KNIVVES VAULT — the application shell.

The Vault is a place: rooms (screens) inside one building (shared masthead,
palette, motion law). Press 1 for the Rack, 2 for the Forge Line. The data
layer is the untouched knivves backend (store + models).
"""
from __future__ import annotations

from pathlib import Path

from textual.app import App

from ..models import KnifeView, knife_views
from ..store import load_database
from .bench import BenchScreen
from .forge import ForgeScreen
from .rack import RackScreen


class KnivvesVault(App):
    TITLE = "KNIVVES VAULT"
    CSS_PATH = Path(__file__).resolve().parent / "vault.tcss"
    SCREENS = {"rack": RackScreen, "forge": ForgeScreen, "bench": BenchScreen}
    BINDINGS = [
        ("1", "room('rack')", "The Rack"),
        ("2", "room('forge')", "The Forge Line"),
        ("3", "room('bench')", "The Bench"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.db = load_database(db_path)
        self.knives = knife_views(self.db)
        self.bench_queue: list[KnifeView] = []

    def send_to_bench(self, knife: KnifeView) -> None:
        """A record-object leaves its room for the bench; follow it there."""
        self.bench_queue.append(knife)
        self.action_room("bench")

    def on_mount(self) -> None:
        self.push_screen("rack")

    def action_room(self, name: str) -> None:
        if self.screen != self.SCREENS.get(name):
            self.switch_screen(name)
