"""Headless tests for the Vault shell.

Plain-python runner (no pytest dependency):  python tests/test_vault_shell.py
Uses Textual's Pilot to drive real input against the composed app.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from textual.widgets import DataTable, Input, Static  # noqa: E402

from knivves.vault.app import KnivvesVault  # noqa: E402
from knivves.vault.plate import Plate  # noqa: E402
from knivves.vault.rack import RackScreen  # noqa: E402
from knivves.vault.forge import ForgeScreen  # noqa: E402


async def test_shell() -> None:
    app = KnivvesVault(db_path=REPO / "knivves" / "data" / "knives.json")
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
        assert "filed" in filed_text, f"filed: {filed_text[:80]}"

        # room switch back: 1 -> the rack, state intact
        await pilot.press("1")
        await pilot.pause()
        assert isinstance(app.screen, RackScreen)

        print(f"PASS: shell boots · rack {n} rows · sort+reverse · search · plate travel · forge transit · room switching")


if __name__ == "__main__":
    asyncio.run(test_shell())
