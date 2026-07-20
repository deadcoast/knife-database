"""App slice 2 — Armory Vault as interface design.

The vault aesthetic applied where it belongs: the application itself.
Machined dark theme, live stats masthead, the rack (sortable table with
visible sort direction), the plate (docked record panel), live search.

Run:  python design/proofs/app-slice-2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Input, Static

from knivves.models import KnifeView, knife_views
from knivves.store import load_database

STEEL_BRIGHT = "#dde6ee"
STEEL_MID = "#8b96a0"
STEEL_DIM = "#5c6670"
ACCENT = "#d7a455"
CLASS_COLORS = {"approved": "#79b473", "rejected": "#c05b4d", "unclassified": "#6b7680"}

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


def cell_sort_key(column: str):
    def key(value):
        plain = value.plain if isinstance(value, Text) else str(value)
        if column == "price":
            cleaned = plain.replace("$", "").replace(",", "").strip()
            try:
                return (0, float(cleaned))
            except ValueError:
                return (1, 0.0)
        return (0, plain.lower())
    return key


class KnivvesVaultSlice(App):
    TITLE = "KNIVVES"
    CSS_PATH = Path(__file__).resolve().parent / "app-slice-2.tcss"
    BINDINGS = [
        ("escape", "close_plate", "Close plate"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.knives = knife_views(load_database(REPO / "knivves" / "data" / "knives.json"))
        self.sort_column: str | None = None
        self.sort_reverse = False

    # ------------------------------------------------------------- layout

    def compose(self) -> ComposeResult:
        with Horizontal(id="masthead"):
            yield Static("KNIVVES ╱╱ VAULT", id="brand")
            yield Static(self._stats_line(), id="stats")
        yield Input(placeholder="search the vault — brand, steel, lock, tag …", id="search")
        with Vertical(id="record"):
            yield Static("", id="record-title")
            yield Static("", id="record-id")
            yield Static("", id="record-body")
        yield DataTable(id="rack")
        yield Footer()

    def _stats_line(self) -> Text:
        prices = [k.price for k in self.knives if k.price is not None]
        avg = sum(prices) / len(prices) if prices else 0
        approved = sum(1 for k in self.knives if k.classification == "approved")
        line = Text()
        line.append(f"{len(self.knives)} blades", style=STEEL_MID)
        line.append("  ·  ", style=STEEL_DIM)
        line.append(f"{approved} approved", style=CLASS_COLORS["approved"])
        line.append("  ·  ", style=STEEL_DIM)
        line.append(f"avg ${avg:,.0f} CAD", style=STEEL_MID)
        return line

    def on_mount(self) -> None:
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
                Text(k.brand, style=STEEL_BRIGHT),
                Text(k.model, style=STEEL_MID),
                Text(cls, style=CLASS_COLORS.get(cls, STEEL_MID)),
                Text(k.blade_steel if k.blade_steel != "Unknown" else "—", style=STEEL_MID),
                Text(k.price_label, style=ACCENT if k.price else STEEL_DIM, justify="right"),
                Text(", ".join(k.tags) or "—", style=STEEL_DIM),
                key=k.id,
            )

    def _visible_knives(self) -> list[KnifeView]:
        query = self.query_one("#search", Input).value.strip().lower()
        if not query:
            return self.knives
        return [k for k in self.knives if query in k.haystack()]

    # ------------------------------------------------------------- events

    def on_input_changed(self, event: Input.Changed) -> None:
        self._fill(self._visible_knives())
        if self.sort_column:
            self._apply_sort()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        column = event.column_key.value or ""
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        previous, self.sort_column = self.sort_column, column
        table = event.data_table
        for key, label, _ in COLUMNS:
            if key == column:
                arrow = ARROW_DOWN if self.sort_reverse else ARROW_UP
                table.columns[event.column_key].label = Text(label + arrow, style=ACCENT)
            elif key == previous:
                for col_key, col in table.columns.items():
                    if col_key.value == key:
                        col.label = Text(label + "  ")
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
        self.query_one("#record-title", Static).update(knife.display_name)
        self.query_one("#record-id", Static).update(knife.id)
        body = Text()

        def field(label: str, value: str, style: str = STEEL_BRIGHT) -> None:
            body.append(f"{label:<10}", style=STEEL_DIM)
            body.append(f"{value}\n", style=style)

        field("CLASS", knife.classification, CLASS_COLORS.get(knife.classification, STEEL_MID))
        field("STEEL", knife.blade_steel)
        field("LOCK", knife.lock_type)
        field("OPEN", knife.opening_method)
        field("LENGTH", knife.blade_length)
        field("PRICE", knife.price_label, ACCENT)
        best = knife.best_retailer
        if best:
            field("SOURCE", str(best.get("retailer") or "—"))
            field("STOCK", str(best.get("availability") or "—"))
        if knife.tags:
            field("TAGS", ", ".join(knife.tags))
        if knife.notes:
            body.append("\n")
            body.append(knife.notes, style=STEEL_DIM)
        self.query_one("#record-body", Static).update(body)
        self.query_one("#record").add_class("open")

    def action_close_plate(self) -> None:
        self.query_one("#record").remove_class("open")
        search = self.query_one("#search", Input)
        if search.value:
            search.value = ""


if __name__ == "__main__":
    KnivvesVaultSlice().run()
