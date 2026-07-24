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

    DEFAULT_CSS = """
    TipRail {
        width: 26;
        height: 100%;
        margin: 0 0 0 1;
        padding: 1 1 0 1;
        background: $surface-low;
        border-top: round $bevel-shadow;
        border-left: round $bevel-shadow;
        border-bottom: round $bevel-light;
        border-right: round $bevel-light;
    }
    TipRail > .tiprail--label {
        color: $steel-dim;
        border-bottom: solid $edge;
    }
    TipRail > .tiprail--body {
        margin-top: 1;
        color: $steel-dim;
    }
    TipRail > .tiprail--more {
        margin-top: 1;
        color: $accent;
        display: none;
    }
    TipRail.expandable > .tiprail--more {
        display: block;
    }
    TipRail > .tiprail--keys {
        height: auto;
        color: $steel-dim;
        border-top: solid $edge;
        padding-top: 1;
    }
    """

    current: Tip | None = None

    def compose(self) -> ComposeResult:
        yield Static("◈ tip", classes="tiprail--label")
        yield Static("", classes="tiprail--body")
        yield Static("❯  t · expand", classes="tiprail--more")
        yield Static("", classes="tiprail--keys")

    def show(self, tip: Tip | None) -> None:
        self.current = tip
        body = self.query_one(".tiprail--body", Static)
        body.update(Text(tip.short if tip else "", style=laws.STEEL_DIM))
        self.set_class(bool(tip and tip.extended), "expandable")

    def set_keys(self, pairs: list[tuple[str, str]]) -> None:
        """The room's key card, printed at the rail's foot."""
        text = Text()
        for key, does in pairs:
            text.append(f"{key:>3} ", style=laws.STEEL_MID)
            text.append(f"{does}\n", style=laws.STEEL_DIM)
        keys = self.query_one(".tiprail--keys", Static)
        # measured height, stated outright — auto-measure under a 1fr
        # sibling has under-counted and let the card clip off the rail
        keys.styles.height = len(pairs) + 2
        keys.update(text)

    def on_click(self) -> None:
        expand = getattr(self.screen, "action_expand_tip", None)
        if callable(expand):
            expand()


class TipCapsule(Vertical):
    """The dropped-out capsule for tips that need room. Hidden until needed."""

    DEFAULT_CSS = """
    TipCapsule {
        layer: capsule;
        dock: right;
        width: 44;
        height: auto;
        margin: 4 1 0 0;
        background: $surface-high;
        border-top: heavy $bevel-light;
        border-left: heavy $bevel-light;
        border-bottom: heavy $bevel-shadow;
        border-right: heavy $bevel-shadow;
        padding: 1 2;
        display: none;
    }
    TipCapsule.open {
        display: block;
    }
    TipCapsule > .capsule--title {
        color: $steel-bright;
        text-style: bold;
        border-bottom: solid $edge;
    }
    TipCapsule > .capsule--body {
        margin-top: 1;
        color: $steel-mid;
    }
    TipCapsule > .capsule--hint {
        margin-top: 1;
        color: $steel-dim;
    }
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
        rail = self._rail()
        rail.show(self.TIPS.get(ROOM_KEY))
        rail.set_keys(self._key_pairs())

    def _key_pairs(self) -> list[tuple[str, str]]:
        """This room's own keys, read from its bindings — never invented."""
        pairs: list[tuple[str, str]] = []
        for binding in getattr(self, "BINDINGS", []):
            if isinstance(binding, tuple):
                parts = list(binding) + [""]
                key, label = parts[0], parts[2]
            else:
                if not getattr(binding, "show", True):
                    continue
                key, label = binding.key, binding.description
            if label:
                key = "esc" if key == "escape" else key
                short = str(label).lower()
                pairs.append((key, short if len(short) <= 16 else short[:15] + "…"))
        pairs.append(("t", "tip detail"))
        return pairs

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
