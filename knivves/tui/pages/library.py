"""The Rack — the browse room.

The full collection as a sortable, searchable rack. Click a column header
to sort (again to reverse — the active header carries the direction arrow
in accent). Click a knife and its Plate travels in from the right edge:
the record arrives as an object, per the motion law.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.coordinate import Coordinate
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input, Static

from ...models import KnifeView, new_brands

if TYPE_CHECKING:
    from .app import KnivvesApp
from ... import buylist as buylist_mod
from .. import laws
from ..masthead import Masthead
from ..plate import Plate
from ..reserve import Reserve
from ..tips import ROOM_KEY, Tip, TipCapsule, TipRail, TipsMixin

COLUMNS = [
    ("brand", "Brand", 16),
    ("model", "Model", 36),
    ("classification", "Class", 14),
    ("steel", "Steel", 18),
    ("price", "CAD", 12),
    ("tags", "Tags", 20),
]

ARROW_UP = " ▲"
ARROW_DOWN = " ▼"
PLATE_HIDDEN_X = 50
RESERVE_HIDDEN_X = 56


def cell_sort_key(column: str):
    def key(value):
        plain = value.plain if isinstance(value, Text) else str(value)
        if column == "price":
            cleaned = plain.replace("$", "").replace(",", "").split("–")[0].strip()
            try:
                return (0, float(cleaned))
            except ValueError:
                return (1, 0.0)
        return (0, plain.lower())
    return key


class LibraryScreen(TipsMixin, Screen):
    CSS_PATH = "library.tcss"

    BINDINGS = [
        ("slash", "focus_search", "Search"),
        ("escape", "close_plate", "Close plate"),
        ("b", "send_bench", "Send to bench"),
        ("y", "toggle_reserve", "The Reserve"),
        ("a", "classify('approved')", "Approve"),
        ("x", "classify('rejected')", "Reject"),
        Binding("u", "classify('clear')", "Unreview", show=False),
        Binding("t", "expand_tip", "tip detail", show=False),
    ]

    TIPS = {
        ROOM_KEY: Tip("the library — browse, sort, send"),
        "rack-search": Tip(
            "live filter across every field",
            "matches brand, model, steel, lock,\ntags, notes, retailer — anything\nthe record knows\n\n"
            "try: magnacut · assisted · affordable\n\n/ focuses the search\nesc clears it",
        ),
        "rack-table": Tip(
            "click a header to sort · again reverses",
            "enter or click a row — its plate\ntravels in\n\nb — send the row to the bench\n\n"
            "a approve · x reject · u clear —\nthe decision writes the database\nand the row recolors live\n\n"
            "the active sort reads on the\nmasthead beside the room name",
        ),
        "rack-plate": Tip(
            "the record plate — class colors its edge",
            "approved green · rejected red ·\nunreviewed steel\n\n"
            "this same plate is stamped on the\nforge line and sits on the bench —\none object, every room",
        ),
        "rack-reserve": Tip(
            "the reserve — buy list priorities",
            "y opens and closes it\n\npriority 1 is the next acquisition\n"
            "Σ is the running cost of the ladder\n\n"
            "the ledger file's BuyList section\nis the source of truth:\nknivves add <file.md>",
        ),
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sort_column: str | None = None
        self.sort_reverse = False

    @property
    def knivves(self) -> "KnivvesApp":
        return cast("KnivvesApp", self.app)

    @property
    def knives(self) -> list[KnifeView]:
        return self.knivves.knives

    def compose(self) -> ComposeResult:
        yield Masthead("LIBRARY")
        yield Input(placeholder="/ searches the vault — brand, steel, lock, section …", id="rack-search")
        yield Plate(id="rack-plate")
        yield Reserve(id="rack-reserve")
        with Horizontal(id="rack-body"):
            yield DataTable(id="rack-table")
            yield Static(
                "no blades match your search\n\nesc clears the filter",
                id="rack-empty",
            )
            yield TipRail()
        yield TipCapsule()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Masthead).update_stats(self.knives)
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        for key, label, width in COLUMNS:
            table.add_column(label + "  ", key=key, width=width)
        self._fill(self.knives)
        table.focus()
        self.show_room_tip()

    def on_screen_resume(self, event: ScreenResume) -> None:
        """Coming back to the rack: reflect anything filed while away."""
        self.query_one(Masthead).update_stats(self.knives)
        self._fill(self._visible())
        self._apply_sort()

    # ------------------------------------------------------------- data

    def _fill(self, knives: list[KnifeView]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        search = self.query_one("#rack-search", Input)
        search.border_subtitle = f"{len(knives)} / {len(self.knives)}"
        self.query_one("#rack-empty", Static).display = not knives
        table.display = bool(knives)
        fresh_brands = new_brands(self.knives)
        for k in knives:
            cls = k.classification
            # ★new aligns in the gutter: end of Brand marks a new maker,
            # start of Model marks a new blade — readable at a glance
            brand_cell = Text(k.brand, style=laws.STEEL_BRIGHT)
            if k.brand.lower() in fresh_brands:
                brand_cell.append(" ★new", style=f"bold {laws.FRESH}")
            model_cell = Text()
            if k.is_new:
                model_cell.append("★new ", style=f"bold {laws.FRESH}")
            model_cell.append(k.model, style=laws.STEEL_MID)
            sections_cell = Text()
            if k.buy_priority:
                sections_cell.append(f"⬖{k.buy_priority} ", style=laws.ACCENT)
            sections_cell.append(", ".join(k.tags) or ("—" if not sections_cell.plain else ""), style=laws.STEEL_DIM)
            table.add_row(
                brand_cell,
                model_cell,
                Text(cls, style=laws.CLASS_COLORS.get(cls, laws.STEEL_MID)),
                Text(k.blade_steel if k.blade_steel != "Unknown" else "—", style=laws.STEEL_MID),
                Text(k.price_label, style=laws.ACCENT if k.price else laws.STEEL_DIM, justify="right"),
                sections_cell,
                key=k.id,
            )

    def _visible(self) -> list[KnifeView]:
        query = self.query_one("#rack-search", Input).value.strip().lower()
        if not query:
            return self.knives
        return [k for k in self.knives if query in k.haystack()]

    # ------------------------------------------------------------- events

    def on_input_changed(self, event: Input.Changed) -> None:
        self._fill(self._visible())
        self._apply_sort()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        column = event.column_key.value or ""
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        previous, self.sort_column = self.sort_column, column
        table = event.data_table
        for col_key, col in table.columns.items():
            base = next(label for key, label, _ in COLUMNS if key == col_key.value)
            if col_key.value == column:
                arrow = ARROW_DOWN if self.sort_reverse else ARROW_UP
                col.label = Text(base + arrow, style=laws.ACCENT)
            elif col_key.value == previous:
                col.label = Text(base + "  ")
        self._apply_sort()
        table.refresh()
        base = next(label for key, label, _ in COLUMNS if key == column)
        arrow = "▼" if self.sort_reverse else "▲"
        self.query_one(Masthead).set_context(f"sorted by {base.lower()} {arrow}")

    def _apply_sort(self) -> None:
        if self.sort_column:
            self.query_one(DataTable).sort(
                self.sort_column, key=cell_sort_key(self.sort_column), reverse=self.sort_reverse
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        knife = next((k for k in self.knives if k.id == event.row_key.value), None)
        if knife is None:
            return
        self._plate_knife_id = knife.id
        plate = self.query_one(Plate)
        plate.set_knife(knife)
        if not plate.has_class("open"):
            plate.add_class("open")
            plate.styles.offset = (PLATE_HIDDEN_X, 0)
        laws.travel(plate, 0, 0, duration=0.35)
        # depth: the rack recedes as the plate arrives
        laws.travel(self.query_one("#rack-body"), -2, 0, duration=0.35)

    def _judgment_target(self) -> str | None:
        """The open plate's knife if one is open, else the highlighted row."""
        plate = self.query_one(Plate)
        if plate.has_class("open") and getattr(self, "_plate_knife_id", None):
            return self._plate_knife_id
        table = self.query_one(DataTable)
        if not table.row_count:
            return None
        return table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0)).row_key.value

    def action_classify(self, classification: str) -> None:
        target = self._judgment_target()
        if target is None:
            return
        verdict = None if classification == "clear" else classification
        view = self.knivves.classify(target, verdict)
        if view is None:
            return
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        self._fill(self._visible())
        self._apply_sort()
        if table.row_count:
            table.move_cursor(row=min(cursor, table.row_count - 1))
        plate = self.query_one(Plate)
        if plate.has_class("open") and getattr(self, "_plate_knife_id", None) == view.id:
            plate.set_knife(view)
        self.query_one(Masthead).update_stats(self.knives)

    def action_focus_search(self) -> None:
        self.query_one("#rack-search", Input).focus()

    def action_send_bench(self) -> None:
        """Send the highlighted knife's plate to the bench and follow it."""
        table = self.query_one(DataTable)
        if not table.row_count:
            return
        row_key = table.coordinate_to_cell_key(
            Coordinate(table.cursor_row, 0)
        ).row_key
        knife = next((k for k in self.knives if k.id == row_key.value), None)
        if knife:
            self.knivves.send_to_compare(knife)

    def action_toggle_reserve(self) -> None:
        """The buy list ledger travels in beside the rack (and back out)."""
        reserve = self.query_one(Reserve)
        if reserve.has_class("open"):
            self._retire_reserve(reserve)
            return
        plate = self.query_one(Plate)
        if plate.has_class("open"):
            laws.travel(plate, PLATE_HIDDEN_X, 0, duration=0.35)
            self.set_timer(0.4, lambda: plate.remove_class("open"))
        db = self.knivves.db
        views = buylist_mod.buylist_views(db)
        reserve.set_reserve(views, buylist_mod.cumulative(views))
        reserve.add_class("open")
        reserve.styles.offset = (RESERVE_HIDDEN_X, 0)
        laws.travel(reserve, 0, 0, duration=0.35)
        laws.travel(self.query_one("#rack-body"), -2, 0, duration=0.35)
        self._rail().show(self.TIPS["rack-reserve"])

    def _retire_reserve(self, reserve: Reserve) -> None:
        laws.travel(reserve, RESERVE_HIDDEN_X, 0, duration=0.35)
        self.set_timer(0.4, lambda: reserve.remove_class("open"))
        laws.travel(self.query_one("#rack-body"), 0, 0, duration=0.35)

    def action_close_plate(self) -> None:
        if self.dismiss_capsule():
            return
        reserve = self.query_one(Reserve)
        if reserve.has_class("open"):
            self._retire_reserve(reserve)
            self.query_one(DataTable).focus()
            return
        plate = self.query_one(Plate)
        if plate.has_class("open"):
            laws.travel(plate, PLATE_HIDDEN_X, 0, duration=0.35)
            self.set_timer(0.4, lambda: plate.remove_class("open"))
            # the rack steps forward again as the plate departs
            laws.travel(self.query_one("#rack-body"), 0, 0, duration=0.35)
        search = self.query_one("#rack-search", Input)
        if search.value:
            search.value = ""
        self.query_one(DataTable).focus()
