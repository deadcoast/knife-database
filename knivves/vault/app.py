"""KNIVVES VAULT — the application shell.

The Vault is a place: rooms (screens) inside one building (shared masthead,
palette, motion law). Press 1 for the Rack, 2 for the Forge Line. The data
layer is the untouched knivves backend (store + models).
"""
from __future__ import annotations

from pathlib import Path

from textual.app import App

from ..models import knife_views
from ..store import load_database
from .forge import ForgeScreen
from .rack import RackScreen


class KnivvesVault(App):
    TITLE = "KNIVVES VAULT"
    CSS_PATH = Path(__file__).resolve().parent / "vault.tcss"
    SCREENS = {"rack": RackScreen, "forge": ForgeScreen}
    BINDINGS = [
        ("1", "room('rack')", "The Rack"),
        ("2", "room('forge')", "The Forge Line"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.db = load_database(db_path)
        self.knives = knife_views(self.db)

    def on_mount(self) -> None:
        self.push_screen("rack")

    def action_room(self, name: str) -> None:
        if self.screen != self.SCREENS.get(name):
            self.switch_screen(name)
