"""The freshness ledger — NEW under the three-generation cache.

A *generation* is the span between two ``knivves update`` runs. Every knife
added to the database is stamped with the generation that was open when it
arrived. ``knivves update`` is the line that decides what reads NEW: it
seals the open batch, and a knife stays NEW while its batch is the open one
or one of the last ``keep_generations`` sealed batches::

    0 <= generation - added_generation <= keep_generations

so a knife is NEW from the moment it is filed, *survives* the update that
seals it (with the default ``keep_generations = 1`` it dies on the second
update), and with the maximum of 3 it survives three updates. Records that
predate this ledger carry no stamp and are never NEW — history is not
retroactively fresh.

The ``new`` flag is *materialized* onto each record (so the raw JSON, the
CLI tables, and the Vault all read the same truth) and re-derived by
``retag`` whenever the line or the cache depth moves. Pure dict-in/dict-out:
no I/O, no imports from the store.
"""
from __future__ import annotations

from datetime import date
from typing import Any

DEFAULT_KEEP = 1
MIN_KEEP = 1
MAX_KEEP = 3


def meta(db: dict[str, Any]) -> dict[str, Any]:
    """The ``updates`` block — created with defaults on first touch."""
    block = db.setdefault("updates", {})
    if not isinstance(block, dict):
        block = {}
        db["updates"] = block
    block.setdefault("generation", 1)
    block.setdefault("keep_generations", DEFAULT_KEEP)
    block.setdefault("history", [])
    return block


def is_new(record: dict[str, Any], meta_block: dict[str, Any]) -> bool:
    """The freshness rule: NEW from filing, through ``keep`` updates.

    A knife's batch survives the update that seals it and stays NEW while
    it is among the last ``keep_generations`` sealed batches. Unstamped
    records are never NEW.
    """
    added = record.get("added_generation")
    if not isinstance(added, int):
        return False
    generation = int(meta_block.get("generation", 1))
    keep = int(meta_block.get("keep_generations", DEFAULT_KEEP))
    return 0 <= generation - added <= keep


def stamp_new(db: dict[str, Any], record: dict[str, Any]) -> None:
    """Stamp an arriving record into the open generation."""
    block = meta(db)
    record["added_generation"] = int(block["generation"])
    record["date_added"] = date.today().isoformat()
    record["new"] = True


def retag(db: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Re-materialize every record's ``new`` flag.

    Returns ``(now_new_ids, aged_out_ids)`` relative to the flags the
    records carried before the pass.
    """
    block = meta(db)
    now_new: list[str] = []
    aged_out: list[str] = []
    for record in db.get("knives") or []:
        if not isinstance(record, dict):
            continue
        before = bool(record.get("new"))
        after = is_new(record, block)
        record["new"] = after
        rid = str(record.get("id") or "")
        if after and not before:
            now_new.append(rid)
        elif before and not after:
            aged_out.append(rid)
    return now_new, aged_out


def set_keep(db: dict[str, Any], keep: int) -> int:
    """Set the cache depth (clamped 1..3) and retag immediately."""
    block = meta(db)
    effective = max(MIN_KEEP, min(MAX_KEEP, int(keep)))
    block["keep_generations"] = effective
    retag(db)
    return effective


def added_in_open_generation(db: dict[str, Any]) -> list[str]:
    """IDs stamped into the generation that is currently open."""
    block = meta(db)
    generation = int(block["generation"])
    return [
        str(record.get("id") or "")
        for record in db.get("knives") or []
        if isinstance(record, dict) and record.get("added_generation") == generation
    ]


def advance(db: dict[str, Any], note: str = "", *, force: bool = False) -> dict[str, Any] | None:
    """``knivves update``'s core: seal the open generation, move the line.

    Freshness ages by *batches of arrivals*, not by update count: an
    update that filed nothing holds the line and returns ``None`` —
    otherwise running ``update`` twice in a row would erase the very
    freshness the first run tagged. Pass ``force=True`` to age the window
    deliberately. On a real seal: advances the generation counter, retags
    every record, and appends a history entry recording the decision.
    """
    block = meta(db)
    added = added_in_open_generation(db)
    if not added and not force:
        return None
    block["generation"] = int(block["generation"]) + 1
    now_new, aged_out = retag(db)
    entry = {
        "generation": block["generation"],
        "date": date.today().isoformat(),
        "note": note,
        "added": len(added),
        "added_ids": added,
        "now_new": now_new,
        "aged_out": aged_out,
    }
    block["history"].append(entry)
    return entry


def new_views_count(db: dict[str, Any]) -> int:
    """How many records currently read NEW (derived, not materialized)."""
    block = meta(db)
    return sum(
        1
        for record in db.get("knives") or []
        if isinstance(record, dict) and is_new(record, block)
    )
