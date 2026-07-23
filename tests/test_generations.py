"""Tests for the three-generation NEW freshness core.

Plain-python runner (no pytest dependency):  python tests/test_generations.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from knivves import generations as gen  # noqa: E402
from knivves.models import KnifeView  # noqa: E402
from knivves.store import add_knife  # noqa: E402


def make_db() -> dict:
    return {"knives": []}


def test_meta_created_with_defaults() -> None:
    db = make_db()
    meta = gen.meta(db)
    assert meta["generation"] == 1
    assert meta["keep_generations"] == 1
    assert meta["history"] == []
    assert db["updates"] is meta


def test_fresh_add_is_new_immediately() -> None:
    db = make_db()
    record = {"id": "test-knife", "brand": "Test", "model": "Knife"}
    add_knife(db, record)
    assert record["new"] is True
    assert record["added_generation"] == 1
    assert record["date_added"]
    assert KnifeView(record).is_new


def test_keep_one_survives_first_update_dies_when_next_batch_seals() -> None:
    # the update SEALS the batch as the newest NEW generation — it must
    # not kill the very knives it just tagged; aging happens when the
    # NEXT batch of arrivals is sealed
    db = make_db()
    record = {"id": "test-knife"}
    add_knife(db, record)
    entry = gen.advance(db)
    assert entry["generation"] == 2
    assert record["new"] is True
    assert "test-knife" not in entry["aged_out"]
    later = {"id": "later-arrival"}
    add_knife(db, later)
    entry = gen.advance(db)
    assert record["new"] is False
    assert "test-knife" in entry["aged_out"]
    assert later["new"] is True


def test_empty_update_holds_the_line() -> None:
    # an update that files nothing must not erase the freshness the
    # previous update tagged (regression: back-to-back updates)
    db = make_db()
    record = {"id": "fresh"}
    add_knife(db, record)
    assert gen.advance(db) is not None
    assert record["new"] is True
    assert gen.advance(db) is None  # nothing filed — line holds
    assert gen.meta(db)["generation"] == 2
    assert record["new"] is True
    entry = gen.advance(db, force=True)  # deliberate aging
    assert entry is not None
    assert record["new"] is False


def test_keep_three_survives_three_batches_dies_on_fourth() -> None:
    db = make_db()
    record = {"id": "survivor"}
    add_knife(db, record)
    gen.set_keep(db, 3)
    for i in range(3):
        add_knife(db, {"id": f"filler-{i}"})
        gen.advance(db)
        assert record["new"] is True
    add_knife(db, {"id": "filler-final"})
    entry = gen.advance(db)
    assert record["new"] is False
    assert "survivor" in entry["aged_out"]


def test_unstamped_legacy_record_never_new() -> None:
    db = {"knives": [{"id": "legacy"}]}
    gen.retag(db)
    assert db["knives"][0]["new"] is False
    gen.set_keep(db, 3)
    gen.advance(db, force=True)
    assert db["knives"][0]["new"] is False
    assert not KnifeView(db["knives"][0]).is_new


def test_set_keep_clamps_to_one_through_three() -> None:
    db = make_db()
    assert gen.set_keep(db, 0) == 1
    assert gen.set_keep(db, 9) == 3
    assert gen.set_keep(db, 2) == 2
    assert gen.meta(db)["keep_generations"] == 2


def test_set_keep_retags_immediately() -> None:
    db = make_db()
    record = {"id": "aging"}
    add_knife(db, record)
    gen.advance(db)
    gen.advance(db, force=True)
    assert record["new"] is False
    gen.set_keep(db, 3)
    assert record["new"] is True


def test_history_grows_and_counts_additions() -> None:
    db = make_db()
    add_knife(db, {"id": "a"})
    add_knife(db, {"id": "b"})
    entry = gen.advance(db, note="weekly refresh")
    assert gen.meta(db)["history"] == [entry]
    assert entry["added"] == 2
    assert entry["note"] == "weekly refresh"
    assert entry["date"]


def test_is_new_pure_rule() -> None:
    meta = {"generation": 5, "keep_generations": 2}
    assert gen.is_new({"added_generation": 5}, meta) is True  # open batch
    assert gen.is_new({"added_generation": 4}, meta) is True  # newest sealed
    assert gen.is_new({"added_generation": 3}, meta) is True  # second sealed
    assert gen.is_new({"added_generation": 2}, meta) is False  # aged out
    assert gen.is_new({}, meta) is False


def test_new_brands_requires_whole_brand_fresh() -> None:
    from knivves.models import new_brands

    views = [
        KnifeView({"id": "a", "brand": "Kansept", "new": True}),
        KnifeView({"id": "b", "brand": "Kansept", "new": True}),
        KnifeView({"id": "c", "brand": "Spyderco", "new": True}),
        KnifeView({"id": "d", "brand": "Spyderco", "new": False}),
        KnifeView({"id": "e", "brand": "Unknown", "new": True}),
    ]
    fresh = new_brands(views)
    assert fresh == {"kansept"}  # Spyderco existed before; Unknown never counts


def test_knife_view_surface() -> None:
    view = KnifeView({"id": "x", "new": True, "buy_priority": 3, "user_tags": ["buy_list"]})
    assert view.is_new
    assert view.buy_priority == 3
    assert view.sections == ["buy_list"]
    assert "new" in view.haystack()
    assert view.flat()["new"] is True
    assert view.flat()["buy_priority"] == 3


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
    print("all generations tests passed")


if __name__ == "__main__":
    main()
