"""Headless tests for the application shell.

Plain-python runner (no pytest dependency):  python tests/test_tui_shell.py
Uses Textual's Pilot to drive real input against the composed app.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from textual.widgets import DataTable, Input, Static  # noqa: E402

import knivves.scrape as scrape_mod  # noqa: E402
from knivves.tui.app import KnivvesApp  # noqa: E402
from knivves.tui.pages.compare import CompareScreen  # noqa: E402
from knivves.tui.plate import Plate  # noqa: E402
from knivves.tui.pages.library import LibraryScreen  # noqa: E402
from knivves.tui.pages.imports import ImportsScreen, GateBank, TapeReader  # noqa: E402


def _clean_listing(url: str, timeout: float = 30.0) -> scrape_mod.Listing:
    return scrape_mod.Listing(
        url=url,
        retailer="Blades Canada / Warriors and Wonders",
        listing_title="Testbrand Testblade Folding Knife, 14C28N, G10 Black, TB123",
        brand="Testbrand",
        model="Testblade (TB123)",
        price_cad=99.99,
        availability="in stock",
        blade_steel="14C28N",
        lock_type="Liner Lock",
        opening_method="Thumb Stud, Flipper",
        blade_length="3.00 in",
        assisted=False,
    )


def _prohibited_listing(url: str, timeout: float = 30.0) -> scrape_mod.Listing:
    return scrape_mod.Listing(
        url=url,
        retailer="Blades Canada / Warriors and Wonders",
        listing_title="Badbrand Balisong Butterfly Trainer, Stainless, BB666",
        brand="Badbrand",
        model="Balisong Trainer (BB666)",
        price_cad=49.99,
    )


async def test_shell() -> None:
    # intake writes to the database: run the whole suite on a throwaway copy
    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await pilot.pause()

        # cold boot: the vault door holds the brand, then opens into the hall
        from knivves.tui.door import VaultDoor
        from knivves.tui.pages.home import HomeScreen

        assert app.screen.query(VaultDoor), "boot door missing"
        await asyncio.sleep(2.3)
        await pilot.pause()
        assert not app.screen.query(VaultDoor), "boot door failed to open"

        # boot lands in the entry hall — the vault is a page
        assert isinstance(app.screen, HomeScreen), f"boot screen: {app.screen}"

        # door 1: the library with the full collection
        await pilot.press("1")
        await asyncio.sleep(1.1)
        await pilot.pause()
        assert isinstance(app.screen, LibraryScreen), f"screen: {app.screen}"
        for _ in range(30):  # the cascade lands late under load, never less
            if app.screen._reveal.settled:
                break
            await asyncio.sleep(0.1)
            await pilot.pause()
        table = app.screen.query_one(DataTable)
        n = len(app.knives)
        assert table.row_count == n > 0, f"{table.row_count} vs {n}"

        # click header sorts; click again reverses
        await pilot.click(DataTable, offset=(2, 0))
        await pilot.pause()
        assert app.screen.sort_column == "brand"
        first = table.get_row_at(0)[0]
        await pilot.click(DataTable, offset=(2, 0))
        await pilot.pause()
        assert app.screen.sort_reverse is True
        assert str(table.get_row_at(0)[0]) != str(first)

        # search filters everything searchable
        await pilot.click("#rack-search")
        await pilot.press(*"sebenza")
        await pilot.pause()
        assert 0 < table.row_count < n, f"filtered {table.row_count}"

        # row click: the plate travels in, carrying the record; the rack recedes
        await pilot.click(DataTable, offset=(4, 1))
        await asyncio.sleep(0.5)
        await pilot.pause()
        plate = app.screen.query_one(Plate)
        assert plate.has_class("open"), "plate did not open"
        body_offset = app.screen.query_one("#rack-body").styles.offset
        assert int(body_offset.x.value) == -2, f"depth nudge missing: {body_offset}"

        # escape sends the plate away and clears search; the rack steps forward
        await pilot.press("escape")
        await asyncio.sleep(0.6)
        await pilot.pause()
        assert not plate.has_class("open")
        assert app.screen.query_one("#rack-search", Input).value == ""
        body_offset = app.screen.query_one("#rack-body").styles.offset
        assert int(body_offset.x.value) == 0, f"depth did not return: {body_offset}"

        # ---- pass A polish: feedback, reach, zero-state ----
        search = app.screen.query_one("#rack-search", Input)
        assert str(search.border_subtitle).endswith(f"/ {n}"), f"subtitle: {search.border_subtitle}"
        # sort readout on the masthead
        from knivves.tui.masthead import Masthead
        context = app.screen.query_one(Masthead).context
        assert "sorted by brand" in context, f"context: {context}"
        # slash reaches the search from the table
        app.screen.query_one(DataTable).focus()
        await pilot.press("slash")
        await pilot.pause()
        assert app.focused is search, f"focused: {app.focused}"
        # zero-state is designed, not blank
        await pilot.press(*"zzqqxx")
        await pilot.pause()
        assert table.row_count == 0
        assert app.screen.query_one("#rack-empty", Static).display is True
        assert str(search.border_subtitle).startswith("0 /")
        await pilot.press("escape")
        await pilot.pause()
        assert table.row_count == n
        assert app.screen.query_one("#rack-empty", Static).display is False
        # palette exposes the building's rooms and operations — normalized names
        commands = {c.title for c in app.get_system_commands(app.screen)}
        for expected in ("Library", "Import Knives", "Compare Models", "Market Prices", "Update market prices"):
            assert expected in commands, f"palette missing: {expected}"

        # ---- tip system: rail on hover, capsule on demand ----
        from knivves.tui.tips import TipCapsule, TipRail

        rail = app.screen.query_one(TipRail)
        # the rail sits directly beside the data's last column, never at the
        # viewport edge across a dead gap
        table_widget = app.screen.query_one(DataTable)
        table_right = table_widget.region.x + table_widget.region.width
        gap = rail.region.x - table_right
        assert 0 <= gap <= 3, f"rail is {gap} cells from the data edge"
        assert rail.region.x + rail.region.width < app.size.width - 10, (
            "rail is pinned to the viewport edge"
        )
        await pilot.hover("#rack-search")
        await pilot.pause()
        assert rail.current and "live filter" in rail.current.short, f"rail: {rail.current}"
        assert rail.has_class("expandable"), "❯ mark missing on expandable tip"
        await pilot.press("t")
        await pilot.pause()
        capsule = app.screen.query_one(TipCapsule)
        assert capsule.has_class("open"), "capsule did not open"
        capsule_body = str(capsule.query_one(".capsule--body", Static).render())
        assert "magnacut" in capsule_body, f"capsule body: {capsule_body[:60]}"
        await pilot.press("escape")
        await pilot.pause()
        assert not capsule.has_class("open"), "escape did not close capsule"
        # a tip with no extended content shows no ❯ mark
        # the door lives ~0.8s and press() blocks until the reveal's
        # transitions go idle — watch for the door concurrently
        async def _see_door() -> bool:
            for _ in range(24):
                if app.screen.query(VaultDoor):
                    return True
                await asyncio.sleep(0.05)
            return False

        watcher = asyncio.ensure_future(_see_door())
        await pilot.press("2")
        assert await watcher, "room door missing on arrival"
        await asyncio.sleep(1.1)
        await pilot.pause()
        forge_rail = app.screen.query_one(TipRail)
        await pilot.hover("#st-extract", offset=(4, 2))
        await pilot.pause()
        assert forge_rail.current and "stamped here" in forge_rail.current.short
        assert forge_rail.has_class("expandable"), "tape tip has extended content — ❯ missing"
        await pilot.hover("#st-vault", offset=(4, 2))
        await pilot.pause()
        assert forge_rail.current and "file here" in forge_rail.current.short
        assert not forge_rail.has_class("expandable"), "❯ shown without extended content"
        await pilot.press("1")
        await pilot.pause()

        # room switch: 2 -> forge line, transit completes on real rules
        await pilot.press("2")
        await pilot.pause()
        assert isinstance(app.screen, ImportsScreen), f"screen: {app.screen}"
        await asyncio.sleep(10.5)
        await pilot.pause()
        gates_text = str(app.screen.query_one("#gates", Static).render())
        filed_text = str(app.screen.query_one("#filed", Static).render())
        assert "CLEAR TO PROCEED" in gates_text, f"gates: {gates_text[:80]}"
        assert "nothing was saved" in filed_text, f"filed: {filed_text[:80]}"
        # the legal screen is a seven-bolt lock: the demo retracts every bolt
        bank = app.screen.query_one(GateBank)
        assert bank.total == 7, f"bolts: {bank.total}"
        assert bank.open_count == 7, f"open bolts: {bank.open_count}"
        assert bank.slammed is None, "demo threw a bolt"
        # the tape reader lights the substrings the parse actually used
        tape = app.screen.query_one(TapeReader)
        assert tape.lit_count >= 1, "demo tape lights nothing"
        from knivves.tui.masthead import Masthead as MastheadWidget
        forge_context = app.screen.query_one(MastheadWidget).context
        assert "idle" in forge_context, f"context: {forge_context}"
        # the traveling plate never clips off screen, whatever its height
        from knivves.tui.plate import Plate as PlateWidget
        forge_plate = app.screen.query_one(PlateWidget)
        plate_bottom = forge_plate.region.y + forge_plate.region.height
        assert plate_bottom <= app.size.height, f"plate clips: bottom {plate_bottom} vs screen {app.size.height}"

        # room switch back: 1 -> the rack, state intact
        await pilot.press("1")
        await pilot.pause()
        assert isinstance(app.screen, LibraryScreen)

        # send-to-bench: `b` carries the highlighted knife's plate to the bench
        await pilot.press("b")
        await pilot.pause()
        assert isinstance(app.screen, CompareScreen), f"screen: {app.screen}"
        assert len(app.screen.slots) == 1, f"slots: {len(app.screen.slots)}"
        first_id = app.screen.slots[0].id

        # second knife -> choreographed arrival, then the calipers measure
        await pilot.press("1")
        await pilot.pause()
        for _ in range(30):  # the cascade lands late under load, never less
            if app.screen._reveal.settled:
                break
            await asyncio.sleep(0.1)
            await pilot.pause()
        await pilot.press("down", "down", "b")
        await pilot.pause()
        assert len(app.screen.slots) == 2, f"slots: {len(app.screen.slots)}"
        assert app.screen.slots[0].id == first_id
        await asyncio.sleep(3.2)  # arrival travel + the jaws closing per beam
        await pilot.pause()
        # the calipers are an instrument now: beams with jaws on a shared
        # scale for the numeric facts, linkages for the categorical ones
        from knivves.tui.pages.compare import Calipers

        cal = app.screen.query_one(Calipers)
        assert cal.measured == tuple(k.id for k in app.screen.slots), "calipers did not read the pair"
        assert len(cal.beams) == 2 and len(cal.links) == 3, "instrument rows missing"
        assert all(b.delta is not None or b.missing for b in cal.beams), "a beam is neither read nor honest"
        assert app.screen._seated == [k.id for k in app.screen.slots], "seating not tracked"
        from knivves.tui.masthead import Masthead as MH
        bench_ctx = app.screen.query_one(MH).context
        assert " vs " in bench_ctx, f"bench state: {bench_ctx}"
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("b")  # same highlighted row as slot 2 -> dedupe
        await pilot.pause()
        assert len(app.screen.slots) == 2, "duplicate was not refused"

        # escape clears the bench
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen.slots) == 0

        # ---- classification: the vault judges, the database records ----
        await pilot.press("1")
        await asyncio.sleep(1.1)
        await pilot.pause()
        await pilot.click(DataTable, offset=(4, 1))  # open first row's plate
        await pilot.pause()
        judged_id = app.screen._plate_knife_id
        prior = next(k.classification for k in app.knives if k.id == judged_id)
        await pilot.press("a")
        await pilot.pause()
        on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
        rec = next(k for k in on_disk["knives"] if k["id"] == judged_id)
        assert rec["user_classification"] == "approved", rec["user_classification"]
        await pilot.press("x")
        await pilot.pause()
        on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
        rec = next(k for k in on_disk["knives"] if k["id"] == judged_id)
        assert rec["user_classification"] == "rejected"
        await pilot.press("u")
        await pilot.pause()
        on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
        rec = next(k for k in on_disk["knives"] if k["id"] == judged_id)
        assert rec["user_classification"] is None
        # restore the record's original state for later assertions
        app.classify(judged_id, prior if prior != "unclassified" else None)
        await pilot.press("escape")
        await pilot.pause()

        # ---- live intake (stubbed fetcher, real filing) ----
        real_fetch = scrape_mod.fetch_listing
        try:
            scrape_mod.fetch_listing = _clean_listing
            await pilot.press("2")
            await asyncio.sleep(1.1)
            await pilot.pause()
            intake = app.screen.query_one("#forge-intake", Input)
            intake.focus()
            intake.value = "https://www.bladescanada.com/Testbrand-Knives/test-listing"
            await pilot.press("enter")
            await asyncio.sleep(10.0)
            await pilot.pause()
            filed_text = str(app.screen.query_one("#filed", Static).render())
            assert "Testbrand" in filed_text and "filed" in filed_text, f"filed: {filed_text[:100]}"
            assert app.screen.query_one(GateBank).open_count == 7, "live intake left bolts thrown"
            assert app.screen.query_one(TapeReader).lit_count >= 2, "tape spans not lit on live intake"
            on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
            ids = {k["id"] for k in on_disk["knives"]}
            assert "testbrand-testblade-tb123" in ids, "record not written to database"
            filed_rec = next(k for k in on_disk["knives"] if k["id"] == "testbrand-testblade-tb123")
            assert filed_rec["user_tags"] == ["affordable"], "under-$150 auto tag missing"
            assert len(app.knives) == n + 1

            # rack reflects the filing on return (cascade settles first)
            await pilot.press("1")
            await asyncio.sleep(1.1)
            await pilot.pause()
            rows_now = app.screen.query_one(DataTable).row_count
            for _ in range(20):  # the cascade's last batch may still be landing
                if rows_now == n + 1:
                    break
                await asyncio.sleep(0.1)
                await pilot.pause()
                rows_now = app.screen.query_one(DataTable).row_count
            assert rows_now == n + 1, f"rows {rows_now} vs {n + 1}"

            # duplicate URL is refused without refetching
            await pilot.press("2")
            await pilot.pause()
            intake = app.screen.query_one("#forge-intake", Input)
            intake.focus()
            intake.value = "https://www.bladescanada.com/Testbrand-Knives/test-listing"
            await pilot.press("enter")
            await asyncio.sleep(1.0)
            await pilot.pause()
            log_text = str(app.screen.query_one("#extract-log", Static).render())
            assert "already in the database" in log_text, f"log: {log_text[:80]}"

            # prohibited listing: gate slams, nothing filed
            scrape_mod.fetch_listing = _prohibited_listing
            intake.focus()
            intake.value = "https://www.bladescanada.com/Badbrand-Knives/balisong-trainer"
            await pilot.press("enter")
            await asyncio.sleep(8.0)
            await pilot.pause()
            gates_now = str(app.screen.query_one("#gates", Static).render())
            filed_now = str(app.screen.query_one("#filed", Static).render())
            assert "✗" in gates_now, f"gates: {gates_now[:100]}"
            assert "not filed" in filed_now, f"filed: {filed_now[:100]}"
            assert app.screen.query_one(GateBank).slammed is not None, "prohibited hit threw no bolt"
            on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
            assert len(on_disk["knives"]) == n + 1, "prohibited record was written"
            # ---- the ledger: survey with a stubbed market ----
            from knivves.tui.pages.market import MarketScreen

            MarketScreen.SURVEY_DELAY = 0
            baseline: dict[str, float] = {
                k.id: k.price for k in app.knives if k.price is not None
            }

            def falling_market(url: str, timeout: float = 30.0) -> scrape_mod.Listing:
                old = next(
                    (p for kid, p in baseline.items()
                     if any(r.get("url") == url for k in app.knives if k.id == kid for r in k.retailers)),
                    100.0,
                )
                return scrape_mod.Listing(
                    url=url, retailer="stub", listing_title="stub",
                    price_cad=round(old * 0.9, 2), availability="in stock",
                )

            scrape_mod.fetch_listing = falling_market
            await pilot.press("4")
            await pilot.pause()
            assert isinstance(app.screen, MarketScreen), f"screen: {app.screen}"
            valuation = str(app.screen.query_one("#valuation-read", Static).render())
            assert "value" in valuation.lower(), f"valuation: {valuation[:80]}"
            from knivves.tui.gauges import GradientBars, PriceScale
            assert app.screen.query_one(PriceScale)._prices, "price scale empty"
            assert sum(c for _, c in app.screen.query_one(GradientBars)._buckets) > 0, "bars empty"
            await pilot.press("s")
            await asyncio.sleep(6.0)
            await pilot.pause()
            movers_text = str(app.screen.query_one("#movers-read", Static).render())
            assert "survey complete" in movers_text, f"movers: {movers_text[:100]}"
            assert "▼" in movers_text, "no downward movers shown"
            # pass D: survey lifecycle reads on the masthead; line panel shows distance
            ledger_ctx = app.screen.query_one(MH).context
            assert "survey complete" in ledger_ctx, f"ledger context: {ledger_ctx}"
            line_text = str(app.screen.query_one("#line-read", Static).render())
            assert "Δ$" in line_text or "nothing near the line" in line_text, f"line: {line_text[:80]}"
            on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
            surveyed = [k for k in on_disk["knives"] if len(k.get("price_history") or []) >= 2]
            assert len(surveyed) > 50, f"history recorded on only {len(surveyed)}"
            # a knife that fell through the $150 line is re-tagged affordable
            crossed = [
                k for k in on_disk["knives"]
                if k["id"] in baseline and 150 <= baseline[k["id"]] < 166.67
            ]
            assert crossed, "no knife crossed the line in this dataset"
            assert all("affordable" in k["user_tags"] for k in crossed), "line-crossers not re-tagged"
        finally:
            scrape_mod.fetch_listing = real_fetch

        print(
            f"PASS: shell boots · rack {n} rows · sort+reverse · search · plate travel · "
            f"forge transit · rooms · bench · live intake files/dedupes/rejects · "
            f"ledger survey records history, shows movers, re-tags line-crossers"
        )


async def test_freshness_and_reserve() -> None:
    """NEW chips on the rack, the masthead new-count, and The Reserve panel."""
    from textual.coordinate import Coordinate

    from knivves.tui.reserve import Reserve

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    db = json.loads((REPO / "knivves" / "data" / "knives.json").read_text(encoding="utf-8"))
    # neutralize whatever freshness the shipped data carries, then stamp
    # exactly two records as freshly filed and rank them in the reserve
    for record in db["knives"]:
        record.pop("new", None)
        record.pop("added_generation", None)
        record.pop("buy_priority", None)
    db.pop("buy_list", None)
    first, second = db["knives"][0], db["knives"][1]
    for record in (first, second):
        record["new"] = True
        record["added_generation"] = 1
    first["buy_priority"], second["buy_priority"] = 1, 2
    db["buy_list"] = {
        "updated": "2026-07-23",
        "items": [{"id": first["id"], "priority": 1}, {"id": second["id"], "priority": 2}],
    }
    db["updates"] = {"generation": 1, "keep_generations": 1, "history": []}
    tmp_db.write_text(json.dumps(db), encoding="utf-8")

    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        await pilot.press("1")
        await asyncio.sleep(1.1)
        await pilot.pause()
        assert isinstance(app.screen, LibraryScreen)

        # ★new aligns in the gutter — start of the Model cell; the sections
        # cell keeps only the reserve rank
        table = app.screen.query_one(DataTable)
        row = table.get_row_at(0)
        model_cell = str(row[1])
        assert model_cell.startswith("★new "), f"model cell: {model_cell!r}"
        sections_cell = str(row[5])
        assert "new" not in sections_cell, f"★new left in sections cell: {sections_cell!r}"
        assert "⬖1" in sections_cell, f"priority mark missing: {sections_cell!r}"

        # the masthead counts the fresh arrivals
        from knivves.tui.masthead import Masthead

        stats_text = "".join(text for text, _, _ in app.screen.query_one(Masthead)._stats)
        assert "2 new" in stats_text, f"masthead stats: {stats_text}"

        # y: the reserve travels in, carrying priorities and the running cost
        reserve = app.screen.query_one(Reserve)
        assert not reserve.has_class("open")
        await pilot.press("y")
        await asyncio.sleep(0.5)
        await pilot.pause()
        assert reserve.has_class("open"), "reserve did not open"
        body = str(app.screen.query_one(".reserve--body", Static).render())
        footer = str(app.screen.query_one(".reserve--footer", Static).render())
        assert "1 " in body and "2 " in body, f"reserve body: {body[:120]}"
        assert "2 priorities" in footer, f"reserve footer: {footer[:120]}"

        # escape retires the reserve before touching plate or search
        await pilot.press("escape")
        await asyncio.sleep(0.6)
        await pilot.pause()
        assert not reserve.has_class("open"), "escape did not retire the reserve"

    print("PASS: rack NEW chips · masthead new-count · reserve travels in and out")


async def test_file_import_transit() -> None:
    """Import Knives runs an ingestion .md down the line and files a batch."""
    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    before = len(json.loads(tmp_db.read_text(encoding="utf-8"))["knives"])
    ledger_path = REPO / "tests" / "fixtures" / "knife-additions.md"

    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        await pilot.press("2")
        await asyncio.sleep(1.2)
        await pilot.pause()
        assert isinstance(app.screen, ImportsScreen)
        intake = app.screen.query_one("#forge-intake", Input)
        intake.focus()
        intake.value = str(ledger_path)
        await pilot.press("enter")
        await asyncio.sleep(6.0)
        await pilot.pause()
        filed_text = str(app.screen.query_one("#filed", Static).render())
        assert "filed" in filed_text and "★new" in filed_text, f"filed: {filed_text[:120]}"
        gates_text = str(app.screen.query_one("#gates", Static).render())
        assert "THE PLAN" in gates_text, f"gates: {gates_text[:120]}"
        assert app.screen.query_one(GateBank).slammed is None, "file intake touched the lock"
        on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
        assert len(on_disk["knives"]) > before, "file import wrote nothing"
        assert on_disk.get("buy_list", {}).get("items"), "buy list not ordered"
        assert len(app.knives) == len(on_disk["knives"]), "views not refreshed"

    print(f"PASS: import knives file intake · {len(on_disk['knives']) - before} filed from the ledger")


async def test_desk_demo_transit() -> None:
    """Door 5 — Research: the demo transit stamps learned fields without
    writing; `s` works the docket for real; the Library plate carries the
    UNRESEARCHED chip (case 2026-07-23-research-desk, REQ-RES-5/6)."""
    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    db = {
        "database_name": "desk-test",
        "version": "0.0",
        "workflow_rules": {
            "canadian_online_retailer_rule": {
                "only_reject_or_fail_if_clear_prohibited_mechanism": ["balisong", "butterfly knife"],
            },
        },
        "knives": [
            {
                # complete — the demo transit's sample subject
                "id": "complete-knife", "brand": "Spyderco", "model": "Manix 2 (C101)",
                "user_classification": None, "user_tags": [],
                "mechanism": {
                    "opening_method": "Thumb Hole", "lock_type": "Ball Bearing Lock",
                    "assist_type": "manual", "blade_length": "3.37 in",
                    "blade_steel": "S30V", "clear_prohibited_mechanism_found": False,
                },
                "canadian_online_retailers": [{
                    "retailer": "Blades Canada / Warriors and Wonders",
                    "url": "https://www.bladescanada.com/Spyderco-Knives/Manix",
                    "listed_price_cad": 219.99, "availability": "in stock",
                    "source_date": "2026-07-01",
                }],
                "listing_title": "Spyderco Manix 2, S30V", "notes": "", "source_input": "",
            },
            {
                # gapped, supported URL — the live pass researches this one
                "id": "research-target", "brand": "Kubey", "model": "Vagabond (KU2101)",
                "user_classification": None, "user_tags": [],
                "mechanism": {
                    "opening_method": None, "lock_type": None, "assist_type": "unknown",
                    "blade_length": None, "blade_steel": None,
                    "clear_prohibited_mechanism_found": False,
                },
                "canadian_online_retailers": [{
                    "retailer": "Blades Canada / Warriors and Wonders",
                    "url": "https://www.bladescanada.com/Kubey-Knives/Kubey-Vagabond-KU2101",
                    "listed_price_cad": None, "availability": "unknown",
                    "source_date": "2026-07-01",
                }],
                "listing_title": "", "notes": "", "source_input": "",
            },
        ],
    }
    tmp_db.write_text(json.dumps(db), encoding="utf-8")
    before_bytes = tmp_db.read_bytes()

    from knivves.tui.pages.research import ResearchScreen

    real_fetch = scrape_mod.fetch_listing
    scrape_mod.fetch_listing = _clean_listing
    try:
        app = KnivvesApp(db_path=tmp_db)
        async with app.run_test(size=(170, 45)) as pilot:
            await asyncio.sleep(2.3)
            await pilot.pause()
            await pilot.press("1")
            await asyncio.sleep(1.1)
            await pilot.pause()

            # the Library plate carries the record's incompleteness (REQ-RES-6)
            await pilot.click("#rack-search")
            await pilot.press(*"research-target")
            await pilot.pause()
            await pilot.click(DataTable, offset=(4, 1))
            await asyncio.sleep(0.6)
            await pilot.pause()
            plate_body = str(app.screen.query_one(".plate--body", Static).render())
            assert "unresearched" in plate_body, f"plate chip missing: {plate_body[:120]}"
            await pilot.press("escape")
            await asyncio.sleep(0.6)

            # door 5 — the demo transit runs on arrival, writes nothing
            await pilot.press("5")
            await asyncio.sleep(1.0)
            await pilot.pause()
            assert isinstance(app.screen, ResearchScreen), f"screen: {app.screen}"
            await asyncio.sleep(6.0)  # power-on reveal, then the demo transit
            await pilot.pause()
            docket_text = " ".join(
                str(card.render()) for card in app.screen.query(".docket-card")
            )
            assert "research-target" in docket_text, f"docket: {docket_text[:160]}"
            stamped_text = str(app.screen.query_one("#stamped", Static).render())
            assert "nothing was saved" in stamped_text, f"stamped: {stamped_text[:120]}"
            assert tmp_db.read_bytes() == before_bytes, "demo transit wrote the database"
            plate = app.screen.query_one(Plate)
            stamp_x = app.screen.query_one("#st-stamp").region.x
            assert plate.region.x >= stamp_x, f"plate at {plate.region.x}, stamp at {stamp_x}"

            # the unknowns map draws every record as a column; the target's
            # column carries its missing-field sockets
            from knivves.tui.pages.research import UnknownsMap

            unknowns = app.screen.query_one(UnknownsMap)
            assert unknowns.records == 2, f"map columns: {unknowns.records}"
            assert unknowns.complete == 1, f"map complete: {unknowns.complete}"
            assert unknowns.wake == 0, "demo must not leave a wake on the map"

            # s — the live pass fills the target through the stubbed listing
            await pilot.press("s")
            await asyncio.sleep(6.0)
            await pilot.pause()
            on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
            record = next(k for k in on_disk["knives"] if k["id"] == "research-target")
            assert record["mechanism"]["blade_steel"] == "14C28N", "steel not filled"
            assert record["canadian_online_retailers"][0]["listed_price_cad"] == 99.99
            assert record["research"]["filled"]["steel"] == "bladescanada.com"
            assert record["price_history"], "first price must seed history"
            docket_after = " ".join(
                str(card.render()) for card in app.screen.query(".docket-card")
            )
            assert "research-target" not in docket_after, "worked record still on the docket"
            empty_state = str(app.screen.query_one("#docket-empty", Static).render())
            assert "fully researched" in empty_state, f"docket after: {empty_state[:80]}"
            # the live pass leaves its amber wake on the map: the cells it
            # filled burn accent, and the vault reads complete
            assert unknowns.complete == 2, f"map complete after pass: {unknowns.complete}"
            assert unknowns.wake >= 5, f"wake cells: {unknowns.wake}"
    finally:
        scrape_mod.fetch_listing = real_fetch

    print("PASS: research desk · library chip · demo transit writes nothing · s fills the docket")


def test_pages_map_to_doors() -> None:
    """The source organization matches the doors (REQ-ARC-1): every screen
    lives in ``pages/<key>.py`` as ``<Key>Screen``; every number key opens
    a registered page."""
    for key, screen_cls in KnivvesApp.SCREENS.items():
        expected_module = f"knivves.tui.pages.{key}"
        assert screen_cls.__module__ == expected_module, (
            f"{screen_cls.__name__} lives in {screen_cls.__module__}, not {expected_module}"
        )
        assert screen_cls.__name__ == f"{key.capitalize()}Screen", screen_cls.__name__
    door_bindings = [b for b in KnivvesApp.BINDINGS if isinstance(b, tuple) and b[1].startswith("room(")]
    assert len(door_bindings) == len(KnivvesApp.SCREENS), "a page has no door key"
    for _key, action, _label in door_bindings:
        target = action.split("'")[1]
        assert target in KnivvesApp.SCREENS, f"door key opens unregistered page: {target}"
    labels = {label for _, _, label in door_bindings}
    for expected in ("Home", "Library", "Import Knives", "Compare Models", "Market Prices", "Research"):
        assert expected in labels, f"door label missing: {expected}"
    print("PASS: pages map to doors — modules, screen classes, keys, labels agree")


def test_pages_own_stylesheets() -> None:
    """REQ-CSS-2: every page screen declares its sibling stylesheet; the
    app-level sheet carries only building chrome."""
    import inspect

    for key, screen_cls in KnivvesApp.SCREENS.items():
        assert screen_cls.CSS_PATH == f"{key}.tcss", f"{key}: {screen_cls.CSS_PATH}"
        sheet = Path(inspect.getfile(screen_cls)).parent / f"{key}.tcss"
        assert sheet.is_file(), f"missing stylesheet: {sheet}"
    app_css = (REPO / "knivves" / "tui" / "app.tcss").read_text(encoding="utf-8")
    page_markers = (
        "#rack", "#bench", "#calipers", "#ledger", "#forge", "#desk", "#hall",
        "LibraryScreen", "ImportsScreen", "CompareScreen", "MarketScreen",
        "ResearchScreen", "HomeScreen",
    )
    for marker in page_markers:
        assert marker not in app_css, f"page-specific selector in app.tcss: {marker}"
    print("PASS: per-page stylesheets — six sheets beside their modules, chrome-only app.tcss")


async def test_theme_is_the_only_palette() -> None:
    """REQ-CSS-1: the knivves theme is registered and active, its variables
    reach the stylesheets, and no .tcss in the building carries a raw color."""
    import re

    from knivves.tui import laws

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await pilot.pause()
        assert app.theme == "knivves", f"active theme: {app.theme}"
        theme = app.get_theme("knivves")
        assert theme is not None and theme.primary == laws.ACCENT
        assert app.theme_variables.get("edge") == laws.EDGE
        assert app.theme_variables.get("fresh") == laws.FRESH
    hex_or_rgb = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgb\(")
    sheets = sorted((REPO / "knivves" / "tui").rglob("*.tcss"))
    assert len(sheets) == 7, f"stylesheets: {[s.name for s in sheets]}"
    for sheet in sheets:
        found = hex_or_rgb.findall(sheet.read_text(encoding="utf-8"))
        assert not found, f"{sheet.name} carries raw color(s): {found}"
    print("PASS: one theme — knivves active, variables live, zero raw colors in any stylesheet")


async def test_reveal_runs_once_per_open() -> None:
    """REQ-MOT-1: the Reveal runner fires once per entrance, jumps to
    settled on demand, and re-arms when the page is left."""
    from knivves.tui import laws

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        hits: list[str] = []
        reveal = laws.Reveal(app.screen)
        played = reveal.play([
            (0, lambda: hits.append("a")),
            (0.05, lambda: hits.append("b")),
            (30.0, lambda: hits.append("c")),
        ])
        assert played, "first play refused"
        await asyncio.sleep(0.4)
        await pilot.pause()
        assert hits == ["a", "b"], f"cascade: {hits}"
        assert not reveal.settled, "settled with a step outstanding"
        reveal.settle()  # a keypress mid-reveal lands the tail instantly
        assert hits == ["a", "b", "c"], f"settle: {hits}"
        assert reveal.settled
        assert not reveal.play([(0, lambda: hits.append("again"))]), "replayed without re-arm"
        assert hits == ["a", "b", "c"]
        reveal.arm()
        assert reveal.play([(0, lambda: hits.append("return"))]), "re-arm did not re-enable"
        assert hits[-1] == "return"
    print("PASS: reveal — once per open · settle lands the tail · re-arms on re-entry")


def test_cues_declared_in_css() -> None:
    """REQ-MOT-2: pointer-facing pages declare their CUE transitions in
    their own stylesheets through the laws' $cue variables. (Compare and
    market are keyboard instruments — nothing there tracks the pointer.)"""
    pages_dir = REPO / "knivves" / "tui" / "pages"
    for page in ("home", "library", "imports"):
        css = (pages_dir / f"{page}.tcss").read_text(encoding="utf-8")
        assert "transition:" in css, f"{page}.tcss declares no transition"
        assert "$cue-duration" in css, f"{page}.tcss does not speak the cue law"
        assert ":hover" in css or ":focus" in css, f"{page}.tcss has no pointer state"
    print("PASS: cues in CSS — vault/library/imports answer the hand through the laws")


async def test_entry_hall_doors() -> None:
    """Page 0 — the vault (REQ-ARC-2): boot lands in the hall, the plaques
    read live state, number keys leave, 0 returns."""
    from knivves.tui.pages.market import MarketScreen
    from knivves.tui.pages.home import HomeScreen

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen), f"boot screen: {app.screen}"
        state = str(app.screen.query_one("#hall-state-body", Static).render())
        assert "KNIVES" in state and "AVG" in state, f"state plaque: {state[:80]}"
        assert "unresearched" in state, f"gaps line missing: {state[:120]}"
        doors = " ".join(str(row.render()) for row in app.screen.query(".door-row"))
        for name in ("LIBRARY", "IMPORT KNIVES", "COMPARE MODELS", "MARKET PRICES", "RESEARCH"):
            assert name in doors, f"door missing from the hall: {name}"
        reserve = str(app.screen.query_one("#hall-reserve-body", Static).render())
        assert reserve.strip(), "acquisitions plaque empty"
        # a number key leaves the hall; 0 always returns
        await pilot.press("4")
        await asyncio.sleep(1.1)
        await pilot.pause()
        assert isinstance(app.screen, MarketScreen), f"screen: {app.screen}"
        await pilot.press("0")
        await asyncio.sleep(1.1)
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen), f"0 did not return home: {app.screen}"
    print("PASS: the vault is a page — boot hall · plaques live · keys out · 0 home")


async def test_map_power_on() -> None:
    """REQ-RES-1: entering research powers the map on — once — and it
    settles to truth; leaving re-arms the performance."""
    from knivves.tui.pages.research import ResearchScreen, UnknownsMap

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        await pilot.press("5")
        await asyncio.sleep(0.3)  # mid-reveal
        await pilot.pause()
        assert isinstance(app.screen, ResearchScreen), f"screen: {app.screen}"
        unknowns = app.screen.query_one(UnknownsMap)
        assert unknowns.revealing, "the power-on did not begin"
        await asyncio.sleep(1.2)
        await pilot.pause()
        assert not unknowns.revealing, "the reveal did not settle"
        truth = unknowns.complete
        assert truth > 0, "the settled map shows nothing known"
        await asyncio.sleep(5.0)  # the demo transit finishes; the desk stills
        await pilot.pause()
        # leaving re-arms; returning powers on again — and never lies
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("5")
        await asyncio.sleep(0.3)
        await pilot.pause()
        assert unknowns.revealing, "re-entry did not power on again"
        await asyncio.sleep(1.2)
        await pilot.pause()
        assert not unknowns.revealing
        assert unknowns.complete == truth, "the reveal changed the truth"
    print("PASS: the map powers on — once per entrance · settles to truth · re-arms")


async def test_idle_stands_down() -> None:
    """REQ-RES-2: the ambient scan breathes only on a still desk — never
    during the reveal, never while a pass works a record."""
    from knivves.tui import laws
    from knivves.tui.pages.research import UnknownsMap

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        await pilot.press("5")
        await asyncio.sleep(6.5)  # reveal + demo transit settle
        await pilot.pause()
        unknowns = app.screen.query_one(UnknownsMap)
        assert unknowns.scan == -1.0, "scan moving before its cadence"
        unknowns.mark_working("some-record")
        unknowns._breathe()
        assert unknowns.scan == -1.0, "idle breathed during a pass"
        unknowns.mark_working(None)
        unknowns.begin_reveal()
        unknowns._breathe()
        assert unknowns.scan == -1.0, "idle breathed during the reveal"
        unknowns.end_reveal()
        unknowns._breathe()
        assert unknowns.scan >= 0.0, "idle did not breathe on a still desk"
        await asyncio.sleep(laws.IDLE_STEP + 0.4)
        await pilot.pause()
        assert unknowns.scan == -1.0, "the breath did not come to rest"
    print("PASS: idle — breathes on stillness, stands down for reveal and pass")


async def test_card_lights_column() -> None:
    """REQ-RES-3: the desk is one instrument — a card under the hand
    lights its column on the map, and the map answers with the card."""
    from knivves.tui.pages.research import DocketCard, UnknownsMap

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        await pilot.press("5")
        await asyncio.sleep(6.5)  # reveal + demo transit settle
        await pilot.pause()
        cards = list(app.screen.query(DocketCard))
        assert cards, "no cards in the file"
        first = cards[0]
        await pilot.hover(f"#card-{first.knife_id}")
        await pilot.pause()
        unknowns = app.screen.query_one(UnknownsMap)
        assert unknowns._spotlight == first.knife_id, "card hover did not light the column"
        # the map answers back: hover the column, the card lifts
        col = unknowns._index[first.knife_id]
        await pilot.hover(UnknownsMap, offset=(unknowns.LABEL_W + col, 4))
        await pilot.pause()
        assert first.has_class("spotlit"), "map hover did not light the card"
        await pilot.hover("#stamped")  # leave — the spotlight dies
        await pilot.pause()
        assert unknowns._spotlight is None, "spotlight survived the hand leaving"
    print("PASS: one instrument — card lights column · column answers card · dies on leave")


async def test_teletype_paces_and_truncates() -> None:
    """REQ-TRM-1: the teletype prints on the house cadence with the
    cursor riding the head; an interrupted print keeps exactly what
    landed, cursor off; a completed print ends clean."""
    from rich.text import Text as RichText

    from knivves.tui import laws
    from knivves.tui.surfaces import Teletype

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        teletype = Teletype()
        await app.screen.mount(teletype)
        lines = [RichText(f"fact {i}") for i in range(5)]

        # pacing: after two beats, the print is underway but not done
        task = asyncio.ensure_future(teletype.type_lines(lines))
        await asyncio.sleep(laws.TELETYPE_CADENCE * 2 + 0.03)
        await pilot.pause()
        mid = str(teletype.render())
        assert teletype.printing, "print already over — no pacing"
        assert "fact 0" in mid and "fact 4" not in mid, f"mid-print: {mid!r}"
        assert Teletype.CURSOR in mid, "no cursor riding the print head"

        # interrupt: what landed stays, the cursor lifts
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await pilot.pause()
        cut = str(teletype.render())
        assert not teletype.printing
        assert Teletype.CURSOR not in cut, "cursor survived the interrupt"
        assert "fact 0" in cut and "fact 4" not in cut, f"truncation lies: {cut!r}"

        # a full print completes clean
        await teletype.type_lines(lines)
        await pilot.pause()
        done = str(teletype.render())
        assert "fact 4" in done and Teletype.CURSOR not in done, f"end state: {done!r}"
    print("PASS: teletype — paced print · cursor on the head · honest truncation")


async def test_two_front_doors_agree() -> None:
    """REQ-STA-1 (one-building): the hall's plaques and the CLI welcome
    page speak the same VaultState — one reading, two doors."""
    from rich.console import Console

    from knivves.render import home_page
    from knivves.state import vault_state

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        state = vault_state(app.db, app.knives)
        plaque = str(app.screen.query_one("#hall-state-body", Static).render())
        assert str(state.blades) in plaque, f"blades missing: {plaque[:80]}"
        assert f"{state.unresearched} unresearched" in plaque, plaque[:120]
        assert f"${state.average_cad:,.0f} CAD" in plaque, plaque[:120]
        assert f"gen {state.generation}" in plaque, plaque[:120]
    import io

    console = Console(width=140, record=True, file=io.StringIO())
    console.print(home_page(state))
    cli_door = console.export_text()
    assert f"{state.blades}" in cli_door and "knives" in cli_door
    assert f"{state.unresearched} unresearched" in cli_door
    assert f"avg ${state.average_cad:,.0f} CAD" in cli_door
    print("PASS: two front doors, one reading — hall and welcome page agree")


async def test_hall_doors_answer_the_hand() -> None:
    """REQ-HAL-1 (one-building): a door row is hardware — the click is
    the key, and the hover cue lives in the page's own stylesheet."""
    from knivves.tui.pages.home import DoorRow, HomeScreen
    from knivves.tui.pages.market import MarketScreen

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        rows = list(app.screen.query(DoorRow))
        assert len(rows) == 6, f"door rows: {len(rows)}"
        await pilot.click("#door-market")
        await asyncio.sleep(1.1)
        await pilot.pause()
        assert isinstance(app.screen, MarketScreen), f"click did not open: {app.screen}"
        await pilot.press("0")
        await asyncio.sleep(1.1)
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
    css = (REPO / "knivves" / "tui" / "pages" / "home.tcss").read_text(encoding="utf-8")
    assert ".door-row:hover" in css, "no hover cue on the door rows"
    print("PASS: the doors answer the hand — click opens, hover cue declared")


async def test_imports_plate_carries() -> None:
    """REQ-IMP-1 (one-building): on the intake line a record plate
    exists only while it carries a record — the same law the research
    desk obeys."""
    from knivves.tui.pages.imports import ImportsScreen

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        await pilot.press("2")
        await asyncio.sleep(10.0)  # the demo transit runs and settles
        await pilot.pause()
        assert isinstance(app.screen, ImportsScreen), f"screen: {app.screen}"
        plate = app.screen.query_one("#forge-plate")
        assert plate.has_class("carrying") and plate.display, "the demo's record never showed"
        # the law itself: no carry, no plate — the CSS binding, not a habit
        plate.remove_class("carrying")
        await pilot.pause()
        assert not plate.display, "an empty plate still displayed — the law does not hold"
        plate.add_class("carrying")
        await pilot.pause()
        assert plate.display
    print("PASS: the intake plate carries or vanishes — the law holds in every room")


async def test_one_hero_per_page() -> None:
    """REQ-REV-1: every page implements exactly one hero reveal through
    laws.Reveal — it plays on entrance and re-arms when the page is left."""
    from knivves.tui import laws

    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    app = KnivvesApp(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        assert isinstance(app.screen._reveal, laws.Reveal), "the hall has no reveal"
        assert app.screen._reveal.played, "the hall did not perform on boot"
        for key in ("1", "2", "3", "4", "5"):
            await pilot.press(key)
            await asyncio.sleep(1.4)
            await pilot.pause()
            reveal = getattr(app.screen, "_reveal", None)
            assert isinstance(reveal, laws.Reveal), f"page {key} has no reveal"
            assert reveal.played, f"page {key} did not perform on entrance"
        # leaving a page re-arms its performance
        research = app.screen
        await pilot.press("0")
        await pilot.pause()
        assert not research._reveal.played, "suspend did not re-arm the reveal"
    print("PASS: one hero per page — every door opens with its single performance")


if __name__ == "__main__":
    test_pages_map_to_doors()
    test_pages_own_stylesheets()
    test_cues_declared_in_css()
    asyncio.run(test_theme_is_the_only_palette())
    asyncio.run(test_reveal_runs_once_per_open())
    asyncio.run(test_entry_hall_doors())
    asyncio.run(test_map_power_on())
    asyncio.run(test_idle_stands_down())
    asyncio.run(test_card_lights_column())
    asyncio.run(test_teletype_paces_and_truncates())
    asyncio.run(test_two_front_doors_agree())
    asyncio.run(test_hall_doors_answer_the_hand())
    asyncio.run(test_imports_plate_carries())
    asyncio.run(test_one_hero_per_page())
    asyncio.run(test_shell())
    asyncio.run(test_freshness_and_reserve())
    asyncio.run(test_file_import_transit())
    asyncio.run(test_desk_demo_transit())
