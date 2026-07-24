"""The Plate — the record as a physical object.

One widget class, every room. The plate stamped on the Forge Line is the
same object that docks beside the Rack and sits on the Bench: object
permanence is structural, not a styling convention. A room never draws its
own record view; it mounts a Plate.

Two modes:
- ``set_knife(view)``   — show a complete record at once (Rack, Bench).
- ``begin(title)`` then ``stamp(label, value)`` — assemble a record field
  by field, the freshest stamp marked in accent (Forge Line).
"""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..models import KnifeView
from ..research import audit_record
from . import laws


class Plate(Vertical):
    DEFAULT_CSS = """
    Plate {
        width: 46;
        height: auto;
        max-height: 100%;
        background: $surface-high;
        border-top: heavy $bevel-light;
        border-left: thick $edge-bright;
        border-bottom: heavy $bevel-shadow;
        border-right: heavy $bevel-shadow;
        padding: 1 2;
    }
    Plate > .plate--title {
        text-style: bold;
        color: $steel-bright;
        border-bottom: solid $edge;
    }
    Plate > .plate--id {
        color: $steel-dim;
    }
    Plate > .plate--body {
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stamped: list[tuple[str, str, str]] = []

    def compose(self) -> ComposeResult:
        yield Static("", classes="plate--title")
        yield Static("", classes="plate--id")
        yield Static("", classes="plate--body")

    # ------------------------------------------------------------- full mode

    def set_knife(self, knife: KnifeView) -> None:
        """Show a complete record; the left spine takes the class color —
        an inlay strip, not a glowing frame."""
        self._stamped = []
        cls = knife.classification
        self.styles.border_left = ("thick", laws.CLASS_COLORS.get(cls, laws.EDGE_BRIGHT))
        self._title(knife.display_name, knife.id)
        body = Text()

        def fit(value: str) -> str:
            # one engraved line per fact — a long value never wraps under
            # the label column, it is cut and marked cut
            return value if len(value) <= 30 else value[:29] + "…"

        rows: list[tuple[str, str, str]] = [
            ("class", cls, laws.CLASS_COLORS.get(cls, laws.STEEL_MID)),
            ("steel", fit(knife.blade_steel), laws.STEEL_BRIGHT),
            ("lock", fit(knife.lock_type), laws.STEEL_BRIGHT),
            ("open", fit(knife.opening_method), laws.STEEL_BRIGHT),
            ("length", fit(knife.blade_length), laws.STEEL_BRIGHT),
            ("price", knife.price_label, laws.ACCENT),
        ]
        best = knife.best_retailer
        if best:
            rows.append(("source", fit(str(best.get("retailer") or "—")), laws.STEEL_BRIGHT))
            rows.append(("stock", fit(str(best.get("availability") or "—")), laws.STEEL_BRIGHT))
        if knife.tags:
            rows.append(("tags", fit(", ".join(knife.tags)), laws.STEEL_MID))
        gaps = audit_record(knife.raw)
        if gaps:
            # the object carries its incompleteness into every room —
            # the Research desk (door 5) is where it gets filled
            rows.append(("gaps", f"{len(gaps)} unresearched", laws.ACCENT))
        for label, value, style in rows:
            body.append_text(laws.field(label, value, style))
            body.append("\n")
        if knife.notes:
            body.append("\n")
            body.append(knife.notes, style=laws.STEEL_DIM)
        self._body(body)

    # ------------------------------------------------------ incremental mode

    def begin(self, title: str, subtitle: str = "") -> None:
        """Blank plate on the line, awaiting stamps. In-transit plates
        keep every engraving to one line — they must seat in the tray."""
        self._stamped = []
        self.styles.border_left = ("thick", laws.EDGE_BRIGHT)
        self._title(
            title if len(title) <= 40 else title[:39] + "…",
            subtitle if len(subtitle) <= 40 else subtitle[:39] + "…",
        )
        self._body(Text())

    def stamp(self, label: str, value: str) -> None:
        """Stamp one field; the freshest stamp reads in accent."""
        if len(value) > 28:
            value = value[:27] + "…"
        self._stamped.append((label, value, laws.STEEL_BRIGHT))
        body = Text()
        for i, (lab, val, style) in enumerate(self._stamped):
            fresh = i == len(self._stamped) - 1
            body.append_text(laws.field(lab, val, laws.ACCENT if fresh else style))
            body.append("\n")
        self._body(body)

    # ------------------------------------------------------------- internals

    def _title(self, title: str, subtitle: str) -> None:
        self.query_one(".plate--title", Static).update(title)
        self.query_one(".plate--id", Static).update(subtitle)

    def _body(self, body: Text) -> None:
        self.query_one(".plate--body", Static).update(body)
