"""Plain-python tests for the vault-state provider.

Runner:  python tests/test_state.py
The provider is the single reading both front doors speak — these tests
pin its numbers against a hand-built database.
"""
from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from knivves.state import vault_state  # noqa: E402


def _db() -> dict:
    return {
        "database_name": "state-test",
        "version": "9.9.9",
        "updates": {"generation": 4, "keep_generations": 2, "history": []},
        "buy_list": {
            "updated": "2026-07-23",
            "items": [{"id": "a-knife", "priority": 1}, {"id": "b-knife", "priority": 2}],
        },
        "knives": [
            {
                "id": "a-knife", "brand": "Alpha", "model": "One (A1)",
                "user_classification": "approved", "user_tags": [],
                "new": True, "added_generation": 4, "buy_priority": 1,
                "mechanism": {
                    "opening_method": "Thumb Stud", "lock_type": "Liner Lock",
                    "assist_type": "manual", "blade_length": "3.00 in",
                    "blade_steel": "14C28N", "clear_prohibited_mechanism_found": False,
                },
                "canadian_online_retailers": [{
                    "retailer": "Blades Canada / Warriors and Wonders",
                    "url": "https://www.bladescanada.com/Alpha/one",
                    "listed_price_cad": 100.0, "availability": "in stock",
                    "source_date": "2026-07-01",
                }],
                "listing_title": "Alpha One", "notes": "", "source_input": "",
            },
            {
                "id": "b-knife", "brand": "Beta", "model": "Two (B2)",
                "user_classification": None, "user_tags": [],
                "buy_priority": 2,
                "mechanism": {
                    "opening_method": None, "lock_type": None,
                    "assist_type": "unknown", "blade_length": None,
                    "blade_steel": None, "clear_prohibited_mechanism_found": False,
                },
                "canadian_online_retailers": [{
                    "retailer": "Blades Canada / Warriors and Wonders",
                    "url": "https://www.bladescanada.com/Beta/two",
                    "listed_price_cad": 300.0, "availability": "in stock",
                    "source_date": "2026-07-01",
                }],
                "listing_title": "", "notes": "", "source_input": "",
            },
        ],
    }


def test_one_reading() -> None:
    state = vault_state(_db())
    assert state.blades == 2, state.blades
    assert state.fresh == 1, state.fresh
    assert state.approved == 1, state.approved
    assert state.unresearched == 1, state.unresearched  # b-knife has open gaps
    assert state.priced == 2 and state.affordable == 1, (state.priced, state.affordable)
    assert state.average_cad == 200.0, state.average_cad
    assert state.generation == 4 and state.keep_generations == 2
    assert state.version == "9.9.9"
    assert [priority for priority, _ in state.ladder] == [1, 2]
    assert list(state.ladder_totals) == [100.0, 400.0], state.ladder_totals
    print("PASS: one reading — counts, gaps, money, window, ladder")


def test_reading_is_frozen() -> None:
    state = vault_state(_db())
    try:
        state.blades = 999  # type: ignore[misc]
    except FrozenInstanceError:
        print("PASS: the reading is frozen — no door can bend the numbers")
        return
    raise AssertionError("VaultState mutated — the reading must be frozen")


def test_prebuilt_views_are_honored() -> None:
    from knivves.models import knife_views

    db = _db()
    views = knife_views(db)
    assert vault_state(db, views) == vault_state(db)
    print("PASS: prebuilt views produce the identical reading")


if __name__ == "__main__":
    test_one_reading()
    test_reading_is_frozen()
    test_prebuilt_views_are_honored()
