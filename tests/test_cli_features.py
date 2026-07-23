"""End-to-end CLI tests for ingestion, update/new freshness, sections, buylist.

Plain-python runner (no pytest dependency):  python tests/test_cli_features.py
Each test runs against a throwaway database directory.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from typer.testing import CliRunner  # noqa: E402

import knivves.store as store  # noqa: E402
from knivves.cli import app  # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "knife-additions.md"
runner = CliRunner()


def fresh_db(tmp: Path) -> Path:
    db_path = tmp / "knives.json"
    db_path.write_text(
        json.dumps(
            {
                "database_name": "test",
                "version": "0.0",
                "knives": [
                    {
                        "id": "legacy-knife",
                        "brand": "Legacy",
                        "model": "Knife (LG1)",
                        "user_classification": "approved",
                        "user_tags": ["fancy"],
                        "canadian_online_retailers": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return db_path


def use_tmp() -> Path:
    tmp = Path(tempfile.mkdtemp())
    store.APP_DIR = tmp
    store.USER_DB = fresh_db(tmp)
    store.BACKUP_DIR = tmp / "backups"
    return tmp


def load() -> dict:
    return json.loads(store.USER_DB.read_text(encoding="utf-8"))


def invoke(*args: str):
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, f"{args}: exit {result.exit_code}\n{result.output}\n{result.exception}"
    return result


def test_add_markdown_dry_run_changes_nothing() -> None:
    use_tmp()
    before = load()
    result = invoke("add", str(FIXTURE), "--dry-run")
    assert load() == before
    assert "BUY LIST" in result.output.upper()


def test_add_markdown_ingests_and_orders_buylist() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    db = load()
    assert len(db["knives"]) > 1
    priorities = [item["priority"] for item in db["buy_list"]["items"]]
    assert priorities == sorted(priorities) and priorities[0] == 1
    added = [k for k in db["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is True for k in added)
    assert db.get("sources"), "sources registry missing"
    assert not any("XX999" in json.dumps(k) for k in db["knives"])


def test_update_seals_batch_as_new_and_empty_updates_hold() -> None:
    # `knivves update` is the line that TAGS the fresh batch as NEW —
    # the batch survives the update that seals it, and an update that
    # files nothing HOLDS the line (regression: back-to-back updates
    # must not erase freshness)
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    invoke("update", "--note", "test refresh")
    db = load()
    assert db["updates"]["generation"] == 2
    assert db["updates"]["history"][-1]["note"] == "test refresh"
    added = [k for k in db["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is True for k in added), "first update killed its own batch"
    result = invoke("update")  # nothing filed since — the line holds
    assert "holds" in result.output
    db = load()
    assert db["updates"]["generation"] == 2, "empty update moved the line"
    added = [k for k in db["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is True for k in added), "empty update erased freshness"
    invoke("update", "--force")  # deliberate aging
    added = [k for k in load()["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is False for k in added)


def test_new_threeg_extends_cache() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    invoke("update")
    invoke("update", "--force")
    added = [k for k in load()["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is False for k in added)
    invoke("new", "-threeg")
    db = load()
    assert db["updates"]["keep_generations"] == 3
    added = [k for k in db["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is True for k in added)


def test_update_survey_shows_progress_and_records_history() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")

    import knivves.scrape as scrape_mod

    def stub_listing(url: str, timeout: float = 30.0) -> scrape_mod.Listing:
        return scrape_mod.Listing(
            url=url, retailer="stub", listing_title="stub",
            price_cad=42.0, availability="in stock",
        )

    real_fetch = scrape_mod.fetch_listing
    scrape_mod.fetch_listing = stub_listing
    try:
        result = invoke("update", "--survey")
    finally:
        scrape_mod.fetch_listing = real_fetch

    assert "surveying the market" in result.output
    assert "first price" in result.output  # ingested knives were unpriced
    db = load()
    surveyed = [
        k for k in db["knives"]
        if k["id"] != "legacy-knife" and (k.get("canadian_online_retailers") or [])
        and scrape_mod.is_supported(str(k["canadian_online_retailers"][0].get("url") or ""))
    ]
    assert surveyed
    for record in surveyed:
        assert record["canadian_online_retailers"][0]["listed_price_cad"] == 42.0
        history = record.get("price_history") or []
        assert history and history[-1]["price_cad"] == 42.0, f"no history on {record['id']}"
        assert "affordable" in record["user_tags"], f"$150 rule not applied to {record['id']}"
    # the batch the survey-update sealed is still NEW
    assert all(k.get("new") is True for k in surveyed)


def test_new_oneg_and_status() -> None:
    use_tmp()
    invoke("new", "-oneg")
    assert load()["updates"]["keep_generations"] == 1
    result = invoke("new", "--status")
    assert "generation" in result.output.lower()


def test_list_new_flag_filters() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    result = invoke("list", "-new", "-o", "ids")
    ids = [line.strip() for line in result.output.splitlines() if line.strip()]
    assert "legacy-knife" not in ids
    assert len(ids) >= 5


def test_list_section_filter_matches_tag_alias() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    by_section = invoke("list", "-section", "buy_list", "-o", "ids").output.split()
    by_tag = invoke("list", "--tag", "buy_list", "-o", "ids").output.split()
    assert by_section == by_tag and len(by_section) == 4


def test_section_command_group_and_tag_alias() -> None:
    use_tmp()
    invoke("section", "add", "legacy-knife", "camping")
    assert "camping" in load()["knives"][0]["user_tags"]
    invoke("section", "remove", "legacy-knife", "camping")
    assert "camping" not in load()["knives"][0]["user_tags"]
    invoke("tag", "add", "legacy-knife", "edc")  # QOL alias stays
    assert "edc" in load()["knives"][0]["user_tags"]


def test_buylist_command_shows_cumulative() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    result = invoke("buylist")
    assert "RESERVE" in result.output.upper() or "BUY" in result.output.upper()
    invoke("list")  # buylist window on the list page must not crash


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
    print("all cli feature tests passed")


if __name__ == "__main__":
    main()
