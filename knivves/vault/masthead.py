"""The Masthead — the building's constant frame.

Every room composes the same masthead: brand on the left, live vault
statistics on the right. Rooms change; the building does not.
"""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from ..models import KnifeView
from . import laws


class Masthead(Horizontal):
    DEFAULT_CSS = f"""
    Masthead {{
        dock: top;
        height: 3;
        background: {laws.SURFACE};
        border-bottom: heavy {laws.EDGE};
        padding: 0 2;
    }}
    Masthead > .masthead--brand {{
        width: auto;
        content-align: left middle;
        text-style: bold;
        color: {laws.STEEL_BRIGHT};
    }}
    Masthead > .masthead--room {{
        width: auto;
        content-align: left middle;
        margin-left: 2;
        color: {laws.ACCENT};
    }}
    Masthead > .masthead--context {{
        width: auto;
        content-align: left middle;
        margin-left: 2;
        color: {laws.STEEL_DIM};
    }}
    Masthead > .masthead--stats {{
        width: 1fr;
        content-align: right middle;
        color: {laws.STEEL_DIM};
    }}
    """

    def __init__(self, room: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._room = room

    def compose(self) -> ComposeResult:
        yield Static("KNIVVES ╱╱ VAULT", classes="masthead--brand")
        yield Static(f"· {self._room}", classes="masthead--room")
        yield Static("", classes="masthead--context")
        yield Static("", classes="masthead--stats")

    def set_context(self, text: str) -> None:
        """Room-state readout beside the room name (e.g. active sort)."""
        self.query_one(".masthead--context", Static).update(text)

    def update_stats(self, knives: list[KnifeView]) -> None:
        prices = [k.price for k in knives if k.price is not None]
        avg = sum(prices) / len(prices) if prices else 0
        approved = sum(1 for k in knives if k.classification == "approved")
        line = Text()
        line.append(f"{len(knives)} blades", style=laws.STEEL_MID)
        line.append("  ·  ", style=laws.STEEL_DIM)
        line.append(f"{approved} approved", style=laws.CLASS_COLORS["approved"])
        line.append("  ·  ", style=laws.STEEL_DIM)
        line.append(f"avg ${avg:,.0f} CAD", style=laws.STEEL_MID)
        self.query_one(".masthead--stats", Static).update(line)
