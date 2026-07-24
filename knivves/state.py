"""The vault's state — derived once, spoken everywhere.

Both front doors — the CLI welcome page and the TUI entry hall — render
the same numbers. They cannot disagree because neither derives its own:
this module is the single reading. Any door that wants the vault's
state takes a ``VaultState`` and speaks it; none computes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import buylist, generations
from .ledger import AFFORDABLE_THRESHOLD_CAD
from .models import KnifeView, knife_views
from .research import audit_database


@dataclass(frozen=True)
class VaultState:
    """One reading of the vault, for any door that speaks its numbers."""

    blades: int
    fresh: int
    approved: int
    unresearched: int
    priced: int
    affordable: int
    average_cad: float
    generation: Any
    keep_generations: Any
    version: str
    ladder: tuple[tuple[int, KnifeView], ...]
    ladder_totals: tuple[float, ...]


def vault_state(db: dict[str, Any], knives: list[KnifeView] | None = None) -> VaultState:
    """Read the vault. Pass ``knives`` when views are already built."""
    views = knife_views(db) if knives is None else knives
    prices = [k.price for k in views if k.price is not None]
    meta = generations.meta(db)
    ladder = buylist.buylist_views(db)
    return VaultState(
        blades=len(views),
        fresh=sum(1 for k in views if k.is_new),
        approved=sum(1 for k in views if k.classification == "approved"),
        unresearched=audit_database(db).with_gaps,
        priced=len(prices),
        affordable=sum(1 for p in prices if p < AFFORDABLE_THRESHOLD_CAD),
        average_cad=(sum(prices) / len(prices)) if prices else 0.0,
        generation=meta.get("generation"),
        keep_generations=meta.get("keep_generations"),
        version=str(db.get("version") or "?"),
        ladder=tuple(ladder),
        ladder_totals=tuple(buylist.cumulative(ladder)),
    )
