"""The Rack — the browse room.

The full collection as a sortable, searchable rack. Click a column header
to sort (again to reverse — the active header carries the direction arrow
in accent). Click a knife and its Plate travels in from the right edge:
the record arrives as an object, per the motion law.
"""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input

from ..models import KnifeView
from . import laws
from .masthead import Masthead
from .plate import Plate

COLUMNS = [
    ("brand", "Brand", 16),
    ("model", "Model", 36),
    ("classification", "Class", 14),
    ("steel", "Steel", 16),
    ("price", "CAD", 12),
    ("tags", "Tags", 16),
]

ARROW_UP = " ▲"
ARROW_DOWN = " ▼"
PLATE_HIDDEN_X = 50


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


class RackScreen(Screen):
    BINDINGS = [("escape", "close_plate", "Close plate")]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sort_column: str | None = None
        self.sort_reverse = False

    @property
    def knives(self) -> list[KnifeView]:
        return self.app.knives

    def compose(self) -> ComposeResult:
        yield Masthead("THE RACK")
        yield Input(placeholder="search the vault — brand, steel, lock, tag …", id="rack-search")
        yield Plate(id="rack-plate")
        yield DataTable(id="rack-table")
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

    # ------------------------------------------------------------- data

    def _fill(self, knives: list[KnifeView]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for k in knives:
            cls = k.classification
            table.add_row(
                Text(k.brand, style=laws.STEEL_BRIGHT),
                Text(k.model, style=laws.STEEL_MID),
                Text(cls, style=laws.CLASS_COLORS.get(cls, laws.STEEL_MID)),
                Text(k.blade_steel if k.blade_steel != "Unknown" else "—", style=laws.STEEL_MID),
                Text(k.price_label, style=laws.ACCENT if k.price else laws.STEEL_DIM, justify="right"),
                Text(", ".join(k.tags) or "—", style=laws.STEEL_DIM),
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

    def _apply_sort(self) -> None:
        if self.sort_column:
            self.query_one(DataTable).sort(
                self.sort_column, key=cell_sort_key(self.sort_column), reverse=self.sort_reverse
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        knife = next((k for k in self.knives if k.id == event.row_key.value), None)
        if knife is None:
            return
        plate = self.query_one(Plate)
        plate.set_knife(knife)
        if not plate.has_class("open"):
            plate.add_class("open")
            plate.styles.offset = (PLATE_HIDDEN_X, 0)
        laws.travel(plate, 0, 0, duration=0.35)

    def action_close_plate(self) -> None:
        plate = self.query_one(Plate)
        if plate.has_class("open"):
            laws.travel(plate, PLATE_HIDDEN_X, 0, duration=0.35)
            self.set_timer(0.4, lambda: plate.remove_class("open"))
        search = self.query_one("#rack-search", Input)
        if search.value:
            search.value = ""
