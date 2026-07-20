"""The tip system — guidance that never chases the mouse.

House rules for tips:
- One reserved rail per room, at the top-right of where the data stops —
  a fixed column that updates on hover. Tips never float at the cursor
  and never bleed past the content area.
- A tip that has more to say shows a ❯ mark on the rail; clicking the rail
  (or `t`) drops the capsule — a larger panel with the extended text.
  The mark exists ONLY when extended content exists; no dead chrome.
- Escape (or `t` again) closes the capsule.

Rooms declare their tips in a ``TIPS`` dict keyed by widget id, with the
special key ``"__room__"`` as the rail's resting tip. ``TipsMixin`` wires
hover resolution and the capsule for any Screen that composes a TipRail
and a TipCapsule.
"""
from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

from . import laws

ROOM_KEY = "__room__"


@dataclass(frozen=True)
class Tip:
    short: str
    extended: str | None = None


class TipRail(Vertical):
    """The reserved column. Shows the current tip; marks expandable ones."""

    DEFAULT_CSS = f"""
    TipRail {{
        width: 26;
        height: auto;
        margin: 0 0 0 1;
        padding: 0 1;
    }}
    TipRail > .tiprail--label {{
        color: {laws.STEEL_DIM};
        border-bottom: solid {laws.EDGE};
    }}
    TipRail > .tiprail--body {{
        margin-top: 1;
        color: {laws.STEEL_DIM};
    }}
    TipRail > .tiprail--more {{
        margin-top: 1;
        color: {laws.ACCENT};
        display: none;
    }}
    TipRail.expandable > .tiprail--more {{
        display: block;
    }}
    """

    current: Tip | None = None

    def compose(self) -> ComposeResult:
        yield Static("◈ tip", classes="tiprail--label")
        yield Static("", classes="tiprail--body")
        yield Static("❯  t · expand", classes="tiprail--more")

    def show(self, tip: Tip | None) -> None:
        self.current = tip
        body = self.query_one(".tiprail--body", Static)
        body.update(Text(tip.short if tip else "", style=laws.STEEL_DIM))
        self.set_class(bool(tip and tip.extended), "expandable")

    def on_click(self) -> None:
        expand = getattr(self.screen, "action_expand_tip", None)
        if callable(expand):
            expand()


class TipCapsule(Vertical):
    """The dropped-out capsule for tips that need room. Hidden until needed."""

    DEFAULT_CSS = f"""
    TipCapsule {{
        layer: capsule;
        dock: right;
        width: 44;
        height: auto;
        margin: 4 1 0 0;
        background: {laws.SURFACE};
        border: heavy {laws.EDGE_BRIGHT};
        padding: 1 2;
        display: none;
    }}
    TipCapsule.open {{
        display: block;
    }}
    TipCapsule > .capsule--title {{
        color: {laws.STEEL_BRIGHT};
        text-style: bold;
        border-bottom: solid {laws.EDGE};
    }}
    TipCapsule > .capsule--body {{
        margin-top: 1;
        color: {laws.STEEL_MID};
    }}
    TipCapsule > .capsule--hint {{
        margin-top: 1;
        color: {laws.STEEL_DIM};
    }}
    """

    def compose(self) -> ComposeResult:
        yield Static("", classes="capsule--title")
        yield Static("", classes="capsule--body")
        yield Static("esc closes", classes="capsule--hint")

    def show(self, tip: Tip) -> None:
        self.query_one(".capsule--title", Static).update(tip.short)
        self.query_one(".capsule--body", Static).update(tip.extended or "")
        self.add_class("open")

    def hide(self) -> bool:
        if self.has_class("open"):
            self.remove_class("open")
            return True
        return False


class TipsMixin:
    """Hover resolution and capsule control for rooms with a TipRail."""

    TIPS: dict[str, Tip] = {}
    BINDINGS = [Binding("t", "expand_tip", "tip detail", show=False)]

    def _rail(self) -> TipRail:
        return self.query_one(TipRail)  # type: ignore[attr-defined]

    def _capsule(self) -> TipCapsule:
        return self.query_one(TipCapsule)  # type: ignore[attr-defined]

    def show_room_tip(self) -> None:
        self._rail().show(self.TIPS.get(ROOM_KEY))

    def on_enter(self, event: events.Enter) -> None:
        node = event.node
        while node is not None:
            node_id = getattr(node, "id", None)
            if node_id and node_id in self.TIPS:
                self._rail().show(self.TIPS[node_id])
                return
            node = getattr(node, "parent", None)
        self.show_room_tip()

    def action_expand_tip(self) -> None:
        capsule = self._capsule()
        if capsule.hide():
            return
        tip = self._rail().current
        if tip and tip.extended:
            capsule.show(tip)

    def dismiss_capsule(self) -> bool:
        return self._capsule().hide()
