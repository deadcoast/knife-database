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


def test_update_ages_out_new_at_default_keep() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    invoke("update", "--note", "test refresh")
    db = load()
    assert db["updates"]["generation"] == 2
    assert db["updates"]["history"][-1]["note"] == "test refresh"
    added = [k for k in db["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is False for k in added)


def test_new_threeg_extends_cache() -> None:
    use_tmp()
    invoke("add", str(FIXTURE), "--yes")
    invoke("update")
    invoke("new", "-threeg")
    db = load()
    assert db["updates"]["keep_generations"] == 3
    added = [k for k in db["knives"] if k["id"] != "legacy-knife"]
    assert all(k.get("new") is True for k in added)


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
