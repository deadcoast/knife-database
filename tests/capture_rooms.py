"""The frame-capture pipeline — every room exhibit, reproducibly.

Drives the Vault headlessly (Textual Pilot) to each room's demonstrative
state and exports the frame with ``App.export_screenshot`` to
``docs/media/room-<name>.svg``. These are the README's exhibits and the
eyes-on verification frames: after any visual change, re-run this and
LOOK at the output — green tests are not visual verification.

Run all rooms:        python tests/capture_rooms.py
Run some:             python tests/capture_rooms.py desk ledger
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

from knivves.vault.app import KnivvesVault  # noqa: E402

MEDIA = REPO / "docs" / "media"
SIZE = (170, 45)
BOOT_DOOR = 2.4


def _fresh_app() -> KnivvesVault:
    tmp_db = Path(tempfile.mkdtemp()) / "knives.json"
    shutil.copyfile(REPO / "knivves" / "data" / "knives.json", tmp_db)
    return KnivvesVault(db_path=tmp_db)


def _save(app: KnivvesVault, name: str) -> None:
    out = MEDIA / f"room-{name}.svg"
    out.write_text(app.export_screenshot(title=f"KNIVVES VAULT — {name}"), encoding="utf-8")
    print(f"captured  {out.relative_to(REPO)}")


async def capture_rack() -> None:
    """Library: the collection with a record's plate traveled in."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        from textual.widgets import DataTable

        await pilot.click(DataTable, offset=(4, 1))
        await asyncio.sleep(0.9)
        await pilot.pause()
        _save(app, "rack")


async def capture_forge() -> None:
    """Import Knives: the demo transit landed at the vault station."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("2")
        await asyncio.sleep(1.0)
        await pilot.pause()
        await asyncio.sleep(9.0)  # demo transit completes and settles
        await pilot.pause()
        _save(app, "forge")


async def capture_bench() -> None:
    """Compare Models: two plates seated, the calipers' measurement held."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("b")
        await asyncio.sleep(1.0)
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("down", "down", "b")
        await asyncio.sleep(3.0)  # arrival choreography + line-by-line read
        await pilot.pause()
        _save(app, "bench")


async def capture_ledger() -> None:
    """Market Prices: the drawn instruments over the real distribution."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("4")
        await asyncio.sleep(1.2)
        await pilot.pause()
        _save(app, "ledger")


async def capture_desk() -> None:
    """Research: the demo transit stamped at STAMP, docket and meter live."""
    app = _fresh_app()
    async with app.run_test(size=SIZE) as pilot:
        await asyncio.sleep(BOOT_DOOR)
        await pilot.pause()
        await pilot.press("5")
        await asyncio.sleep(1.0)
        await pilot.pause()
        await asyncio.sleep(5.0)  # demo transit completes
        await pilot.pause()
        _save(app, "desk")


ROOMS = {
    "rack": capture_rack,
    "forge": capture_forge,
    "bench": capture_bench,
    "ledger": capture_ledger,
    "desk": capture_desk,
}


def main() -> None:
    wanted = [name.lower() for name in sys.argv[1:]] or list(ROOMS)
    unknown = [name for name in wanted if name not in ROOMS]
    if unknown:
        sys.exit(f"unknown room(s): {', '.join(unknown)} — pick from {', '.join(ROOMS)}")
    for name in wanted:
        asyncio.run(ROOMS[name]())
    print(f"{len(wanted)} frame(s) — now LOOK at them before claiming anything")


if __name__ == "__main__":
    main()
