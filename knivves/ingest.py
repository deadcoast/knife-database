"""The intake dock — markdown ingestion for `knivves add <file.md>`.

The ingestion file format is a deliberate, dense link ledger:

* **SLI** (Section Line Indicator) — a line of exactly 31 ``-`` characters.
  SLIs fence headings and group related data so long lists stay ingestible.
* **SectionID** — a ``// Name`` heading fenced by SLIs (SLI directly above,
  a blank line after, an SLI closing the heading). ``*Tag*`` markers on the
  line attach tags to every entry in the section.
* **Inline annotation** — a ``// Name *Tag*`` line *inside* a section body:
  names a source and tags the entries that follow it.
* **Entries** — ``- [label](url)`` list items.

The machine here is tolerant by design. Real ledger files arrive with
swapped labels, URLs split across lines, angle-bracket link forms, stray
parentheses, tracking queries, and TODO placeholders — every case observed
in production notes is repaired, and every repair and grammar violation is
recorded as data (``Entry.repairs`` / ``Document.diagnostics``), never
raised. Three pure stages keep it testable and dry-runnable::

    parse_document(text)  -> Document      # lex + parse + repair
    build_plan(doc, db)   -> IngestPlan    # dedupe, DB merge, records
    apply_plan(plan, db)  -> IngestReport  # stamp, write, order buy list
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, NamedTuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import slugify

# --------------------------------------------------------------- vocabulary

SLI_WIDTH = 31

KIND_KNIVES = "knives"
KIND_SOURCES = "sources"
KIND_BUYLIST = "buylist"

BUYLIST_SECTION = "buy_list"

RETAILERS = {
    "bladescanada.com": "Blades Canada / Warriors and Wonders",
    "houseofknives.ca": "House of Knives",
    "canadiantire.ca": "Canadian Tire",
    "kershawcanada.com": "Kershaw Canada",
}

# Brands seen across the ledger and the live database. ``build_plan`` also
# learns every brand already filed, so this list only has to seed the shape.
KNOWN_BRANDS = (
    "Bestechman", "Bestech", "DreamTech", "Vosteed", "Microtech", "CIVIVI",
    "SENCUT", "Trivisa", "WE Knife", "Kizer", "Kunwu", "Kansept", "Hogue", "Gerber",
    "Kershaw", "Spyderco", "Cold Steel", "Honey Badger", "Petrified Fish",
    "Rike Knife", "OKC", "Knafs", "SRM Knives", "Molsect", "Vixino Knives",
    "SOG", "QSP", "CJRB", "Benchmade", "CRKT", "Zero Tolerance", "Demko",
    "Chris Reeve", "Emerson", "Protech", "Heretic", "Reate", "Artisan",
    "Real Steel", "Ruike", "Civivi", "Boker", "Ontario",
)

BRAND_TYPOS = {"bestchman": "Bestechman"}

TRACKING_PARAMS = {"srsltid", "gclid", "fbclid", "rq", "ref"}

TODO_LABEL = re.compile(r"^\s*TODO\b", re.I)

# SKU shape: has a digit, letters mostly uppercase (or mostly digits), and
# is not a bare measurement like ``7.4-in``.
_MEASUREMENT = re.compile(r"^\d+(?:\.\d+)?\s*-?\s*(?:in|mm|cm)\.?$", re.I)
_SKU_TOKEN = r"[A-Za-z0-9][A-Za-z0-9./#-]{2,}"

_STEELS = re.compile(
    r"\b(14C28N|12C27|8Cr1[34]MoV|9Cr18MoV|10Cr15MoV|420HC|420|440C?|4116|"
    r"D2|AUS-?\d+|VG-?10|S30V|S35VN|S45VN|S90V|S110V|M390MK|M390|M-Cut|20CV|"
    r"MagnaCut|CPM MagnaCut|Cru-?Wear|Elmax|CTS-?XHP|N690|154CM|Nitro-?V|3V|"
    r"BD1N|AEB-L|SUJ2|Vanax|Damascus)\b",
    re.I,
)


# ------------------------------------------------------------------- lexer

class Token(NamedTuple):
    line: int
    kind: str  # SLI H1 SECTION ANNOTATION ENTRY BLANK PROSE
    text: str
    indent: int = 0


@dataclass
class Diagnostic:
    line: int
    severity: str  # "warning" | "note"
    message: str


def lex(text: str, diagnostics: list[Diagnostic] | None = None) -> list[Token]:
    """Tokenize an ingestion ledger. Fenced code blocks are example material
    and produce no tokens; irregular dash runs still read as SLI, with a
    warning naming the actual width."""
    sink = diagnostics if diagnostics is not None else []
    tokens: list[Token] = []
    in_fence = False
    for line_no, raw in enumerate(text.lstrip("﻿").splitlines(), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if stripped.startswith("```"):
            if not in_fence:
                sink.append(Diagnostic(line_no, "note", "fenced block skipped as example material"))
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            tokens.append(Token(line_no, "BLANK", ""))
        elif re.fullmatch(r"-{3,}", stripped):
            if len(stripped) != SLI_WIDTH:
                sink.append(Diagnostic(line_no, "warning", f"separator has {len(stripped)} dashes; SLI is exactly {SLI_WIDTH}"))
            tokens.append(Token(line_no, "SLI", stripped))
        elif re.match(r"#\s", stripped):
            tokens.append(Token(line_no, "H1", stripped.lstrip("#").strip()))
        elif re.match(r"#{2,}\s", stripped):
            sink.append(Diagnostic(line_no, "warning", "unexpected markdown heading — only the file title uses '#'; headings are '// SectionID'"))
            tokens.append(Token(line_no, "PROSE", stripped))
        elif stripped.startswith("//"):
            tokens.append(Token(line_no, "SECTION", stripped[2:].strip(), indent))
        elif re.match(r"[-*]\s+//", stripped):
            # `- // Name *Tag*` — bullet-form annotation scoped to its
            # indented children, unlike a bare `//` which annotates the
            # rest of the section
            tokens.append(Token(line_no, "ANNOTATION", re.sub(r"^[-*]\s+//\s*", "", stripped), indent))
        elif re.match(r"[-*]\s+\S", stripped):
            tokens.append(Token(line_no, "ENTRY", re.sub(r"^[-*]\s+", "", stripped), indent))
        else:
            tokens.append(Token(line_no, "PROSE", stripped))
    if in_fence:
        sink.append(Diagnostic(len(tokens), "warning", "unterminated fenced block"))
    return tokens


# ------------------------------------------------------------- data model

@dataclass
class Entry:
    label: str
    url: str | None
    line: int
    brand: str = "Unknown"
    model: str = "Unknown"
    sku: str | None = None
    steel: str | None = None
    tags: list[str] = field(default_factory=list)
    source_name: str | None = None
    repairs: list[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class Section:
    name: str
    slug: str
    kind: str
    line: int
    tags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Document:
    title: str
    sections: list[Section]
    diagnostics: list[Diagnostic]


@dataclass
class ParsedTitle:
    brand: str
    model: str
    sku: str | None
    steel: str | None


@dataclass
class IngestPlan:
    new_records: list[dict[str, Any]]
    merges: list[tuple[str, list[str], int | None]]  # (knife_id, sections_to_add, buy_priority)
    sources: list[dict[str, Any]]
    buylist_keys: list[str]  # dedupe keys in priority order
    key_to_id: dict[str, str]  # keys already resolved to existing DB ids
    skipped: list[tuple[int, str, str]]  # (line, label, reason)
    diagnostics: list[Diagnostic]


@dataclass
class IngestReport:
    added: int
    merged: int
    sources: int
    duplicates: int
    buylist: int
    added_ids: list[str]
    merged_ids: list[str]
    repairs: list[tuple[int, str]]
    diagnostics: list[Diagnostic]


# --------------------------------------------------------------- utilities

def section_slug(name: str) -> str:
    """SectionID → stored slug, in the DB's lowercase_underscore style.
    CamelCase splits: ``ForCamping`` → ``for_camping``."""
    split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", split).strip("_").lower()
    return re.sub(r"_+", "_", slug) or "section"


def classify_section(name: str) -> str:
    packed = re.sub(r"[^a-z0-9]", "", name.lower())
    if "buylist" in packed or ("buy" in packed and "list" in packed):
        return KIND_BUYLIST
    if "source" in packed:
        return KIND_SOURCES
    return KIND_KNIVES


def _extract_star_tags(text: str) -> tuple[str, list[str]]:
    """Pull ``*Tag*`` markers off a heading/annotation line."""
    tags = [section_slug(m) for m in re.findall(r"\*([^*]+)\*", text)]
    cleaned = re.sub(r"\*[^*]+\*", "", text)
    cleaned = re.sub(r"[,\s]+$", "", cleaned).strip(" ,")
    return cleaned.strip(), tags


def clean_url(url: str) -> str:
    """Straighten a URL: drop angle wrapping, whitespace, stray parens, and
    tracking query parameters (meaningful queries survive)."""
    url = re.sub(r"[\s<>]+", "", url.strip())
    url = url.replace("()", "").rstrip(")")
    parts = urlsplit(url)
    if parts.query:
        kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))
    return url


def normalize_url(url: str) -> str:
    """Comparison key for dedupe: scheme/www/trailing-slash insensitive."""
    parts = urlsplit(clean_url(url))
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    query = f"?{parts.query}" if parts.query else ""
    return f"{host}{path}{query}".lower()


def url_domain(url: str | None) -> str | None:
    if not url:
        return None
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return host or None


def retailer_for(url: str | None) -> str | None:
    domain = url_domain(url)
    if not domain:
        return None
    for known, name in RETAILERS.items():
        if domain == known or domain.endswith("." + known):
            return name
    return None


def _looks_like_url(text: str) -> bool:
    return bool(re.match(r"https?://", text.strip().strip("<>")))


def _is_sku_candidate(token: str) -> bool:
    token = token.strip()
    if not (3 <= len(token) <= 24) or " " in token:
        return False
    if not any(ch.isdigit() for ch in token):
        return False
    if _MEASUREMENT.match(token):
        return False
    letters = [ch for ch in token if ch.isalpha()]
    digits = sum(ch.isdigit() for ch in token)
    if letters and sum(ch.isupper() for ch in letters) / len(letters) < 0.5:
        return digits >= len(token) * 0.6  # e.g. retailer codes like 1752469p
    return True


def title_from_url(url: str) -> str:
    """A display title derived from a product URL slug, for TODO/URL-only
    labels. Retailer slugs are word lists; the last SKU-shaped token is
    separated with a dash per the ledger's reference rule."""
    segment = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    segment = re.sub(r"\.(html?|php|aspx?)$", "", segment, flags=re.I)
    words = [w for w in segment.split("-") if w]
    if not words:
        return url
    styled: list[str] = []
    for word in words:
        if any(ch.isdigit() for ch in word):
            styled.append(word.upper())
        elif word.isupper() or len(word) <= 3:
            styled.append(word.upper() if word.lower() in {"sw", "od", "cf", "pvd", "dlc", "okc", "srm", "we"} else word.capitalize())
        else:
            styled.append(word if word[0].isupper() else word.capitalize())
    if len(styled) > 1 and _is_sku_candidate(styled[-1]):
        return " ".join(styled[:-1]) + " - " + styled[-1]
    return " ".join(styled)


# -------------------------------------------------------------- title parse

def _extract_sku(label: str) -> tuple[str, str | None, list[str]]:
    """Peel a reference number off a label. Round brackets and ``#`` refs
    are normalized to dash separation (the REF2 rule)."""
    repairs: list[str] = []
    patterns = (
        (rf"\(\s*({_SKU_TOKEN})\s*\)\s*$", "bracket reference normalized to dash separation"),
        (rf"#\s*({_SKU_TOKEN})\s*$", "hash reference normalized to dash separation"),
        (rf"\s[-–—]\s*({_SKU_TOKEN})\s*$", ""),
        (rf",\s*({_SKU_TOKEN})\s*$", ""),
    )
    for pattern, note in patterns:
        match = re.search(pattern, label)
        if match and _is_sku_candidate(match.group(1)):
            sku = match.group(1).strip()
            label = label[: match.start()].rstrip(" ,-–—#")
            if note:
                repairs.append(note)
            return label, sku, repairs
    return label.rstrip(" ,"), None, repairs


def _match_brand(label: str, known_brands: tuple[str, ...] | list[str]) -> str | None:
    lowered = label.lower()
    for brand in sorted(set(known_brands), key=len, reverse=True):
        prefix = brand.lower()
        if lowered.startswith(prefix) and (len(lowered) == len(prefix) or not lowered[len(prefix)].isalnum()):
            return brand
    return None


def parse_title(label: str, known_brands: tuple[str, ...] | list[str] = KNOWN_BRANDS) -> ParsedTitle:
    """Split a ledger label into brand, model (with ``(SKU)`` suffix per the
    database convention), reference number, and a steel guess."""
    label = re.sub(r"\s+", " ", label).strip()
    remainder, sku, _ = _extract_sku(label)

    first_word = remainder.split(" ", 1)[0].strip(",") if remainder else ""
    typo = BRAND_TYPOS.get(first_word.lower())
    if typo:
        remainder = typo + remainder[len(first_word):]
    brand = _match_brand(remainder, known_brands) or (remainder.split(" ", 1)[0].strip(",") if remainder else "Unknown")

    after_brand = remainder[len(brand):].strip(" ,") if remainder.lower().startswith(brand.lower()) else remainder
    segments = [seg.strip() for seg in after_brand.split(",") if seg.strip()]
    model_base = segments[0] if segments else (after_brand or "Unknown")

    steel = None
    for segment in segments:
        match = _STEELS.search(segment)
        if match:
            steel = match.group(1)
            break

    model = f"{model_base} ({sku})" if sku else model_base
    return ParsedTitle(brand=brand, model=model, sku=sku, steel=steel)


# ------------------------------------------------------------------ parser

_LINK_STANDARD = re.compile(r"\[(?P<label>.*?)\]\((?P<url>.*)\)\s*$", re.S)
_LINK_ANGLE = re.compile(r"\[(?P<label>.*?)\]\s*<(?P<url>.*?)>\s*$", re.S)
_LINK_LABEL_ONLY = re.compile(r"\[(?P<label>.*?)\]\s*$", re.S)


def _unbalanced(text: str) -> bool:
    return text.count("[") != text.count("]") or text.count("(") != text.count(")")


def _parse_entry(raw: str, line_no: int, diagnostics: list[Diagnostic]) -> Entry:
    text = raw.strip()
    repairs: list[str] = []

    label: str = text
    url: str | None = None
    for pattern in (_LINK_STANDARD, _LINK_ANGLE):
        match = pattern.match(text)
        if match:
            label = match.group("label").strip()
            url = match.group("url").strip()
            if pattern is _LINK_ANGLE:
                repairs.append("angle-bracket link form unwrapped")
            break
    else:
        match = _LINK_LABEL_ONLY.match(text)
        if match:
            label = match.group("label").strip()
        elif _looks_like_url(text):
            url, label = text, ""

    if url and _looks_like_url(label) and not _looks_like_url(url):
        label, url = url, label
        repairs.append("swapped label and url")

    if url is not None:
        cleaned = clean_url(url)
        if cleaned != url.strip():
            repairs.append("url cleaned")
        url = cleaned
        if not _looks_like_url(url):
            diagnostics.append(Diagnostic(line_no, "warning", f"entry has no usable url: {text[:60]}"))
            url = None

    if (not label or TODO_LABEL.match(label) or _looks_like_url(label)) and url:
        label = title_from_url(url)
        repairs.append("title derived from url slug")

    entry = Entry(label=label, url=url, line=line_no, raw=raw, repairs=repairs)

    stripped_label, sku_from_ref, ref_repairs = _extract_sku(label)
    entry.repairs.extend(ref_repairs)
    parsed = parse_title(label)
    entry.brand, entry.model, entry.sku, entry.steel = parsed.brand, parsed.model, parsed.sku, parsed.steel
    if entry.sku is None and sku_from_ref:
        entry.sku = sku_from_ref
        entry.model = f"{stripped_label} ({sku_from_ref})"
    return entry


def parse_document(text: str) -> Document:
    diagnostics: list[Diagnostic] = []
    tokens = lex(text, diagnostics)

    title = ""
    sections: list[Section] = []
    current: Section | None = None
    annotation_name: str | None = None
    annotation_tags: list[str] = []
    annotation_indent: int | None = None  # set for bullet-form annotations only

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.kind == "H1":
            if not title:
                title = token.text
                if any(t.kind in {"SECTION", "ENTRY"} for t in tokens[:i]):
                    diagnostics.append(Diagnostic(token.line, "warning", "file title should be the first heading"))
            else:
                diagnostics.append(Diagnostic(token.line, "warning", "extra '#' heading ignored — sections use '// SectionID'"))
            i += 1
            continue

        if token.kind == "SECTION":
            previous = tokens[i - 1] if i else None
            fenced_above = previous is not None and previous.kind == "SLI"
            if not fenced_above and current is not None:
                # a ``//`` line inside a section body: inline annotation
                # for the rest of the section
                name, tags = _extract_star_tags(token.text)
                annotation_name = name or None
                annotation_tags = tags
                annotation_indent = None
                i += 1
                continue
            if not fenced_above:
                diagnostics.append(Diagnostic(token.line, "warning", "SectionID missing SLI directly above"))
            elif previous is not None and i >= 2 and tokens[i - 1].kind == "SLI" and tokens[i - 2].kind == "BLANK":
                pass  # SLI fences the heading; blank above the SLI is normal
            name, tags = _extract_star_tags(token.text)
            following = tokens[i + 1] if i + 1 < len(tokens) else None
            after_blank = tokens[i + 2] if i + 2 < len(tokens) else None
            if following is None or following.kind != "BLANK":
                diagnostics.append(Diagnostic(token.line, "warning", "SectionID must be followed by an empty line"))
            elif after_blank is None or after_blank.kind != "SLI":
                diagnostics.append(Diagnostic(token.line, "warning", "SectionID heading is not closed by an SLI"))
            current = Section(name=name, slug=section_slug(name), kind=classify_section(name), line=token.line, tags=tags)
            sections.append(current)
            annotation_name = None
            annotation_tags = []
            annotation_indent = None
            i += 1
            continue

        if token.kind == "ANNOTATION":
            if current is None:
                diagnostics.append(Diagnostic(token.line, "warning", "annotation before any SectionID — ignored"))
            else:
                name, tags = _extract_star_tags(token.text)
                annotation_name = name or None
                annotation_tags = tags
                annotation_indent = token.indent
            i += 1
            continue

        if token.kind == "ENTRY":
            if annotation_indent is not None and token.indent <= annotation_indent:
                # a sibling (or shallower) entry closes a bullet-form annotation
                annotation_name = None
                annotation_tags = []
                annotation_indent = None
            raw = token.text
            consumed = 0
            while _unbalanced(raw) and consumed < 3:
                lookahead = tokens[i + 1 + consumed] if i + 1 + consumed < len(tokens) else None
                if lookahead is None or lookahead.kind not in {"PROSE", "ENTRY"}:
                    break
                raw += lookahead.text
                consumed += 1
            entry = _parse_entry(raw, token.line, diagnostics)
            if consumed:
                entry.repairs.append(f"joined {consumed} continuation line(s)")
                i += consumed
            if current is None:
                diagnostics.append(Diagnostic(token.line, "warning", "entry before any SectionID — filed under 'unfiled'"))
                current = Section(name="Unfiled", slug="unfiled", kind=KIND_KNIVES, line=token.line)
                sections.append(current)
            entry.tags = list(annotation_tags)
            entry.source_name = annotation_name
            current.entries.append(entry)
            i += 1
            continue

        if token.kind == "PROSE" and current is not None and token.text.startswith(">"):
            note = token.text.lstrip("> ").strip()
            if note:
                current.notes.append(note)
        i += 1

    return Document(title=title, sections=sections, diagnostics=diagnostics)


# ----------------------------------------------------------------- planner

def _existing_indexes(db: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """(sku → id, normalized url → id, known brands) from the live database."""
    sku_index: dict[str, str] = {}
    url_index: dict[str, str] = {}
    brands: list[str] = []
    for record in db.get("knives") or []:
        if not isinstance(record, dict):
            continue
        rid = str(record.get("id") or "")
        if not rid:
            continue
        brand = str(record.get("brand") or "").strip()
        if brand and brand.lower() not in {"unknown", ""}:
            brands.append(brand)
        model = str(record.get("model") or "")
        match = re.search(r"\(([A-Za-z0-9./#-]+)\)\s*$", model)
        if match:
            sku_index.setdefault(match.group(1).lower(), rid)
        for retailer in record.get("canadian_online_retailers") or []:
            if isinstance(retailer, dict) and retailer.get("url"):
                url_index.setdefault(normalize_url(str(retailer["url"])), rid)
    return sku_index, url_index, brands


def _entry_key(entry: Entry) -> str:
    if entry.sku:
        return f"sku:{entry.sku.lower()}"
    if entry.url:
        return f"url:{normalize_url(entry.url)}"
    return f"label:{slugify(entry.label)}"


def _build_record(entry: Entry, sections: list[str]) -> dict[str, Any]:
    retailer_name = retailer_for(entry.url)
    retailers: list[dict[str, Any]] = []
    if retailer_name and entry.url:
        retailers.append(
            {
                "retailer": entry.source_name or retailer_name,
                "url": entry.url,
                "listed_price_cad": None,
                "availability": "unknown",
                "source_date": date.today().isoformat(),
            }
        )
    return {
        "id": slugify(f"{entry.brand} {entry.model}"),
        "brand": entry.brand,
        "model": entry.model,
        "user_classification": None,
        "user_tags": sorted(set(sections)),
        "research_status": "canadian_retailer_verified" if retailers else "pending_canadian_retailer_search",
        "acquisition_status": "pending_research",
        "mechanism": {
            "opening_method": None,
            "lock_type": None,
            "assist_type": "unknown",
            "blade_length": None,
            "blade_steel": entry.steel,
            "clear_prohibited_mechanism_found": None,
        },
        "canadian_online_retailers": retailers,
        "notes": "",
        "source_input": entry.raw.strip(),
        "_sku": entry.sku,
        "_key": _entry_key(entry),
        "_line": entry.line,
        "_repairs": list(entry.repairs),
    }


def build_plan(doc: Document, db: dict[str, Any]) -> IngestPlan:
    sku_index, url_index, db_brands = _existing_indexes(db)
    known_brands = list(KNOWN_BRANDS) + db_brands

    new_records: list[dict[str, Any]] = []
    new_by_key: dict[str, dict[str, Any]] = {}
    merges: dict[str, set[str]] = {}
    sources: list[dict[str, Any]] = []
    seen_source_urls: set[str] = set()
    buylist_keys: list[str] = []
    key_to_id: dict[str, str] = {}
    skipped: list[tuple[int, str, str]] = []
    diagnostics = list(doc.diagnostics)

    for section in doc.sections:
        if section.kind == KIND_SOURCES:
            for entry in section.entries:
                key = normalize_url(entry.url) if entry.url else slugify(entry.label)
                if key in seen_source_urls:
                    skipped.append((entry.line, entry.label, "duplicate source"))
                    continue
                seen_source_urls.add(key)
                sources.append({"name": entry.label, "url": entry.url, "sections": sorted({section.slug, *section.tags, *entry.tags})})
            continue

        member_sections = [BUYLIST_SECTION] if section.kind == KIND_BUYLIST else [section.slug]
        member_sections += section.tags

        for entry in section.entries:
            # re-parse with the learned brand table so DB brands win
            parsed = parse_title(entry.label, known_brands)
            if parsed.brand != entry.brand:
                entry.brand, entry.model, entry.steel = parsed.brand, parsed.model, parsed.steel or entry.steel
                if parsed.sku:
                    entry.sku = parsed.sku
            key = _entry_key(entry)
            entry_sections = sorted({*member_sections, *entry.tags})

            existing_id = None
            if entry.sku:
                existing_id = sku_index.get(entry.sku.lower())
            if existing_id is None and entry.url:
                existing_id = url_index.get(normalize_url(entry.url))

            if section.kind == KIND_BUYLIST and key not in buylist_keys:
                buylist_keys.append(key)

            if existing_id:
                key_to_id[key] = existing_id
                merges.setdefault(existing_id, set()).update(entry_sections)
                continue

            duplicate = new_by_key.get(key)
            if duplicate is not None:
                duplicate["user_tags"] = sorted(set(duplicate["user_tags"]) | set(entry_sections))
                skipped.append((entry.line, entry.label, "duplicate in file"))
                continue

            record = _build_record(entry, entry_sections)
            new_by_key[key] = record
            new_records.append(record)

    merge_list = [(rid, sorted(section_set), None) for rid, section_set in merges.items()]
    return IngestPlan(
        new_records=new_records,
        merges=merge_list,
        sources=sources,
        buylist_keys=buylist_keys,
        key_to_id=key_to_id,
        skipped=skipped,
        diagnostics=diagnostics,
    )


def apply_plan(plan: IngestPlan, db: dict[str, Any]) -> IngestReport:
    """Write the plan into the database dict (no file I/O here)."""
    from .buylist import set_buylist
    from .store import add_knife

    repairs: list[tuple[int, str]] = []
    added_ids: list[str] = []
    key_to_id = dict(plan.key_to_id)

    for record in plan.new_records:
        staged = dict(record)
        key = staged.pop("_key")
        line = staged.pop("_line")
        staged.pop("_sku", None)
        for note in staged.pop("_repairs", []):
            repairs.append((line, note))
        add_knife(db, staged)
        key_to_id[key] = staged["id"]
        added_ids.append(staged["id"])

    merged_ids: list[str] = []
    by_id = {str(k.get("id")): k for k in db.get("knives") or [] if isinstance(k, dict)}
    for rid, add_sections, _priority in plan.merges:
        record = by_id.get(rid)
        if record is None:
            continue
        current = [str(t) for t in record.get("user_tags") or []]
        record["user_tags"] = sorted(set(current) | set(add_sections))
        merged_ids.append(rid)

    if plan.sources:
        registry = db.setdefault("sources", [])
        known = {normalize_url(str(s.get("url"))) for s in registry if isinstance(s, dict) and s.get("url")}
        for source in plan.sources:
            key = normalize_url(str(source.get("url"))) if source.get("url") else str(source.get("name"))
            if key in known:
                continue
            known.add(key)
            registry.append(source)

    buylist_ids = [key_to_id[key] for key in plan.buylist_keys if key in key_to_id]
    if buylist_ids:
        set_buylist(db, buylist_ids)

    return IngestReport(
        added=len(added_ids),
        merged=len(merged_ids),
        sources=len(plan.sources),
        duplicates=len(plan.skipped),
        buylist=len(buylist_ids),
        added_ids=added_ids,
        merged_ids=merged_ids,
        repairs=repairs,
        diagnostics=plan.diagnostics,
    )
