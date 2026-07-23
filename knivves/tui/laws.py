"""The house laws — design constants every room of the Vault obeys.

The Vault reads as one application because no room is allowed its own
vocabulary. Three laws, enforced here as the only source of truth:

1. One palette. Machined darks, steel text, classification colors, and a
   single amber accent. No room introduces a color.
2. One field grammar. Every labeled value everywhere renders through
   ``field()`` — the plate, the gates, the masthead, the bench.
3. One motion law. Objects travel, they never teleport and never fade.
   Every animation moves through ``travel()`` with the same easing.
"""
from __future__ import annotations

from rich.text import Text
from textual.css.scalar import ScalarOffset
from textual.theme import Theme
from textual.widget import Widget

# -- law 1: the palette ------------------------------------------------------

BG = "#14171a"
SURFACE = "#1d2126"
SURFACE_LOW = "#171a1e"     # recessed machined tone — zebra rows
SURFACE_HIGH = "#262b31"    # raised machined tone — a surface under the hand
SURFACE_RAISED = "#2a3038"  # the seated cursor row
EDGE = "#31363c"
EDGE_BRIGHT = "#525a62"

STEEL_BRIGHT = "#dde6ee"
STEEL_BODY = "#c2cdd6"      # the body text everywhere — between bright and mid
STEEL_MID = "#8b96a0"
STEEL_DIM = "#5c6670"

ACCENT = "#d7a455"          # the only accent in the building
FRESH = "#5fd3bc"           # cold mint — the glint of a fresh edge; ★new wears it in every room
PASS = "#79b473"
FAIL = "#c05b4d"

CLASS_COLORS = {
    "approved": PASS,
    "rejected": FAIL,
    "unclassified": STEEL_DIM,
}

# The palette as the application's registered Theme: laws.py stays the
# single Python source of truth, and every stylesheet speaks it as
# $variables — no .tcss in the building may carry a raw color.

THEME_VARIABLES = {
    "edge": EDGE,
    "edge-bright": EDGE_BRIGHT,
    "steel-bright": STEEL_BRIGHT,
    "steel-body": STEEL_BODY,
    "steel-mid": STEEL_MID,
    "steel-dim": STEEL_DIM,
    "fresh": FRESH,
    "pass": PASS,
    "fail": FAIL,
    "surface-low": SURFACE_LOW,
    "surface-high": SURFACE_HIGH,
    "surface-raised": SURFACE_RAISED,
}

KNIVVES_THEME = Theme(
    name="knivves",
    primary=ACCENT,
    accent=ACCENT,
    warning=ACCENT,
    error=FAIL,
    success=PASS,
    foreground=STEEL_BODY,
    background=BG,
    surface=SURFACE,
    panel=SURFACE,
    dark=True,
    variables=THEME_VARIABLES,
)

# -- law 2: the field grammar ------------------------------------------------

LABEL_WIDTH = 10


def field(label: str, value: str, value_style: str = STEEL_BRIGHT) -> Text:
    """One labeled value, in the grammar every room speaks."""
    text = Text()
    text.append(f"{label.upper():<{LABEL_WIDTH}}", style=STEEL_DIM)
    text.append(value, style=value_style)
    return text


# -- law 3: the motion law ---------------------------------------------------

EASING = "in_out_cubic"
TRAVEL_DURATION = 0.55


def travel(widget: Widget, x: int, y: int, duration: float = TRAVEL_DURATION) -> None:
    """Move an object to (x, y). The only sanctioned way anything moves."""
    target = ScalarOffset.from_offset((x, y))
    widget.styles.animate("offset", value=target, duration=duration, easing=EASING)
