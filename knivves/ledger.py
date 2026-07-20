"""Price intelligence — observations, history, movers, and the threshold rule.

Pure record-dict operations, no UI imports. The Vault's Ledger room and any
future CLI command speak through these.

Price history lives on each record as ``price_history``:
    [{"date": "YYYY-MM-DD", "price_cad": 123.45}, ...]
The first observation is seeded from the retailer entry's existing
``listed_price_cad`` / ``source_date`` snapshot, so history begins at the
record's oldest known price, not at the first survey.
"""
from __future__ import annotations

from typing import Any

from .models import KnifeView

AFFORDABLE_THRESHOLD_CAD = 150.0
NEAR_LINE_BAND_CAD = 25.0

BUCKETS = [
    ("under $50", 0, 50),
    ("$50–100", 50, 100),
    ("$100–150", 100, 150),
    ("$150–250", 150, 250),
    ("$250–400", 250, 400),
    ("$400–700", 400, 700),
    ("$700+", 700, float("inf")),
]


def seed_history(record: dict[str, Any]) -> bool:
    """Backfill the first observation from the existing snapshot. True if seeded."""
    if record.get("price_history"):
        return False
    retailers = record.get("canadian_online_retailers") or []
    if not retailers:
        return False
    price = retailers[0].get("listed_price_cad")
    if not isinstance(price, (int, float)):
        return False
    on_date = str(retailers[0].get("source_date") or "unknown")
    record["price_history"] = [{"date": on_date, "price_cad": float(price)}]
    return True


def observe(
    record: dict[str, Any],
    price: float | None,
    availability: str | None,
    on_date: str,
) -> float | None:
    """Record a fresh market observation on the primary retailer entry.

    Returns the price delta (new - old) when both prices are known,
    else None. Same-date re-observations update in place.
    """
    retailers = record.get("canadian_online_retailers") or []
    if not retailers:
        return None
    seed_history(record)
    entry = retailers[0]
    old = entry.get("listed_price_cad")
    if availability:
        entry["availability"] = availability
    entry["source_date"] = on_date
    if price is None:
        return None
    entry["listed_price_cad"] = float(price)
    history = record.setdefault("price_history", [])
    if history and history[-1].get("date") == on_date:
        history[-1]["price_cad"] = float(price)
    else:
        history.append({"date": on_date, "price_cad": float(price)})
    return float(price) - float(old) if isinstance(old, (int, float)) else None


def retag_affordable(record: dict[str, Any]) -> None:
    """Re-apply the auto tag rule: `affordable` iff priced under the threshold."""
    tags = [t for t in (record.get("user_tags") or []) if t != "affordable"]
    prices = [
        r.get("listed_price_cad")
        for r in record.get("canadian_online_retailers") or []
    ]
    prices = [p for p in prices if isinstance(p, (int, float))]
    if prices and min(prices) < AFFORDABLE_THRESHOLD_CAD:
        tags.append("affordable")
    record["user_tags"] = tags


def price_buckets(knives: list[KnifeView]) -> list[tuple[str, int]]:
    """Distribution of best prices across the fixed bucket edges."""
    counts = [0] * len(BUCKETS)
    for knife in knives:
        if knife.price is None:
            continue
        for i, (_, lo, hi) in enumerate(BUCKETS):
            if lo <= knife.price < hi:
                counts[i] += 1
                break
    return [(label, counts[i]) for i, (label, _, _) in enumerate(BUCKETS)]


def near_the_line(knives: list[KnifeView]) -> list[KnifeView]:
    """Knives whose price sits within the band around the affordable threshold."""
    near = [
        k for k in knives
        if k.price is not None
        and abs(k.price - AFFORDABLE_THRESHOLD_CAD) <= NEAR_LINE_BAND_CAD
    ]
    return sorted(near, key=lambda k: abs((k.price or 0) - AFFORDABLE_THRESHOLD_CAD))


def vault_valuation(knives: list[KnifeView]) -> dict[str, float | int]:
    prices = [k.price for k in knives if k.price is not None]
    return {
        "priced": len(prices),
        "total": sum(prices),
        "average": sum(prices) / len(prices) if prices else 0.0,
        "affordable": sum(1 for k in knives if "affordable" in k.tags),
    }
