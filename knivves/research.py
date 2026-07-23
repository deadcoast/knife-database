"""The Research Desk backend — the vault researches its own unknowns.

Case: docs/dev-spec/2026-07-23-research-desk (REQ-RES-1..3).

Three pure stages, no UI imports, no network of its own:

- ``audit_record`` / ``audit_database`` name every gap in a record —
  placeholder titles, Unknown mechanism fields, missing prices — as
  first-class facts (REQ-RES-1).
- ``build_docket`` orders the auditable records deterministically:
  BuyList rank first, then ★new, then most-gaps-first. Records with no
  supported listing URL land on the *unreachable* shelf with a stated
  reason — honest gaps, never silent skips (REQ-RES-2).
- ``research_record`` merges a fetched Listing under one law: only
  empty fields are written, user data is never overwritten. Every fill
  is stamped with provenance; a filled first price seeds history and
  re-tags the affordable rule; rulebook hits are reported, never
  written — the flag stays the user's decision (REQ-RES-3).

``run_research`` orchestrates the pass with an injectable ``fetch`` so
every test runs offline.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from . import scrape
from .ledger import retag_affordable, seed_history
from .models import NULLISH, KnifeView, knife_views

# A record whose title was never researched: ingest derives it from the
# URL slug and keeps the raw ledger line (with its TODO label) in
# ``source_input``.
TODO_SOURCE = re.compile(r"\bTODO\b", re.I)

_URL_IN_TEXT = re.compile(r"https?://[^\s)\]>]+")

# Keywords that make a rulebook line trip on listing text. Deliberately
# precise: "assisted opening" is legal and must never trip a gate.
# Backend home of the table the Forge Line's legal screen executes.
RULE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "automatic switchblade": ("switchblade", "automatic knife"),
    "OTF automatic": ("otf",),
    "gravity knife": ("gravity knife",),
    "balisong": ("balisong",),
    "butterfly knife": ("butterfly",),
    "explicit centrifugal/flick knife": ("centrifugal", "flick knife"),
    "button/spring/device in handle that automatically opens the blade": (
        "auto opening", "push button open",
    ),
}


def rulebook(db: dict[str, Any]) -> list[str]:
    """The prohibited-mechanism rulebook, read from the database itself."""
    rule = db.get("workflow_rules", {}).get("canadian_online_retailer_rule", {})
    return list(rule.get("only_reject_or_fail_if_clear_prohibited_mechanism", []))


def screen_text(text: str, rules: list[str], keywords: dict[str, tuple[str, ...]] | None = None) -> list[tuple[str, list[str]]]:
    """Run rulebook lines over text; returns (rule, matched keywords) hits."""
    table = keywords or RULE_KEYWORDS
    low = text.lower()
    hits: list[tuple[str, list[str]]] = []
    for rule in rules:
        matched = [kw for kw in table.get(rule, (rule.lower(),)) if kw in low]
        if matched:
            hits.append((rule, matched))
    return hits


def host_of(url: str) -> str:
    """The supported host a URL belongs to, or its bare netloc."""
    for host in scrape.SUPPORTED_HOSTS:
        if host in url:
            return host
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1) if match else url


def _nullish(value: Any) -> bool:
    return value is None or str(value).strip().lower() in NULLISH


def source_url(record: dict[str, Any]) -> str | None:
    """The listing URL a record could be researched from: the primary
    retailer entry first, else a URL inside the raw source line."""
    for retailer in record.get("canadian_online_retailers") or []:
        if isinstance(retailer, dict) and retailer.get("url"):
            return str(retailer["url"])
    match = _URL_IN_TEXT.search(str(record.get("source_input") or ""))
    return match.group(0) if match else None


# ------------------------------------------------------- REQ-RES-1 audit

@dataclass(frozen=True)
class Gap:
    """One thing a record does not know, and where it could learn it."""

    field: str
    where: str
    source_url: str | None
    supported: bool


# (field key, dotted record path) in stamping order; mechanism fields
# audit via _nullish, the rest carry their own rules below.
_MECH_FIELDS = (
    ("steel", "blade_steel"),
    ("lock", "lock_type"),
    ("opening", "opening_method"),
    ("length", "blade_length"),
)


def audit_record(record: dict[str, Any]) -> list[Gap]:
    """Every gap in one record, as data. Pure — no network, no writes."""
    url = source_url(record)
    supported = bool(url and scrape.is_supported(url))

    def gap(field: str, where: str) -> Gap:
        return Gap(field=field, where=where, source_url=url, supported=supported)

    gaps: list[Gap] = []
    if TODO_SOURCE.search(str(record.get("source_input") or "")):
        gaps.append(gap("title", "model"))
    else:
        if _nullish(record.get("brand")):
            gaps.append(gap("brand", "brand"))
        if _nullish(record.get("model")):
            gaps.append(gap("model", "model"))
    mechanism = record.get("mechanism") or {}
    for field, key in _MECH_FIELDS:
        if _nullish(mechanism.get(key)):
            gaps.append(gap(field, f"mechanism.{key}"))
    retailers = [r for r in record.get("canadian_online_retailers") or [] if isinstance(r, dict)]
    if not any(isinstance(r.get("listed_price_cad"), (int, float)) for r in retailers):
        gaps.append(gap("price", "canadian_online_retailers[0].listed_price_cad"))
    if retailers and _nullish(retailers[0].get("availability")):
        gaps.append(gap("availability", "canadian_online_retailers[0].availability"))
    if _nullish(record.get("listing_title")):
        gaps.append(gap("listing_title", "listing_title"))
    return gaps


@dataclass
class Audit:
    """The vault-wide completeness picture."""

    records: int
    complete: int
    gaps_by_id: dict[str, list[Gap]]

    @property
    def with_gaps(self) -> int:
        return len(self.gaps_by_id)

    @property
    def gap_total(self) -> int:
        return sum(len(gaps) for gaps in self.gaps_by_id.values())


def audit_database(db: dict[str, Any]) -> Audit:
    gaps_by_id: dict[str, list[Gap]] = {}
    records = 0
    for record in db.get("knives") or []:
        if not isinstance(record, dict):
            continue
        records += 1
        gaps = audit_record(record)
        if gaps:
            gaps_by_id[str(record.get("id") or f"#{records}")] = gaps
    return Audit(records=records, complete=records - len(gaps_by_id), gaps_by_id=gaps_by_id)


# ------------------------------------------------------ REQ-RES-2 docket

@dataclass(frozen=True)
class DocketEntry:
    knife_id: str
    url: str | None
    gaps: tuple[Gap, ...]
    buy_priority: int | None
    is_new: bool
    reason: str = ""


@dataclass
class Docket:
    entries: list[DocketEntry]
    unreachable: list[DocketEntry]


def build_docket(knives: list[KnifeView]) -> Docket:
    """What to research, in the order it deserves: BuyList rank first,
    then ★new, then most-gaps-first. No supported source → the
    unreachable shelf, with the reason said."""
    entries: list[DocketEntry] = []
    unreachable: list[DocketEntry] = []
    for knife in knives:
        gaps = audit_record(knife.raw)
        if not gaps:
            continue
        url = source_url(knife.raw)
        entry = DocketEntry(
            knife_id=knife.id,
            url=url,
            gaps=tuple(gaps),
            buy_priority=knife.buy_priority,
            is_new=knife.is_new,
        )
        if url and scrape.is_supported(url):
            entries.append(entry)
        else:
            reason = "no listing url" if not url else f"unsupported host — {host_of(url)}"
            unreachable.append(DocketEntry(**{**entry.__dict__, "reason": reason}))
    entries.sort(
        key=lambda e: (
            e.buy_priority if e.buy_priority is not None else float("inf"),
            not e.is_new,
            -len(e.gaps),
            e.knife_id,
        )
    )
    return Docket(entries=entries, unreachable=unreachable)


# ------------------------------------------------- REQ-RES-3 completion

@dataclass
class ResearchReport:
    """What one pass over one record actually did — every fill named."""

    knife_id: str
    filled: list[tuple[str, str]]
    rulebook_hits: list[tuple[str, list[str]]]


def research_record(
    record: dict[str, Any],
    listing: scrape.Listing,
    *,
    rules: list[str] | None = None,
    on_date: str | None = None,
) -> ResearchReport:
    """Merge a fetched listing under the law: fill only what is empty.

    User-entered data is never overwritten. Fills are stamped with
    provenance under the additive ``research`` sub-dict. A filled first
    price seeds history and re-tags the affordable rule. Rulebook hits
    are reported in the return value only — the record's
    ``clear_prohibited_mechanism_found`` flag is never written here.
    """
    on_date = on_date or date.today().isoformat()
    host = host_of(listing.url)
    gaps = {gap.field for gap in audit_record(record)}
    filled: list[tuple[str, str]] = []

    if "title" in gaps and (listing.brand or listing.model):
        # a slug-derived placeholder earns its researched name; the id
        # is stable and is never re-derived from it
        if listing.brand:
            record["brand"] = listing.brand
        if listing.model:
            record["model"] = listing.model
        filled.append(("title", host))
    else:
        if "brand" in gaps and listing.brand:
            record["brand"] = listing.brand
            filled.append(("brand", host))
        if "model" in gaps and listing.model:
            record["model"] = listing.model
            filled.append(("model", host))
    if "listing_title" in gaps and listing.listing_title:
        record["listing_title"] = listing.listing_title
        filled.append(("listing_title", host))

    mechanism = record.setdefault("mechanism", {})
    for field, value in (
        ("steel", listing.blade_steel),
        ("lock", listing.lock_type),
        ("opening", listing.opening_method),
        ("length", listing.blade_length),
    ):
        if field in gaps and value:
            mechanism[dict(_MECH_FIELDS)[field]] = value
            filled.append((field, host))

    retailers = record.setdefault("canadian_online_retailers", [])
    if not retailers and scrape.is_supported(listing.url):
        # the record had no market presence at all — the researched
        # listing becomes its primary entry (an empty list is a gap)
        retailers.append({
            "retailer": listing.retailer,
            "url": listing.url,
            "listed_price_cad": None,
            "availability": "unknown",
            "source_date": on_date,
        })
    if retailers and isinstance(retailers[0], dict):
        entry = retailers[0]
        if "price" in gaps and listing.price_cad is not None:
            entry["listed_price_cad"] = float(listing.price_cad)
            entry["source_date"] = on_date
            seed_history(record)
            retag_affordable(record)
            filled.append(("price", host))
        if "availability" in gaps and listing.availability:
            entry["availability"] = listing.availability
            filled.append(("availability", host))

    if filled:
        provenance = record.setdefault("research", {})
        provenance["last_pass"] = on_date
        provenance.setdefault("filled", {}).update({field: source for field, source in filled})

    screened = " ".join(
        part for part in (listing.listing_title, listing.lock_type, listing.opening_method) if part
    )
    hits = screen_text(screened, list(rules or []))
    return ResearchReport(knife_id=str(record.get("id") or ""), filled=filled, rulebook_hits=hits)


# --------------------------------------------------------- the full pass

@dataclass
class PassSummary:
    """One research pass, accounted for completely: what was planned,
    what filled, what failed, and what was never reachable."""

    planned: list[DocketEntry]
    unreachable: list[DocketEntry]
    reports: list[ResearchReport]
    failed: list[tuple[str, str]]
    dry_run: bool

    @property
    def field_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for report in self.reports:
            for field, _ in report.filled:
                counts[field] = counts.get(field, 0) + 1
        return counts

    @property
    def rulebook_hits(self) -> list[tuple[str, str]]:
        return [(r.knife_id, rule) for r in self.reports for rule, _ in r.rulebook_hits]


def run_research(
    db: dict[str, Any],
    *,
    fetch: Callable[[str], scrape.Listing] = scrape.fetch_listing,
    only_id: str | None = None,
    dry_run: bool = False,
    on_date: str | None = None,
    workers: int = 6,
    progress: Callable[[str], None] | None = None,
) -> PassSummary:
    """Work the docket. Fetches run concurrently; fills apply in docket
    order so the pass is deterministic. The caller persists the database
    — this function only researches it."""
    knives = knife_views(db)
    if only_id is not None:
        knives = [k for k in knives if k.id == only_id]
    docket = build_docket(knives)
    if dry_run or not docket.entries:
        return PassSummary(
            planned=docket.entries, unreachable=docket.unreachable,
            reports=[], failed=[], dry_run=dry_run,
        )

    def pull(entry: DocketEntry) -> tuple[str, scrape.Listing | Exception]:
        try:
            return entry.knife_id, fetch(str(entry.url))
        except scrape.ScrapeError as exc:
            return entry.knife_id, exc

    listings: dict[str, scrape.Listing | Exception] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(docket.entries)))) as pool:
        for knife_id, result in pool.map(pull, docket.entries):
            listings[knife_id] = result
            if progress is not None:
                progress(knife_id)

    by_id = {str(r.get("id")): r for r in db.get("knives") or [] if isinstance(r, dict)}
    rules = rulebook(db)
    reports: list[ResearchReport] = []
    failed: list[tuple[str, str]] = []
    for entry in docket.entries:
        result = listings[entry.knife_id]
        if isinstance(result, Exception):
            failed.append((entry.knife_id, str(result)))
            continue
        reports.append(
            research_record(by_id[entry.knife_id], result, rules=rules, on_date=on_date)
        )
    return PassSummary(
        planned=docket.entries, unreachable=docket.unreachable,
        reports=reports, failed=failed, dry_run=False,
    )
