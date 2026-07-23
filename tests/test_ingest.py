"""Tests for the markdown ingestion engine — lexer, parser, planner.

Plain-python runner (no pytest dependency):  python tests/test_ingest.py
Every malformed-input case here is lifted verbatim from real TODO.md data.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from knivves import ingest  # noqa: E402

FIXTURE = (REPO / "tests" / "fixtures" / "knife-additions.md").read_text(encoding="utf-8")


def _doc() -> "ingest.Document":
    return ingest.parse_document(FIXTURE)


def _section(doc, needle: str):
    for section in doc.sections:
        if needle.lower() in section.name.lower():
            return section
    raise AssertionError(f"no section matching {needle!r}: {[s.name for s in doc.sections]}")


# ------------------------------------------------------------------- lexer

def test_lex_exact_sli() -> None:
    tokens = ingest.lex("-" * 31 + "\n# T\n")
    assert tokens[0].kind == "SLI"
    assert tokens[1].kind == "H1"


def test_lex_short_dash_run_is_sli_with_warning() -> None:
    diagnostics: list = []
    tokens = ingest.lex("------------\n", diagnostics)
    assert tokens[0].kind == "SLI"
    assert any("31" in d.message for d in diagnostics)


def test_lex_section_entry_blank_prose() -> None:
    tokens = ingest.lex("// A\n\n- [x](https://a.b)\n> note\n")
    assert [t.kind for t in tokens] == ["SECTION", "BLANK", "ENTRY", "PROSE"]


def test_lex_skips_fenced_blocks() -> None:
    tokens = ingest.lex("```markdown\n- [x](https://a.b)\n```\n- [y](https://c.d)\n")
    kinds = [t.kind for t in tokens]
    assert kinds.count("ENTRY") == 1


# ------------------------------------------------------------------ parser

def test_document_title_and_sections() -> None:
    doc = _doc()
    assert doc.title == "KNIFE ADDITIONS"
    names = [s.name for s in doc.sections]
    assert "ForCamping" not in names  # fenced example skipped
    assert len(doc.sections) == 4
    kinds = [s.kind for s in doc.sections]
    assert kinds == ["buylist", "sources", "knives", "knives"]


def test_buylist_note_and_inline_annotation() -> None:
    section = _section(_doc(), "BUY LIST")
    assert any("DESCENDING" in note or "numerical order" in note for note in section.notes)
    assert len(section.entries) == 4
    kershaw = section.entries[-1]
    assert kershaw.source_name == "Canadian Tire"
    assert set(kershaw.tags) == {"new_source", "affordable_source"}
    # entries before the annotation are untouched by it
    assert section.entries[0].source_name is None


def test_hash_reference_normalized() -> None:
    kershaw = _section(_doc(), "BUY LIST").entries[-1]
    assert kershaw.sku == "175-2469-8"
    assert "#" not in kershaw.model


def test_bracket_reference_normalized_to_dash() -> None:
    toddler = _section(_doc(), "BUY LIST").entries[1]
    assert toddler.sku == "BG64C"
    assert toddler.brand == "Bestech"


def test_split_url_continuation_joined() -> None:
    psyop = _section(_doc(), "UNSORTED").entries[0]
    assert psyop.url == (
        "https://www.bladescanada.com/Vosteed-Knives/"
        "Vosteed-Psyop-Button-Lock-Flipper-Folding-Knife-Elmax-Satin-Titanium-Grey-Curved-A2204"
    )
    assert psyop.sku == "A2204"
    assert any("continuation" in r for r in psyop.repairs)


def test_swapped_label_and_url_repaired() -> None:
    duoz = next(e for e in _section(_doc(), "UNSORTED").entries if e.sku == "BG65F")
    assert duoz.url.startswith("https://www.bladescanada.com/Bestech-Knives/")
    assert duoz.brand == "Bestech"
    assert any("swap" in r for r in duoz.repairs)


def test_angle_url_with_stray_parens_repaired() -> None:
    batwing = next(e for e in _section(_doc(), "UNSORTED").entries if e.brand == "Trivisa")
    assert batwing.url.endswith("JM10S-BG-14")
    assert "()" not in batwing.url and "<" not in batwing.url


def test_tracking_query_params_stripped() -> None:
    kunwu = next(e for e in _section(_doc(), "UNSORTED").entries if e.brand == "Kunwu")
    assert "srsltid" not in kunwu.url
    assert kunwu.url.endswith("kunwu-gringo-verta-titanium-honeydew-b712t-r2-1/")


def test_todo_label_derives_title_from_url() -> None:
    doc = _doc()
    cobber = doc.sections[-1].entries[0]
    assert cobber.brand == "Bestech"
    assert "Cobber" in cobber.model
    assert cobber.sku == "BG68A"
    assert any("url" in r for r in cobber.repairs)


def test_sources_section_kind() -> None:
    sources = _section(_doc(), "MAIN SOURCES")
    assert sources.kind == "sources"
    assert len(sources.entries) == 2


# ------------------------------------------------------------- parse_title

def test_parse_title_comma_form() -> None:
    parsed = ingest.parse_title("DreamTech Flipper Folding Knife, D2 Satin, Titanium Grey, D4285TG")
    assert parsed.brand == "DreamTech"
    assert parsed.sku == "D4285TG"
    assert parsed.model == "Flipper Folding Knife (D4285TG)"
    assert parsed.steel == "D2"


def test_parse_title_dash_form() -> None:
    parsed = ingest.parse_title("Bestech Swordfish Satin 14C28N G10 Black/White - BG62B")
    assert parsed.brand == "Bestech"
    assert parsed.sku == "BG62B"
    assert parsed.steel == "14C28N"


def test_parse_title_multiword_brand() -> None:
    parsed = ingest.parse_title(
        "WE Knife Flight Line Flipper Folding Knife, Limited Edition, M390 Satin, Titanium Bead Blasted, WE23089-3"
    )
    assert parsed.brand == "WE Knife"
    assert parsed.sku == "WE23089-3"


def test_parse_title_brand_typo_normalized() -> None:
    parsed = ingest.parse_title("Bestchman Velix Flipper Button Lock Folding Knife, 14C28N Two-Tone, G10 Black, BMK07A")
    assert parsed.brand == "Bestechman"


def test_parse_title_measurement_not_sku() -> None:
    parsed = ingest.parse_title("Gerber Ripstop II Stainless Steel Fine Edge Folding Pocket Knife, 7.4-in")
    assert parsed.sku is None


# ------------------------------------------------------------------- plan

def _existing_db() -> dict:
    return {
        "knives": [
            {
                "id": "bestech-swordfish-bg62b",
                "brand": "Bestech",
                "model": "Swordfish Satin 14C28N G10 Black/White (BG62B)",
                "user_tags": ["under_100"],
                "canadian_online_retailers": [
                    {
                        "retailer": "House of Knives",
                        "url": "https://houseofknives.ca/bestech-swordfish-satin-14c28n-g10-black-white-bg62b/",
                    }
                ],
            }
        ]
    }


def test_plan_dedupes_in_file_and_merges_existing() -> None:
    db = _existing_db()
    plan = ingest.build_plan(_doc(), db)
    skus = [r.get("_sku") for r in plan.new_records]
    assert skus.count("S25104-3") == 1  # triple entry collapsed
    assert skus.count("D4285TG") == 1  # buylist + unsorted collapsed
    assert all(sku != "BG62B" for sku in skus)  # existing knife not re-added
    merged_ids = [m[0] for m in plan.merges]
    assert "bestech-swordfish-bg62b" in merged_ids
    assert len(plan.sources) == 2
    assert plan.buylist_keys, "buylist ordering missing"


def test_plan_sections_and_tags_assigned() -> None:
    plan = ingest.build_plan(_doc(), {"knives": []})
    dream = next(r for r in plan.new_records if r.get("_sku") == "D4285TG")
    assert "buy_list" in dream["user_tags"]
    assert "unsorted" in dream["user_tags"]
    kershaw = next(r for r in plan.new_records if r.get("_sku") == "175-2469-8")
    assert {"new_source", "affordable_source", "buy_list"} <= set(kershaw["user_tags"])
    assert kershaw["canadian_online_retailers"][0]["retailer"] == "Canadian Tire"


def test_apply_plan_writes_everything() -> None:
    db = _existing_db()
    plan = ingest.build_plan(_doc(), db)
    report = ingest.apply_plan(plan, db)
    assert report.added == len(plan.new_records) > 0
    assert report.merged == 1
    assert report.duplicates >= 2
    items = db["buy_list"]["items"]
    assert [item["priority"] for item in items] == [1, 2, 3, 4]
    assert any(item["id"] == "bestech-swordfish-bg62b" for item in items)
    by_id = {k["id"]: k for k in db["knives"]}
    assert by_id["bestech-swordfish-bg62b"].get("buy_priority") == 3
    for record in db["knives"]:
        if record["id"] != "bestech-swordfish-bg62b":
            assert record.get("new") is True
            assert "_sku" not in record
    assert len(db["sources"]) == 2
    assert all("XX999" not in str(record) for record in db["knives"])  # fenced example never ingested


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
    print("all ingest tests passed")


if __name__ == "__main__":
    main()
