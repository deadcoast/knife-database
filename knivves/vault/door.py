"""The Vault Door — navigation as mechanism.

Not two bars: a machine. The door is custom-rendered steel — brushed
leaves drawn line by line with banding and a beveled seam edge — locked
by a bolt column. Arrival is staged: the door holds closed, the bolts
retract in a cascade, and only then do the leaves part. On cold boot the
brand is engraved on the closed door and travels out with its leaf.

The door overlays the incoming room, plays its sequence (~0.6s on a room
switch, ~1.4s on boot), and removes itself.
"""
from __future__ import annotations

import asyncio

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static

from . import laws

CLOSED_HOLD = 0.12
BOOT_HOLD = 0.8
BOLT_STEP = 0.028
OPEN_DURATION = 0.30


class SteelLeaf(Widget):
    """One machined door leaf: brushed banding, beveled seam edge."""

    DEFAULT_CSS = """
    SteelLeaf {
        layer: leaves;
        position: absolute;
        width: 50%;
        height: 100%;
    }
    """

    def __init__(self, side: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.side = side  # "left" | "right"

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0:
            return Strip([])
        # brushed steel: fine banding + occasional hairline on a raised tone
        delta = -2 if y % 2 == 1 else 0
        if y % 8 == 0:
            delta = 4
        tone = Style(bgcolor=f"rgb({33 + delta},{37 + delta},{43 + delta})")
        # the seam: a machined lip catching light, then a dark recessed channel
        lip = Style(bgcolor="rgb(107,118,128)")
        channel = Style(bgcolor="rgb(21,23,27)")
        body = Segment(" " * max(width - 2, 0), tone)
        if self.side == "left":
            segments = [body, Segment(" ", lip), Segment(" ", channel)]
        else:
            segments = [Segment(" ", channel), Segment(" ", lip), body]
        return Strip(segments, width)


class VaultDoor(Container):
    DEFAULT_CSS = f"""
    VaultDoor {{
        layer: door;
        width: 100%;
        height: 100%;
        layers: leaves mechanism;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }}
    VaultDoor > #door-bolts {{
        layer: mechanism;
        position: absolute;
        width: 2;
        height: 100%;
    }}
    VaultDoor > #door-brand {{
        layer: mechanism;
        position: absolute;
        width: auto;
        height: 1;
        text-style: bold;
        color: {laws.STEEL_BRIGHT};
        background: rgb(33,37,43);
    }}
    """

    def __init__(self, brand: str | None = None, hold: float = CLOSED_HOLD) -> None:
        super().__init__()
        self._brand = brand
        self._hold = hold

    def compose(self) -> ComposeResult:
        yield SteelLeaf("left", id="door-left")
        yield SteelLeaf("right", id="door-right")
        yield Static("", id="door-bolts")
        if self._brand:
            yield Static(self._brand, id="door-brand")

    def on_mount(self) -> None:
        self.run_worker(self._sequence(), exclusive=False)

    # ------------------------------------------------------------- sequence

    async def _await_layout(self) -> None:
        for _ in range(30):
            if self.size.width > 0:
                return
            await asyncio.sleep(1 / 60)

    def _bolt_positions(self) -> list[int]:
        height = self.size.height
        count = max(3, height // 6)
        return [int((i + 0.5) * height / count) for i in range(count)]

    def _bolt_text(self, retracted: int) -> Text:
        positions = self._bolt_positions()
        text = Text()
        index = 0
        for y in range(self.size.height):
            if index < len(positions) and y == positions[index]:
                if index < retracted:
                    text.append("╹╹\n", style=laws.STEEL_DIM)
                else:
                    text.append("██\n", style=laws.STEEL_BRIGHT)
                index += 1
            else:
                text.append("  \n")
        return text

    async def _sequence(self) -> None:
        await self._await_layout()
        width, height = self.size.width, self.size.height
        seam_x = width // 2

        left_leaf = self.query_one("#door-left")
        right_leaf = self.query_one("#door-right")
        left_leaf.styles.offset = (0, 0)
        right_leaf.styles.offset = (width - right_leaf.size.width, 0)
        self._right_home = width - right_leaf.size.width

        bolts = self.query_one("#door-bolts", Static)
        bolts.styles.offset = (seam_x - 1, 0)
        bolts.update(self._bolt_text(0))

        brand = None
        if self._brand:
            brand = self.query_one("#door-brand", Static)
            brand.styles.offset = (max(2, seam_x - len(self._brand) - 3), height // 2)

        # stage 1 — locked
        await asyncio.sleep(self._hold)

        # stage 2 — bolts retract, top to bottom
        for retracted in range(1, len(self._bolt_positions()) + 1):
            bolts.update(self._bolt_text(retracted))
            await asyncio.sleep(BOLT_STEP)
        bolts.remove()

        # stage 3 — the leaves part; the engraving travels with its leaf
        travel_x = seam_x + 4
        laws.travel(left_leaf, -travel_x, 0, duration=OPEN_DURATION)
        laws.travel(right_leaf, self._right_home + travel_x, 0, duration=OPEN_DURATION)
        if brand is not None:
            current = brand.styles.offset
            laws.travel(brand, int(current.x.value) - travel_x, height // 2, duration=OPEN_DURATION)
        await asyncio.sleep(OPEN_DURATION + 0.12)
        self.remove()


def open_door(screen, brand: str | None = None, hold: float = CLOSED_HOLD) -> None:
    """Mount an opening door over a screen. Fire-and-forget."""
    screen.mount(VaultDoor(brand=brand, hold=hold))
