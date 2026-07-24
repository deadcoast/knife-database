"""KNIVVES — the application shell.

KNIVVES is the knife database; its visual application is a building of
pages behind one machined door. The vault is a page — the entry hall the
door opens onto — and every working page is a module under ``pages/``
named exactly as its door reads. Shared chrome (masthead, palette,
motion law) frames them all. The data layer is the untouched knivves
backend (store + models).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from ..models import KnifeView, knife_views
from ..store import add_knife, load_database, save_database
from . import laws
from .door import BOOT_HOLD, open_door
from .pages.compare import CompareScreen
from .pages.imports import ImportsScreen
from .pages.library import LibraryScreen
from .pages.market import MarketScreen
from .pages.research import ResearchScreen
from .pages.home import HomeScreen


class KnivvesApp(App):
    TITLE = "KNIVVES"
    CSS_PATH = Path(__file__).resolve().parent / "app.tcss"
    SCREENS = {
        "home": HomeScreen,
        "library": LibraryScreen,
        "imports": ImportsScreen,
        "compare": CompareScreen,
        "market": MarketScreen,
        "research": ResearchScreen,
    }
    BINDINGS = [
        ("0", "room('home')", "Home"),
        ("1", "room('library')", "Library"),
        ("2", "room('imports')", "Import Knives"),
        ("3", "room('compare')", "Compare Models"),
        ("4", "room('market')", "Market Prices"),
        ("5", "room('research')", "Research"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.register_theme(laws.KNIVVES_THEME)
        self.theme = "knivves"
        self.db_path = db_path
        self.db = load_database(db_path)
        self.knives = knife_views(self.db)
        self.compare_queue: list[KnifeView] = []

    def get_theme_variable_defaults(self) -> dict[str, str]:
        """The house variables hold whatever theme is active — the palette
        law cannot be switched off from the palette menu."""
        return laws.THEME_VARIABLES

    def send_to_compare(self, knife: KnifeView) -> None:
        """A record-object leaves its page for the bench; follow it there."""
        self.compare_queue.append(knife)
        self.action_room("compare")

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
        """The building's pages and operations, reachable from the palette."""
        yield from super().get_system_commands(screen)
        yield SystemCommand("Home", "Overview — collection, pages, buy list", lambda: self.action_room("home"))
        yield SystemCommand("Library", "Browse the collection", lambda: self.action_room("library"))
        yield SystemCommand("Import Knives", "Intake a listing URL or an ingestion .md", lambda: self.action_room("imports"))
        yield SystemCommand("Compare Models", "Two blades, measured", lambda: self.action_room("compare"))
        yield SystemCommand("Market Prices", "Valuation, the $150 line, price reads", lambda: self.action_room("market"))
        yield SystemCommand("Research", "The docket of unknowns — fill empty fields from their own listings", lambda: self.action_room("research"))
        yield SystemCommand(
            "Update market prices",
            "Re-read every live listing and record what moved",
            self._palette_survey,
        )

    def _palette_survey(self) -> None:
        self.action_room("market")
        self.call_after_refresh(self._start_survey)

    def _start_survey(self) -> None:
        screen = self.screen
        action = getattr(screen, "action_survey", None)
        if callable(action):
            action()

    def on_mount(self) -> None:
        self.push_screen("home")
        open_door(self.get_screen("home"), brand="KNIVVES", hold=BOOT_HOLD)

    def action_room(self, name: str) -> None:
        screen_type = self.SCREENS.get(name)
        if screen_type is None or isinstance(self.screen, screen_type):
            return
        incoming = self.get_screen(name)
        self.switch_screen(name)
        open_door(incoming)
