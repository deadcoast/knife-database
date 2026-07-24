"""The frame-capture pipeline — every page exhibit, reproducibly.

Drives the application headlessly (Textual Pilot) to each page's
demonstrative state and exports the frame with ``App.export_screenshot``
to ``docs/media/page-<name>.svg``. These are the README's exhibits and
the eyes-on verification frames: after any visual change, re-run this
and LOOK at the output — green tests are not visual verification.

Run all pages:        python tests/capture_pages.py
Run some:             python tests/capture_pages.py research market
No network, no writes: everything runs on a throwaway database copy.
"""
from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from knivves.tui.app import KnivvesApp  # noqa: E402

MEDIA = REPO / "docs" / "media"
SIZE = (170, 45)
BOOT_DOOR = 2.4
ROOM_DOOR = 1.1


def _fresh_app() -> KnivvesApp:
    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    return KnivvesApp(db_path=tmp_db)


def _save(app: KnivvesApp, name: str) -> None:
    out = MEDIA / f"page-{name}.svg"
    out.write_text(app.export_screenshot(title=f"KNIVVES — {name}"), encoding="utf-8")
    print(f"captured  {out.relative_to(REPO)}")


async def capture_home() -> None:
    """The entry hall: brand plate, meters, door slabs, the floor map."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await asyncio.sleep(0.8)  # the hall's reveal and floor power-on settle
        await pilot.pause()
        _save(app, "home")


async def capture_library() -> None:
    """Library: the collection with a record's plate traveled in."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("1")
        await asyncio.sleep(ROOM_DOOR)
        await pilot.pause()
        from textual.widgets import DataTable

        await pilot.click(DataTable, offset=(4, 1))
        await asyncio.sleep(0.9)
        await pilot.pause()
        _save(app, "library")


async def capture_imports() -> None:
    """Import Knives: the demo transit landed at the vault station."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("2")
        await asyncio.sleep(ROOM_DOOR)
        await pilot.pause()
        await asyncio.sleep(9.0)  # demo transit completes and settles
        await pilot.pause()
        _save(app, "imports")


async def capture_compare() -> None:
    """Compare Models: two plates seated, the calipers' measurement held."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("1")
        await asyncio.sleep(ROOM_DOOR)
        await pilot.pause()
        await pilot.press("b")
        await asyncio.sleep(1.0)
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("down", "down", "b")
        await asyncio.sleep(4.0)  # arrival choreography + jaws closing per beam
        await pilot.pause()
        _save(app, "compare")


async def capture_market() -> None:
    """Market Prices: the drawn instruments over the real distribution."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("4")
        await asyncio.sleep(2.0)  # the scale's reveal settles at ~1.1s — never export mid-draw
        await pilot.pause()
        _save(app, "market")


async def capture_research() -> None:
    """Research: the demo transit stamped at STAMP, docket and meter live."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("5")
        await asyncio.sleep(ROOM_DOOR)
        await pilot.pause()
        await asyncio.sleep(6.5)  # power-on reveal, then the demo transit
        await pilot.pause()
        _save(app, "research")


PAGES = {
    "home": capture_home,
    "library": capture_library,
    "imports": capture_imports,
    "compare": capture_compare,
    "market": capture_market,
    "research": capture_research,
}


def main() -> None:
    wanted = [name.lower() for name in sys.argv[1:]] or list(PAGES)
    unknown = [name for name in wanted if name not in PAGES]
    if unknown:
        sys.exit(f"unknown page(s): {', '.join(unknown)} — pick from {', '.join(PAGES)}")
    for name in wanted:
        asyncio.run(PAGES[name]())
    print(f"{len(wanted)} frame(s) — now LOOK at them before claiming anything")


if __name__ == "__main__":
    main()
