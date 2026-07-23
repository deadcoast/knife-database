"""The Reserve — the buy list as a fixture of the room.

The acquisition shortlist, racked in descending desire: priority 1 is the
next blade to leave the wishlist and enter the vault. The panel docks
beside the Rack (press ``y``) and travels in under the motion law, the
same way the Plate does — the reserve ledger is an object in the room,
not a popup.

Each rung shows its priority stamp, the blade, its price, and the running
total — "what would the top of the ladder cost me" is the number the
reserve exists to answer.
"""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..models import KnifeView
from . import laws


class Reserve(Vertical):
    DEFAULT_CSS = f"""
    Reserve {{
        width: 52;
        height: auto;
        max-height: 100%;
        background: {laws.SURFACE};
        border: heavy {laws.ACCENT};
        padding: 1 2;
    }}
    Reserve > .reserve--title {{
        text-style: bold;
        color: {laws.STEEL_BRIGHT};
        border-bottom: solid {laws.EDGE};
    }}
    Reserve > .reserve--subtitle {{
        color: {laws.STEEL_DIM};
    }}
    Reserve > .reserve--body {{
        margin-top: 1;
    }}
    Reserve > .reserve--footer {{
        margin-top: 1;
        border-top: solid {laws.EDGE};
        color: {laws.STEEL_MID};
    }}
    """

    def compose(self) -> ComposeResult:
        yield Static("THE RESERVE", classes="reserve--title")
        yield Static("buy list · descending priority", classes="reserve--subtitle")
        yield Static("", classes="reserve--body")
        yield Static("", classes="reserve--footer")

    def set_reserve(self, views: list[tuple[int, KnifeView]], totals: list[float], *, limit: int = 12) -> None:
        body = Text()
        if not views:
            body.append("the reserve is empty\n\n", style=laws.STEEL_MID)
            body.append("ingest a ledger with a BuyList\nsection:  knivves add <file.md>", style=laws.STEEL_DIM)
            self.query_one(".reserve--body", Static).update(body)
            self.query_one(".reserve--footer", Static).update("")
            return
        for (priority, knife), running in list(zip(views, totals))[:limit]:
            body.append(f"{priority:>2} ", style=f"bold {laws.ACCENT}")
            body.append(knife.display_name[:40], style=laws.STEEL_BRIGHT)
            if knife.is_new:
                body.append("  ★new", style=laws.FRESH)
            body.append("\n   ")
            body.append(f"{knife.price_label:<14}", style=laws.STEEL_MID)
            body.append(f"Σ ${running:,.0f}", style=laws.STEEL_DIM)
            body.append("\n")
        if len(views) > limit:
            body.append(f"\n   … {len(views) - limit} deeper in the reserve", style=laws.STEEL_DIM)
        self.query_one(".reserve--body", Static).update(body)

        priced = sum(1 for _, k in views if k.price is not None)
        total = totals[-1] if totals else 0.0
        footer = Text()
        footer.append_text(laws.field("ladder", f"{len(views)} priorities", laws.STEEL_BRIGHT))
        footer.append("\n")
        footer.append_text(laws.field("cost", f"${total:,.2f} CAD across {priced} priced", laws.ACCENT))
        self.query_one(".reserve--footer", Static).update(footer)
