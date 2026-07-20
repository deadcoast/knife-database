"""Font test card — ground truth for what THIS terminal actually renders.

Every candidate drawing primitive, side by side. Nothing here is a design.
The only question per row: does it render as clean solid ink, or not?

Run:  python design/proofs/font-test-card.py
"""
from __future__ import annotations

from rich.console import Console
from rich.text import Text

console = Console()

LABEL = "#8b96a0"
RAMP = ["#3a4046", "#454c53", "#525a62", "#626b74", "#758089",
        "#8b96a0", "#a5b0ba", "#c2cdd6", "#dde6ee"]


def row(tag: str, sample: Text) -> None:
    line = Text(f"  {tag:<26}", style=LABEL)
    line.append_text(sample)
    console.print(line)
    console.print()


def main() -> None:
    console.print()
    console.print(Text("FONT TEST CARD — judge each row: solid / broken / ugly", style=f"bold {LABEL}"))
    console.print()

    t = Text()
    for i, c in enumerate("█" * 36):
        t.append(c, style=RAMP[min(len(RAMP) - 1, i * len(RAMP) // 36)])
    row("A  full blocks + ramp", t)

    t = Text()
    t.append("███████████████████████████████", style="#758089")
    t.append("▋", style="#758089")
    row("B  eighth-block bar end", t)

    t = Text("▏▎▍▌▋▊▉█", style="#a5b0ba")
    t.append("   (8 widths of one cell)", style=LABEL)
    row("C  eighth-block steps", t)

    t = Text("▀▀▀▀▀▀▀▀  ▄▄▄▄▄▄▄▄  ", style="#a5b0ba")
    t.append("▘▝▖▗▚▞▌▐", style="#a5b0ba")
    row("D  half + quadrant blocks", t)

    t = Text("░░░░░░  ▒▒▒▒▒▒  ▓▓▓▓▓▓  ██████", style="#758089")
    row("E  shade characters", t)

    t = Text("⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿", style="#758089")
    t.append("   (the one that failed)", style=LABEL)
    row("F  braille full", t)

    t = Text("┌─────┬─────┐ ┏━━━━━┳━━━━━┓ ╔═════╦═════╗", style="#8b96a0")
    row("G  box drawing 3 weights", t)

    t = Text()
    for i in range(36):
        shade = int(58 + (222 - 58) * i / 35)
        t.append("█", style=f"rgb({shade},{shade + 4},{shade + 8})")
    row("H  truecolor smoothness", t)

    console.print(Text("  COMPARISON — the same 152 mm bar, both primitives (1 cell = 2 mm):", style=f"bold {LABEL}"))
    console.print()
    t = Text()
    t.append("█" * 76, style="#758089")
    t.append("  152 mm  solid blocks", style=LABEL)
    console.print(Text("  ") + t)
    t = Text()
    t.append("⣿" * 76, style="#758089")
    t.append("  152 mm  braille (failed)", style=LABEL)
    console.print(Text("  ") + t)
    console.print()
    console.print(Text("  Report per row: solid / broken / ugly. That report becomes the constraint file.", style=LABEL))
    console.print()


if __name__ == "__main__":
    main()
