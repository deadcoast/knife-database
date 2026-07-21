"""The Vault Door — navigation as mechanism.

Rooms are not switched, they are entered: steel leaves part to admit you.
On cold boot the door holds closed with the engraved brand, then opens
into the Rack. Per the motion law the leaves travel — nothing fades.

The door is an overlay widget that mounts closed over the incoming room,
opens, and removes itself. It exists for under half a second per arrival;
its whole job is to make arrival an event.
"""
from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static

from . import laws

OPEN_DURATION = 0.30
BOOT_HOLD = 0.7


class VaultDoor(Container):
    DEFAULT_CSS = f"""
    VaultDoor {{
        layer: door;
        width: 100%;
        height: 100%;
        background: {laws.BG} 0%;
    }}
    VaultDoor > .door--leaf {{
        height: 100%;
        background: {laws.SURFACE};
    }}
    VaultDoor > #door-left {{
        dock: left;
        width: 50%;
        border-right: thick {laws.EDGE_BRIGHT};
    }}
    VaultDoor > #door-right {{
        dock: right;
        width: 50%;
        border-left: thick {laws.EDGE};
    }}
    VaultDoor .door--brand {{
        width: 100%;
        height: 100%;
        content-align: right middle;
        padding-right: 3;
        text-style: bold;
        color: {laws.STEEL_BRIGHT};
    }}
    """

    def __init__(self, brand: str | None = None, hold: float = 0.0) -> None:
        super().__init__()
        self._brand = brand
        self._hold = hold

    def compose(self) -> ComposeResult:
        with Vertical(classes="door--leaf", id="door-left"):
            if self._brand:
                yield Static(self._brand, classes="door--brand")
        yield Vertical(classes="door--leaf", id="door-right")

    def on_mount(self) -> None:
        self.run_worker(self._open(), exclusive=False)

    async def _open(self) -> None:
        if self._hold:
            await asyncio.sleep(self._hold)
        half = (self.size.width // 2) + 3
        left = self.query_one("#door-left")
        right = self.query_one("#door-right")
        laws.travel(left, -half, 0, duration=OPEN_DURATION)
        laws.travel(right, half, 0, duration=OPEN_DURATION)
        await asyncio.sleep(OPEN_DURATION + 0.12)
        self.remove()


def open_door(screen, brand: str | None = None, hold: float = 0.0) -> None:
    """Mount an opening door over a screen. Fire-and-forget."""
    screen.mount(VaultDoor(brand=brand, hold=hold))
