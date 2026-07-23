"""Tests for the Research Desk backend — the vault researches its own unknowns.

Case: docs/dev-spec/2026-07-23-research-desk (REQ-RES-1..3).
Plain-python runner (no pytest dependency):  python tests/test_research.py

Laws under test: fill-only-empty (user data never overwritten), honest
gaps (unreachable shelved and said, never skipped silently), rulebook
hits reported never written. All offline — fetch is injected.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from knivves import research  # noqa: E402
from knivves.models import KnifeView, knife_views  # noqa: E402
from knivves.scrape import Listing, ScrapeError  # noqa: E402

BC_URL = "https://www.bladescanada.com/Kubey-Knives/Kubey-Gurkha-KU345A"
UNSUPPORTED_URL = "https://www.canadiantire.ca/en/pdp/kershaw-skyline-1752469p.html"

RULES = [
    "automatic switchblade",
    "butterfly knife",
]


def make_record(**over) -> dict:
    """A complete record; tests knock fields out to open gaps."""
    record = {
        "id": "kubey-gurkha",
        "brand": "Kubey",
        "model": "Gurkha (KU345A)",
        "user_classification": None,
        "user_tags": [],
        "research_status": "canadian_retailer_verified",
        "acquisition_status": "pending_research",
        "mechanism": {
            "opening_method": "Thumb Stud",
            "lock_type": "Liner Lock",
            "assist_type": "manual",
            "blade_length": "3.2 in (81mm)",
            "blade_steel": "14C28N",
            "clear_prohibited_mechanism_found": False,
        },
        "canadian_online_retailers": [{
            "retailer": "Blades Canada / Warriors and Wonders",
            "url": BC_URL,
            "listed_price_cad": 89.99,
            "availability": "in stock",
            "source_date": "2026-07-01",
        }],
        "listing_title": "Kubey Gurkha Folding Knife, 14C28N, KU345A",
        "notes": "",
        "source_input": "",
    }
    record.update(over)
    return record


def make_listing(**over) -> Listing:
    listing = Listing(
        url=BC_URL,
        retailer="Blades Canada / Warriors and Wonders",
        listing_title="Kubey Gurkha Folding Knife, 14C28N Satin, G10 Black, KU345A",
        brand="Kubey",
        model="Gurkha (KU345A)",
        price_cad=89.99,
        availability="in stock",
        blade_steel="14C28N",
        lock_type="Liner Lock",
        opening_method="Thumb Stud, Flipper",
        blade_length="3.2 in (81mm)",
    )
    for key, value in over.items():
        setattr(listing, key, value)
    return listing


# ------------------------------------------------------- REQ-RES-1 audit

def test_audit_flags_gaps() -> None:
    # a record with a TODO title, Unknown steel, and no price yields
    # exactly those gaps; a complete record yields none
    record = make_record(
        source_input=f"- [TODO:GET-KNIFE-DATA]({BC_URL})",
        listing_title="",
    )
    record["mechanism"]["blade_steel"] = None
    record["canadian_online_retailers"][0]["listed_price_cad"] = None
    gaps = research.audit_record(record)
    fields = {gap.field for gap in gaps}
    assert fields == {"title", "steel", "price", "listing_title"}, fields
    for gap in gaps:
        assert gap.source_url == BC_URL
        assert gap.supported is True

    assert research.audit_record(make_record()) == []


def test_audit_database_counts_complete_and_gapped() -> None:
    db = {"knives": [
        make_record(),
        make_record(id="second", mechanism={
            "opening_method": None, "lock_type": None, "assist_type": "unknown",
            "blade_length": None, "blade_steel": None,
            "clear_prohibited_mechanism_found": None,
        }),
    ]}
    audit = research.audit_database(db)
    assert audit.records == 2
    assert audit.complete == 1
    assert set(audit.gaps_by_id) == {"second"}
    assert audit.gap_total == len(audit.gaps_by_id["second"])


# ------------------------------------------------------ REQ-RES-2 docket

def test_docket_orders_buylist_first() -> None:
    # docket order is buy-rank -> new -> gap-count; the unsupported-URL
    # record appears only on the unreachable shelf
    def gapped(rid: str, **over) -> dict:
        record = make_record(id=rid, **over)
        record["mechanism"]["blade_steel"] = None
        return record

    archive = gapped("archive")
    fresh = gapped("fresh", new=True)
    wanted = gapped("wanted", buy_priority=2)
    wide_open = gapped("wide-open")
    wide_open["mechanism"]["lock_type"] = None
    offshore = gapped("offshore")
    offshore["canadian_online_retailers"][0]["url"] = UNSUPPORTED_URL
    complete = make_record(id="complete", buy_priority=1)

    knives = knife_views({"knives": [archive, fresh, wanted, wide_open, offshore, complete]})
    docket = research.build_docket(knives)

    assert [e.knife_id for e in docket.entries] == ["wanted", "fresh", "wide-open", "archive"]
    assert [e.knife_id for e in docket.unreachable] == ["offshore"]
    assert docket.unreachable[0].reason  # honest gaps: the shelf says why


# ------------------------------------------------- REQ-RES-3 completion

def test_fill_never_overwrites() -> None:
    # user-entered steel survives a listing that disagrees
    record = make_record()
    listing = make_listing(blade_steel="S35VN", price_cad=999.99, lock_type="Frame Lock")
    report = research.research_record(record, listing, on_date="2026-07-23")
    assert record["mechanism"]["blade_steel"] == "14C28N"
    assert record["mechanism"]["lock_type"] == "Liner Lock"
    assert record["canadian_online_retailers"][0]["listed_price_cad"] == 89.99
    assert report.filled == []


def test_fill_only_empty_fields_land() -> None:
    record = make_record()
    record["mechanism"]["blade_steel"] = None
    record["mechanism"]["blade_length"] = "Unknown"
    listing = make_listing()
    report = research.research_record(record, listing, on_date="2026-07-23")
    assert record["mechanism"]["blade_steel"] == "14C28N"
    assert record["mechanism"]["blade_length"] == "3.2 in (81mm)"
    filled = dict(report.filled)
    assert set(filled) == {"steel", "length"}
    # provenance stamped, additive, host named
    assert record["research"]["last_pass"] == "2026-07-23"
    assert record["research"]["filled"]["steel"] == "bladescanada.com"


def test_price_fill_seeds_history_and_retags_affordable() -> None:
    record = make_record()
    record["canadian_online_retailers"][0]["listed_price_cad"] = None
    record["canadian_online_retailers"][0]["availability"] = "unknown"
    listing = make_listing(price_cad=129.99)
    report = research.research_record(record, listing, on_date="2026-07-23")
    entry = record["canadian_online_retailers"][0]
    assert entry["listed_price_cad"] == 129.99
    assert entry["availability"] == "in stock"
    assert entry["source_date"] == "2026-07-23"
    assert record["price_history"] == [{"date": "2026-07-23", "price_cad": 129.99}]
    assert "affordable" in record["user_tags"]
    assert dict(report.filled)["price"] == "bladescanada.com"


def test_title_placeholder_resolved_from_listing() -> None:
    # a slug-derived TODO record earns its real name; the id never changes
    record = make_record(
        brand="Kansept",
        model="Korvid V Crossbar Lock Folding Knife - TE2030V1",
        listing_title="",
        source_input=f"- [TODO:GET-KNIFE-DATA]({BC_URL})",
    )
    listing = make_listing(
        brand="Kansept", model="Korvid V (TE2030V1)",
        listing_title="Kansept Korvid V Crossbar Lock Folding Knife, D2 Rose Gold, TE2030V1",
    )
    report = research.research_record(record, listing, on_date="2026-07-23")
    assert record["model"] == "Korvid V (TE2030V1)"
    assert record["listing_title"].startswith("Kansept Korvid V")
    assert record["id"] == "kubey-gurkha"  # ids are stable, never re-derived
    assert "title" in dict(report.filled)


def test_rulebook_hit_reported_not_written() -> None:
    # a listing whose text matches a rulebook term yields a reported hit
    # with the record's flag unchanged — the decision stays the user's
    record = make_record()
    record["mechanism"]["lock_type"] = None
    listing = make_listing(
        listing_title="Kubey Butterfly Trainer Folding Knife, 14C28N",
        lock_type=None,
    )
    report = research.research_record(record, listing, rules=RULES, on_date="2026-07-23")
    assert [rule for rule, _ in report.rulebook_hits] == ["butterfly knife"]
    assert record["mechanism"]["clear_prohibited_mechanism_found"] is False


def test_screen_text_assisted_opening_never_trips() -> None:
    # the forge's precision law, now enforced at the backend
    hits = research.screen_text(
        "Falcon Flipper Folding Knife, Assisted Opening, 440 Stainless",
        list(research.RULE_KEYWORDS),
    )
    assert hits == []


# ------------------------------------------------- run_research pass

def test_run_research_fills_docket_and_reports() -> None:
    record = make_record()
    record["mechanism"]["blade_steel"] = None
    db = {"knives": [record]}

    def fetch(url: str) -> Listing:
        assert url == BC_URL
        return make_listing()

    summary = research.run_research(db, fetch=fetch, on_date="2026-07-23")
    assert not summary.dry_run
    assert [r.knife_id for r in summary.reports] == ["kubey-gurkha"]
    assert summary.field_counts == {"steel": 1}
    assert record["mechanism"]["blade_steel"] == "14C28N"


def test_run_research_dry_run_touches_nothing() -> None:
    record = make_record()
    record["mechanism"]["blade_steel"] = None
    db = {"knives": [record]}
    calls: list[str] = []

    def fetch(url: str) -> Listing:  # pragma: no cover — must never run
        calls.append(url)
        return make_listing()

    import copy
    before = copy.deepcopy(db)
    summary = research.run_research(db, fetch=fetch, dry_run=True, on_date="2026-07-23")
    assert summary.dry_run
    assert calls == []
    assert db == before
    assert [e.knife_id for e in summary.planned] == ["kubey-gurkha"]


def test_run_research_fetch_error_is_honest() -> None:
    # an unreachable listing is recorded and said, never silently skipped
    record = make_record()
    record["mechanism"]["blade_steel"] = None
    db = {"knives": [record]}

    def fetch(url: str) -> Listing:
        raise ScrapeError("fetch failed: connection refused")

    summary = research.run_research(db, fetch=fetch, on_date="2026-07-23")
    assert summary.reports == []
    assert [rid for rid, _ in summary.failed] == ["kubey-gurkha"]
    assert "connection refused" in summary.failed[0][1]
    assert record["mechanism"]["blade_steel"] is None


def test_run_research_only_id_narrows_the_pass() -> None:
    first = make_record()
    first["mechanism"]["blade_steel"] = None
    second = make_record(id="second")
    second["mechanism"]["lock_type"] = None
    db = {"knives": [first, second]}
    fetched: list[str] = []

    def fetch(url: str) -> Listing:
        fetched.append(url)
        return make_listing()

    summary = research.run_research(db, fetch=fetch, only_id="second", on_date="2026-07-23")
    assert [r.knife_id for r in summary.reports] == ["second"]
    assert len(fetched) == 1
    assert first["mechanism"]["blade_steel"] is None


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
    print("all research tests passed")


if __name__ == "__main__":
    main()


# KnifeView import is exercised via knife_views in the docket test; keep
# the symbol referenced so linters see the intent.
_ = KnifeView
