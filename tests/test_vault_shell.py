"""Headless tests for the Vault shell.

Plain-python runner (no pytest dependency):  python tests/test_vault_shell.py
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
from knivves.vault.app import KnivvesVault  # noqa: E402
from knivves.vault.bench import BenchScreen  # noqa: E402
from knivves.vault.plate import Plate  # noqa: E402
from knivves.vault.rack import RackScreen  # noqa: E402
from knivves.vault.forge import ForgeScreen  # noqa: E402


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
    app = KnivvesVault(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await pilot.pause()

        # cold boot: the vault door holds the brand, then opens into the rack
        from knivves.vault.door import VaultDoor

        assert app.screen.query(VaultDoor), "boot door missing"
        await asyncio.sleep(2.3)
        await pilot.pause()
        assert not app.screen.query(VaultDoor), "boot door failed to open"

        # boots into the rack with the full collection
        assert isinstance(app.screen, RackScreen), f"boot screen: {app.screen}"
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
        from knivves.vault.masthead import Masthead
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
        # palette exposes the building's rooms and operations
        commands = {c.title for c in app.get_system_commands(app.screen)}
        for expected in ("The Rack", "The Forge Line", "The Bench", "The Ledger", "Survey the market"):
            assert expected in commands, f"palette missing: {expected}"

        # ---- tip system: rail on hover, capsule on demand ----
        from knivves.vault.tips import TipCapsule, TipRail

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
        await pilot.press("2")
        await pilot.pause()
        assert app.screen.query(VaultDoor), "room door missing on arrival"
        await asyncio.sleep(1.1)
        await pilot.pause()
        forge_rail = app.screen.query_one(TipRail)
        await pilot.hover("#st-extract", offset=(4, 2))
        await pilot.pause()
        assert forge_rail.current and "stamped here" in forge_rail.current.short
        assert not forge_rail.has_class("expandable"), "❯ shown without extended content"
        await pilot.press("1")
        await pilot.pause()

        # room switch: 2 -> forge line, transit completes on real rules
        await pilot.press("2")
        await pilot.pause()
        assert isinstance(app.screen, ForgeScreen), f"screen: {app.screen}"
        await asyncio.sleep(8.5)
        await pilot.pause()
        gates_text = str(app.screen.query_one("#gates", Static).render())
        filed_text = str(app.screen.query_one("#filed", Static).render())
        assert "CLEAR TO PROCEED" in gates_text, f"gates: {gates_text[:80]}"
        assert "demo transit" in filed_text, f"filed: {filed_text[:80]}"
        # pass B: gates read as stamped labels with a counter; line state on masthead
        assert "AUTOMATIC / SWITCHBLADE" in gates_text, f"gates: {gates_text[:120]}"
        assert "GATES 7/7" in gates_text, f"gate counter missing: {gates_text[:60]}"
        from knivves.vault.masthead import Masthead as MastheadWidget
        forge_context = app.screen.query_one(MastheadWidget).context
        assert "line idle" in forge_context, f"context: {forge_context}"
        # the traveling plate never clips off screen, whatever its height
        from knivves.vault.plate import Plate as PlateWidget
        forge_plate = app.screen.query_one(PlateWidget)
        plate_bottom = forge_plate.region.y + forge_plate.region.height
        assert plate_bottom <= app.size.height, f"plate clips: bottom {plate_bottom} vs screen {app.size.height}"

        # room switch back: 1 -> the rack, state intact
        await pilot.press("1")
        await pilot.pause()
        assert isinstance(app.screen, RackScreen)

        # send-to-bench: `b` carries the highlighted knife's plate to the bench
        await pilot.press("b")
        await pilot.pause()
        assert isinstance(app.screen, BenchScreen), f"screen: {app.screen}"
        assert len(app.screen.slots) == 1, f"slots: {len(app.screen.slots)}"
        first_id = app.screen.slots[0].id

        # second knife -> choreographed arrival, then the calipers measure
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("down", "down", "b")
        await pilot.pause()
        assert len(app.screen.slots) == 2, f"slots: {len(app.screen.slots)}"
        assert app.screen.slots[0].id == first_id
        await asyncio.sleep(2.4)  # arrival travel + staged caliper readings
        await pilot.pause()
        calipers = str(app.screen.query_one("#calipers-read", Static).render())
        assert "Δ" in calipers or "incomparable" in calipers, f"calipers: {calipers[:80]}"
        assert app.screen._seated == [k.id for k in app.screen.slots], "seating not tracked"
        from knivves.vault.masthead import Masthead as MH
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
            await asyncio.sleep(7.5)
            await pilot.pause()
            filed_text = str(app.screen.query_one("#filed", Static).render())
            assert "Testbrand" in filed_text and "filed" in filed_text, f"filed: {filed_text[:100]}"
            on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
            ids = {k["id"] for k in on_disk["knives"]}
            assert "testbrand-testblade-tb123" in ids, "record not written to database"
            filed_rec = next(k for k in on_disk["knives"] if k["id"] == "testbrand-testblade-tb123")
            assert filed_rec["user_tags"] == ["affordable"], "under-$150 auto tag missing"
            assert len(app.knives) == n + 1

            # rack reflects the filing on return
            await pilot.press("1")
            await pilot.pause()
            assert app.screen.query_one(DataTable).row_count == n + 1

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
            assert "already in the vault" in log_text, f"log: {log_text[:80]}"

            # prohibited listing: gate slams, nothing filed
            scrape_mod.fetch_listing = _prohibited_listing
            intake.focus()
            intake.value = "https://www.bladescanada.com/Badbrand-Knives/balisong-trainer"
            await pilot.press("enter")
            await asyncio.sleep(6.0)
            await pilot.pause()
            gates_now = str(app.screen.query_one("#gates", Static).render())
            filed_now = str(app.screen.query_one("#filed", Static).render())
            assert "✗" in gates_now, f"gates: {gates_now[:100]}"
            assert "not filed" in filed_now, f"filed: {filed_now[:100]}"
            on_disk = json.loads(tmp_db.read_text(encoding="utf-8"))
            assert len(on_disk["knives"]) == n + 1, "prohibited record was written"
            # ---- the ledger: survey with a stubbed market ----
            from knivves.vault.ledger import LedgerScreen

            LedgerScreen.SURVEY_DELAY = 0
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
            assert isinstance(app.screen, LedgerScreen), f"screen: {app.screen}"
            valuation = str(app.screen.query_one("#valuation-read", Static).render())
            assert "value" in valuation.lower(), f"valuation: {valuation[:80]}"
            from knivves.vault.gauges import GradientBars, PriceScale
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

    from knivves.vault.reserve import Reserve

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

    app = KnivvesVault(db_path=tmp_db)
    async with app.run_test(size=(170, 45)) as pilot:
        await asyncio.sleep(2.3)
        await pilot.pause()
        assert isinstance(app.screen, RackScreen)

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
        from knivves.vault.masthead import Masthead

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


if __name__ == "__main__":
    asyncio.run(test_shell())
    asyncio.run(test_freshness_and_reserve())
