from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

APP_DIR = Path(os.environ.get("KNIVVES_HOME", str(Path.home() / ".knivves"))).expanduser()
USER_DB = Path(os.environ.get("KNIVVES_DB", str(APP_DIR / "knives.json"))).expanduser()
BACKUP_DIR = APP_DIR / "backups"


class DatabaseError(RuntimeError):
    """Raised when the JSON database cannot be read or written safely."""


@dataclass
class ValidationIssue:
    severity: str
    id: str
    message: str
    fix: str = ""


def bundled_db_path() -> Path:
    return Path(str(files("knivves") / "data" / "knives.json"))


def ensure_user_db(path: Path | None = None) -> Path:
    db_path = path.expanduser().resolve() if path else USER_DB.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        shutil.copyfile(bundled_db_path(), db_path)
    return db_path


def load_database(path: Path | None = None) -> dict[str, Any]:
    db_path = ensure_user_db(path)
    try:
        with db_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise DatabaseError(f"Invalid JSON in {db_path}: line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    except OSError as exc:
        raise DatabaseError(f"Could not read database {db_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DatabaseError(f"Database root must be a JSON object: {db_path}")
    data.setdefault("knives", [])
    if not isinstance(data["knives"], list):
        raise DatabaseError("Database field `knives` must be a JSON array.")
    return data


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_database(label: str | None = "manual", path: Path | None = None) -> Path:
    db_path = ensure_user_db(path)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in (label or "manual")).strip("-") or "backup"
    backup_path = BACKUP_DIR / f"knives-{timestamp()}-{safe_label}.json"
    shutil.copyfile(db_path, backup_path)
    return backup_path


def list_backups() -> list[Path]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(BACKUP_DIR.glob("knives-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def save_database(
    db: dict[str, Any],
    path: Path | None = None,
    *,
    make_backup: bool = False,
    backup_label: str = "autosave",
) -> Path:
    db_path = ensure_user_db(path)
    if make_backup and db_path.exists():
        backup_database(backup_label, db_path)
    tmp_path = db_path.with_suffix(db_path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
            f.write("\n")
        tmp_path.replace(db_path)
    except OSError as exc:
        raise DatabaseError(f"Could not write database {db_path}: {exc}") from exc
    return db_path


def reset_user_db(path: Path | None = None) -> Path:
    db_path = ensure_user_db(path)
    if db_path.exists():
        backup_database("pre-reset", db_path)
    shutil.copyfile(bundled_db_path(), db_path)
    return db_path


def knives_list(db: dict[str, Any]) -> list[dict[str, Any]]:
    knives = db.setdefault("knives", [])
    if not isinstance(knives, list):
        raise DatabaseError("Database field `knives` must be a JSON array.")
    return knives


def make_knife_id(brand: str, model: str) -> str:
    from .models import slugify

    return slugify(f"{brand} {model}")


def _unique_id(existing: set[str], base: str) -> str:
    candidate = base
    counter = 2
    while candidate in existing:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def add_knife(db: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    knives = knives_list(db)
    existing = {str(k.get("id")) for k in knives if isinstance(k, dict) and k.get("id")}
    base = str(record.get("id") or make_knife_id(str(record.get("brand") or "knife"), str(record.get("model") or "unknown")))
    record["id"] = _unique_id(existing, base)
    knives.append(record)
    return record


def find_knife_index(db: dict[str, Any], identifier: str) -> int | None:
    key = identifier.lower().strip()
    for idx, raw in enumerate(knives_list(db)):
        if not isinstance(raw, dict):
            continue
        if str(raw.get("id") or "").lower() == key:
            return idx
    return None


def merge_database(db: dict[str, Any], incoming: dict[str, Any], *, replace_existing: bool = False) -> tuple[int, int]:
    current = knives_list(db)
    incoming_knives = incoming.get("knives") or []
    if not isinstance(incoming_knives, list):
        raise DatabaseError("Imported database field `knives` must be a list.")
    id_to_index = {str(k.get("id")): i for i, k in enumerate(current) if isinstance(k, dict) and k.get("id")}
    existing = set(id_to_index)
    added = 0
    updated = 0
    for raw in incoming_knives:
        if not isinstance(raw, dict):
            continue
        record = dict(raw)
        rid = str(record.get("id") or make_knife_id(str(record.get("brand") or "knife"), str(record.get("model") or "unknown")))
        record["id"] = rid
        if rid in id_to_index:
            if replace_existing:
                current[id_to_index[rid]] = record
                updated += 1
            continue
        record["id"] = _unique_id(existing, rid)
        existing.add(record["id"])
        current.append(record)
        added += 1
    return added, updated


def validate_database(db: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(db, dict):
        return [ValidationIssue("error", "database", "Database root is not an object.", "Use a knivves JSON object.")]
    knives = db.get("knives")
    if not isinstance(knives, list):
        return [ValidationIssue("error", "database", "Top-level `knives` is not a list.", "Set `knives` to an array of knife objects.")]
    seen: set[str] = set()
    for idx, raw in enumerate(knives, start=1):
        if not isinstance(raw, dict):
            issues.append(ValidationIssue("error", f"#{idx}", "Knife record is not an object.", "Replace it with an object."))
            continue
        rid = str(raw.get("id") or "").strip()
        if not rid:
            issues.append(ValidationIssue("error", f"#{idx}", "Missing knife ID.", "Add a stable kebab-case `id`."))
        elif rid in seen:
            issues.append(ValidationIssue("error", rid, "Duplicate knife ID.", "Rename one duplicate ID."))
        seen.add(rid)
        if not raw.get("brand"):
            issues.append(ValidationIssue("warning", rid or f"#{idx}", "Missing brand.", "Add `brand`."))
        if not raw.get("model"):
            issues.append(ValidationIssue("warning", rid or f"#{idx}", "Missing model.", "Add `model`."))
        cls = raw.get("user_classification")
        if cls not in {None, "approved", "rejected"}:
            issues.append(ValidationIssue("warning", rid or f"#{idx}", f"Unexpected classification: {cls}", "Use approved, rejected, or null."))
        retailers = raw.get("canadian_online_retailers") or []
        if raw.get("research_status") == "canadian_retailer_verified" and not retailers:
            issues.append(ValidationIssue("warning", rid or f"#{idx}", "Marked canadian_retailer_verified but no retailer is saved.", "Add a retailer or set research_status back to pending_canadian_retailer_search."))
        if not isinstance(retailers, list):
            issues.append(ValidationIssue("error", rid or f"#{idx}", "Retailers field is not a list.", "Use an array for `canadian_online_retailers`."))
        else:
            for r_idx, retailer in enumerate(retailers, start=1):
                if not isinstance(retailer, dict):
                    issues.append(ValidationIssue("error", rid or f"#{idx}", f"Retailer #{r_idx} is not an object.", "Use a retailer object."))
                    continue
                if not retailer.get("retailer"):
                    issues.append(ValidationIssue("warning", rid or f"#{idx}", f"Retailer #{r_idx} has no name.", "Add `retailer`."))
                if not retailer.get("url"):
                    issues.append(ValidationIssue("warning", rid or f"#{idx}", f"Retailer #{r_idx} has no URL.", "Add `url`."))
    return issues


def restore_backup(path: Path) -> Path:
    path = path.expanduser().resolve()
    # Validate before replacing live DB.
    load_database(path)
    db_path = ensure_user_db()
    backup_database("pre-restore", db_path)
    shutil.copyfile(path, db_path)
    return db_path
