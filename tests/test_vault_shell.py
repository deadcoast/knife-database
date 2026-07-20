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

        # row click: the plate travels in, carrying the record
        await pilot.click(DataTable, offset=(4, 1))
        await pilot.pause()
        plate = app.screen.query_one(Plate)
        assert plate.has_class("open"), "plate did not open"

        # escape sends the plate away and clears search
        await pilot.press("escape")
        await asyncio.sleep(0.6)
        await pilot.pause()
        assert not plate.has_class("open")
        assert app.screen.query_one("#rack-search", Input).value == ""

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

        # second knife -> calipers read deltas; duplicate is refused
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("down", "down", "b")
        await pilot.pause()
        assert len(app.screen.slots) == 2, f"slots: {len(app.screen.slots)}"
        assert app.screen.slots[0].id == first_id
        calipers = str(app.screen.query_one("#calipers-read", Static).render())
        assert "Δ" in calipers or "incomparable" in calipers, f"calipers: {calipers[:80]}"
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("b")  # same highlighted row as slot 2 -> dedupe
        await pilot.pause()
        assert len(app.screen.slots) == 2, "duplicate was not refused"

        # escape clears the bench
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen.slots) == 0

        # ---- live intake (stubbed fetcher, real filing) ----
        real_fetch = scrape_mod.fetch_listing
        try:
            scrape_mod.fetch_listing = _clean_listing
            await pilot.press("2")
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
            assert "value" in valuation.lower() and "█" in valuation, f"valuation: {valuation[:80]}"
            await pilot.press("s")
            await asyncio.sleep(6.0)
            await pilot.pause()
            movers_text = str(app.screen.query_one("#movers-read", Static).render())
            assert "survey complete" in movers_text, f"movers: {movers_text[:100]}"
            assert "▼" in movers_text, "no downward movers shown"
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


if __name__ == "__main__":
    asyncio.run(test_shell())
