"""The reserve ledger — BuyList acquisition priorities.

The BuyList is an *ordered* shortlist: priority 1 is the most sought
acquisition. The ingestion file is the source of truth for the ordering
(its BuyList section is written top-down by desire), so ``set_buylist``
replaces the whole ordering each time it runs.

Truth lives in two places on purpose:

* ``db["buy_list"]`` — the ordered ledger (`{"updated", "items": [...]}`)
  so displays can walk priorities without scanning every record, and
* materialized ``buy_priority`` + the ``buy_list`` section on each member
  record, so a single knife (raw JSON, plate, detail panel) tells its own
  story. ``set_buylist`` keeps both in lockstep and scrubs ex-members.

Pure dict-in/dict-out; no file I/O.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .models import KnifeView

BUYLIST_SECTION = "buy_list"


def set_buylist(db: dict[str, Any], ids: list[str]) -> tuple[list[str], list[str]]:
    """Replace the BuyList ordering. Returns ``(kept_ids, missing_ids)``.

    Unknown ids are dropped (reported, not raised); stale members lose
    their ``buy_priority`` and ``buy_list`` section.
    """
    by_id = {str(k.get("id")): k for k in db.get("knives") or [] if isinstance(k, dict)}
    kept: list[str] = []
    missing: list[str] = []
    for rid in ids:
        (kept if rid in by_id else missing).append(rid)

    wanted = set(kept)
    for rid, record in by_id.items():
        if rid in wanted:
            continue
        record.pop("buy_priority", None)
        tags = [str(t) for t in record.get("user_tags") or []]
        if BUYLIST_SECTION in tags:
            record["user_tags"] = [t for t in tags if t != BUYLIST_SECTION]

    items: list[dict[str, Any]] = []
    for priority, rid in enumerate(kept, start=1):
        record = by_id[rid]
        record["buy_priority"] = priority
        tags = [str(t) for t in record.get("user_tags") or []]
        if BUYLIST_SECTION not in tags:
            tags.append(BUYLIST_SECTION)
        record["user_tags"] = sorted(tags)
        items.append({"id": rid, "priority": priority})

    db["buy_list"] = {"updated": date.today().isoformat(), "items": items}
    return kept, missing


def buylist_views(db: dict[str, Any]) -> list[tuple[int, KnifeView]]:
    """The BuyList in priority order, skipping records that no longer exist."""
    by_id = {str(k.get("id")): k for k in db.get("knives") or [] if isinstance(k, dict)}
    block = db.get("buy_list") or {}
    views: list[tuple[int, KnifeView]] = []
    for item in block.get("items") or []:
        if not isinstance(item, dict):
            continue
        record = by_id.get(str(item.get("id")))
        if record is None:
            continue
        priority = item.get("priority")
        if isinstance(priority, int) and priority > 0:
            views.append((priority, KnifeView(record)))
    return views


def cumulative(views: list[tuple[int, KnifeView]]) -> list[float]:
    """Running acquisition cost down the priority ladder.

    A row with no listed price contributes zero — the running total simply
    carries through, so ``cumulative(...)[k]`` always answers "what would
    the top k+1 priorities cost, as far as prices are known?"
    """
    totals: list[float] = []
    running = 0.0
    for _priority, view in views:
        if view.price is not None:
            running += view.price
        totals.append(running)
    return totals
