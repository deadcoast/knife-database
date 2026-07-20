"""Working app slice: the real database in a real Textual table.

Click a column header to sort by it. Click again to reverse. Click a row to
see the record. That's it — the feature originally asked for, nothing else.

Run:  python design/proofs/app-slice.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer

from knivves.models import knife_views
from knivves.store import load_database

COLUMNS = [
    ("brand", "Brand"),
    ("model", "Model"),
    ("classification", "Class"),
    ("tags", "Tags"),
    ("blade_steel", "Steel"),
    ("price", "CAD"),
    ("retailer_count", "CA"),
]


def sort_key(column: str):
    def key(value):
        if column in {"price", "retailer_count"}:
            return (value is None, value if value is not None else 0.0)
        return str(value).lower()
    return key


class KnivvesSlice(App):
    TITLE = "knivves — app slice"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.knives = knife_views(load_database(REPO / "knivves" / "data" / "knives.json"))
        self.sort_column: str | None = None
        self.sort_reverse = False

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        for key, label in COLUMNS:
            table.add_column(label, key=key)
        for knife in self.knives:
            table.add_row(
                knife.brand,
                knife.model,
                knife.classification,
                ", ".join(knife.tags) or "—",
                knife.blade_steel,
                knife.price,
                knife.retailer_count,
                key=knife.id,
            )

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        column = event.column_key.value or ""
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        self.sort_column = column
        event.data_table.sort(column, key=sort_key(column), reverse=self.sort_reverse)
        arrow = "↓" if self.sort_reverse else "↑"
        self.sub_title = f"sorted by {column} {arrow}"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        knife = next((k for k in self.knives if k.id == event.row_key.value), None)
        if knife:
            self.notify(
                f"{knife.display_name}\n{knife.blade_steel} · {knife.lock_type} · {knife.price_label}",
                title=knife.id,
                timeout=4,
            )


if __name__ == "__main__":
    KnivvesSlice().run()
