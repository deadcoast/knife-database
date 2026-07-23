"""Tests for the BuyList priority model.

Plain-python runner (no pytest dependency):  python tests/test_buylist.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from knivves import buylist  # noqa: E402


def make_db() -> dict:
    return {
        "knives": [
            {"id": "alpha", "brand": "A", "model": "One", "user_tags": [],
             "canadian_online_retailers": [{"retailer": "X", "url": "https://x", "listed_price_cad": 100.0}]},
            {"id": "bravo", "brand": "B", "model": "Two", "user_tags": ["fancy"],
             "canadian_online_retailers": []},
            {"id": "charlie", "brand": "C", "model": "Three", "user_tags": [],
             "canadian_online_retailers": [{"retailer": "X", "url": "https://y", "listed_price_cad": 50.0}]},
        ]
    }


def test_set_buylist_orders_and_materializes() -> None:
    db = make_db()
    buylist.set_buylist(db, ["charlie", "alpha"])
    items = db["buy_list"]["items"]
    assert [(i["id"], i["priority"]) for i in items] == [("charlie", 1), ("alpha", 2)]
    by_id = {k["id"]: k for k in db["knives"]}
    assert by_id["charlie"]["buy_priority"] == 1
    assert by_id["alpha"]["buy_priority"] == 2
    assert "buy_list" in by_id["charlie"]["user_tags"]
    assert db["buy_list"]["updated"]


def test_reset_clears_stale_members() -> None:
    db = make_db()
    buylist.set_buylist(db, ["charlie", "alpha"])
    buylist.set_buylist(db, ["bravo"])
    by_id = {k["id"]: k for k in db["knives"]}
    assert by_id["bravo"]["buy_priority"] == 1
    assert "buy_priority" not in by_id["charlie"]
    assert "buy_list" not in by_id["charlie"]["user_tags"]
    assert "fancy" in by_id["bravo"]["user_tags"]  # other sections untouched


def test_unknown_ids_dropped_with_report() -> None:
    db = make_db()
    kept, missing = buylist.set_buylist(db, ["alpha", "ghost"])
    assert kept == ["alpha"]
    assert missing == ["ghost"]
    assert len(db["buy_list"]["items"]) == 1


def test_views_and_cumulative_math() -> None:
    db = make_db()
    buylist.set_buylist(db, ["alpha", "bravo", "charlie"])
    views = buylist.buylist_views(db)
    assert [priority for priority, _ in views] == [1, 2, 3]
    running = buylist.cumulative(views)
    # bravo has no price: the running total carries through unchanged
    assert running == [100.0, 100.0, 150.0]


def test_views_skip_deleted_records() -> None:
    db = make_db()
    buylist.set_buylist(db, ["alpha", "bravo"])
    db["knives"] = [k for k in db["knives"] if k["id"] != "alpha"]
    views = buylist.buylist_views(db)
    assert [(p, v.id) for p, v in views] == [(2, "bravo")]


def main() -> None:
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok  {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL  {name}: {exc}")
    if failures:
        sys.exit(f"{failures} test(s) failed")
    print("all buylist tests passed")


if __name__ == "__main__":
    main()
