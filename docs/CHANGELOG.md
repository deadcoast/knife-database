# CHANGELOG

## 006 — v0.10.0 (2026-07-23) — THE RESEARCH DESK

The vault researches its own unknowns. Case:
`docs/dev-spec/2026-07-23-research-desk` (in development).

- **The research backend** (`knivves/research.py`) — three pure stages,
  offline-testable: `audit_record`/`audit_database` name every gap in a
  record as data (placeholder `TODO:` titles, Unknown mechanism fields,
  missing prices); `build_docket` orders the work BuyList-rank first,
  then ★new, then most-gaps-first, shelving records with no supported
  listing URL as *unreachable* with the reason said; `research_record`
  merges a fetched listing under the law **fill only what is empty** —
  user data is never overwritten, every fill carries provenance
  (`research.filled` names the host per field), a filled first price
  seeds `price_history` and re-tags the $150 rule, and rulebook hits
  are **reported, never written** — the prohibited flag stays the
  user's decision. `run_research` works the docket concurrently with
  deterministic apply order and an injectable fetch.
- **One rulebook table** — the legal-screen keyword table
  (`RULE_KEYWORDS`) moved to its backend home in `research.py`; the
  Forge Line imports it. Same words, one source of truth.

## 005 — v0.9.0 (2026-07-23) — PLAIN WORDS ON THE DOORS

Normalized names, a real front door, and the ledger intake inside the
vault. The craft stays; the labels stop being homework.

- **Rooms renamed** — proprietary titles normalized to plain function:
  **Library** (was The Rack), **Import Knives** (The Forge Line),
  **Compare Models** (The Bench), **Market Prices** (The Ledger). Keys,
  modules, and mechanics unchanged; only the doors read differently.
- **Import Knives takes ingestion files** — enter a path to an ingestion
  `.md` in the same intake slot: sections read at EXTRACT, the plan
  screens at LEGAL SCREEN (file / merge / duplicates / buy-list rungs /
  format warnings), and the batch files ★new at VAULT — the same line the
  URL intake runs, with its own output fitted to the stations.
- **`--survey` → `--prices`** — `knivves update --prices` is the flag;
  "Market Prices" is the room that references it. Progress reads
  "reading market prices"; first prices are counted in the summary, never
  streamed (nothing to compare against); movers keep live ▼/▲ deltas.
- **A real home page** — bare `knivves` now opens the welcome page: vault
  state, ★new window, next acquisitions, and every door with its command.
  The classic interactive table lives on as `knivves browse` — nothing
  removed, everything reachable.
- **One palette everywhere** — the classic CLI's drifting colors
  (default cyan/magenta/blue) normalized to the house laws: steel text,
  machined edges, single amber accent, mint ★new. `★new` placement:
  end of Brand marks a new maker, start of Model marks a new blade,
  aligned in the gutter across the Library and every CLI table.
- **Freshness ages by batches** — an update that files nothing holds the
  generation line (`--force` ages the window deliberately); the batch an
  update seals survives that update.

## 004 — v0.8.0 (2026-07-23) — THE INTAKE DOCK

Ingestion, freshness, and the acquisition ladder. The database now eats
markdown link ledgers whole and knows what's fresh.

- **`knivves add <file.md>`** — markdown ingestion: SLI-fenced (31-dash)
  `// SectionID` grammar, `*Tag*` markers, inline source annotations,
  BuyList/Sources section kinds. A tolerant lexer/parser repairs real-world
  damage — swapped `[url](label)` links, URLs split across lines,
  `[label]<url()>` angle forms, `(REF)`/`#REF` normalization, tracking-query
  stripping, `TODO:` titles derived from URL slugs — and reports every
  repair and grammar diagnostic. `--dry-run` previews the full plan.
  Entries dedupe in-file (SKU → URL → label) and merge into existing
  records instead of duplicating them.
- **`knivves update`** — seals the fresh batch as the newest NEW
  generation and records history. Freshness ages by batches of arrivals,
  not update count: an empty update holds the line (`--force` overrides).
  `--survey` re-reads every supported live listing concurrently with a
  live progress bar; observations land in `price_history` and the $150
  affordable rule re-tags, exactly like the Ledger room.
- **`knivves new`** — the three-generation cache: `-oneg`/`-twog`/`-threeg`
  set how many updates a knife survives as ★NEW; `--status` shows the
  cache; plain `new` lists what's fresh. NEW reads everywhere: CLI tables,
  summary cards, the interactive browser, the Rack, the masthead.
- **SectionID** — the formal vocabulary for group identifiers:
  `knivves section add/remove/list`, `knivves list -section X`,
  `knivves sections`; `tag` stays as the quality-of-life alias.
- **The Reserve** — the BuyList as a room fixture: `y` on the Rack slides
  in the priority ladder with running Σ CAD; `knivves buylist` prints the
  same ladder with cumulative cost; the list page shows a compact BuyList
  window.
- New pure backend modules (`ingest`, `generations`, `buylist`) with
  plain-python test suites lifted from the production ledger's actual
  malformed lines.

## 003 — v0.7.0 (2026-07-21) — KNIVVES VAULT

The visual application. Built with Textual as one coherent machine —
rooms behind a vault door, records as traveling objects, the database's
own rules executing on screen.

The building:

- **The Rack** — sortable/searchable collection; plate slides in on
  selection while the rack recedes (depth); `a`/`x`/`u` classification
  writes the database live.
- **The Forge Line** — live retailer intake: paste a URL, parsed fields
  stamp the plate, the prohibited-mechanism rulebook executes as gates
  (a hit rejects; nothing is written), cleared records file for real.
  `r` replays a no-network demo transit.
- **The Bench** — send knives from the rack with `b`; choreographed
  arrivals (seated plates never re-animate; replacements depart first);
  the calipers take the measurement line by line.
- **The Ledger** — drawn instruments (price scale with the $150 rule cut
  in accent; gradient histogram); `s` surveys every live listing,
  appends price history, surfaces movers, re-tags line-crossers.

The material:

- Machined vault door on boot and every room switch (drawn steel leaves,
  bolt cascade, staged parting; brand engraved on boot).
- Single-widget brushed-steel masthead with stamped chrome and per-room
  state readouts (sort · line state · bench pairing · survey lifecycle).
- Engraved station headers; tip rail beside the data with ❯ expansion
  capsules; command palette commands for rooms and the survey.
- House laws as code (`laws.py`): one palette, one field grammar, one
  motion law.

Engineering:

- Six custom `render_line` widgets; headless Pilot suite driving every
  capability against a throwaway database, including layout-law
  assertions; eyes-on frame-capture verification pipeline (the
  `docs/media/` exhibits are its output).
- Backend additions: `scrape.py` (listing parser), `ledger.py` (price
  history, movers, the affordable-threshold rule), `price_history` on
  records, `file_record`/`classify` operations.
- Build fix: explicit setuptools package discovery; textual pinned.

## 002 — v0.5.0 (2026-07-18) — checkpoint release

Database:

- Imported all 53 knives from TODO.md into the database, deduplicated, with section provenance in notes.
- Scraped every retailer product page (Blades Canada, House of Knives) to populate CAD prices, availability, blade steel, lock type, opening method, and blade length. 64/67 knives now priced; the only unpriced records are the three without a Canadian product listing (Kunwu Albatross, Miguron Karok Teal, Kubey Zephyr).
- Renamed all records to short scannable model names ("Bel Air XL (KE-6110)"); the original verbose retailer listing title is preserved per record in `listing_title`.
- New tag rule: `affordable` is auto-assigned to any knife priced under $150 CAD and is the only non-user-assigned tag. All other tags (clean, fancy, tiered) remain user-assigned.
- Resolved all pending records with confirmed retailer links (Kizer T1-BD, Drop Bear Zero, Sebenza 31 Insingo L31-1124); added CRKT Zephyr and Kubey Gurkha; removed Kissing Crane (dead listing); Kubey Zephyr and Miguron Karok Teal kept on US/brand sources pending Canadian availability.

Interactive UI:

- Redraw now clears terminal scrollback — no more stacked stale frames.
- Page size adapts to terminal height instead of a fixed 8 rows.
- Replaced the boxed banner/summary/filter panels with a compact 2-line header.
- Table rows are always one line per knife (ellipsis truncation).
- Footer documents that typing any text is a live substring search.

## 001

The Current Repository has built out the supporting CLI, and will continue developing the CLI untill it is in a complete and working state. After the CLI is complete and the development is in a stable state, the front end web stack work will begin.

CLI Install:

```bash
cd knivves
python -m pip install -e .
```

Run the interactive CLI:

```bash
knivves
```

Useful direct commands:

```bash
knivves list
knivves list --tag clean
knivves list --classification approved
knivves list --canadian
knivves list --sort price
knivves show benchmade-bugout-axis-lock-535sl-13
knivves path
knivves export ./knives.backup.json
knivves reset
```

It creates/uses your live database here:

```text
~/.knivves/knives.json
```

What I included:

```text
knivves/
├── pyproject.toml
├── README.md
└── knivves/
    ├── __init__.py
    ├── cli.py
    ├── models.py
    ├── render.py
    ├── store.py
    └── data/
        └── knives.json
```

The CLI uses a JSON structure, with knife-name slug IDs like:

```json
"benchmade-bugout-axis-lock-535sl-13"
```

and supports filtering by:

```text
classification
tag
research status
Canadian retailer presence
search text
price / brand / model / steel sorting
```

---

## 002

Built the second-pass **`knivves` v0.2.0** CLI.

Download: [knivves-v0.2.0.zip](sandbox:/mnt/data/knivves-v0.2.0.zip)

Also kept the standard filename updated here: [knivves.zip](sandbox:/mnt/data/knivves.zip)

Install:

```bash
cd knivves
python -m pip install -e .
```

Run:

```bash
knivves
```

Major upgrades included:

```text
CLI UI
- Cleaner Rich dashboard
- Responsive table layout for narrow terminals
- Better detail panels
- Stats dashboard
- Interactive pagination
- Interactive search/filter/sort flow
- Help panel inside the interactive menu

Database output
- table / compact / json / jsonl / csv / ids outputs
- tag, retailer, steel, status indexes
- filtered exports
- CSV-friendly flattened rows
- retailer URL printing/opening
- validation/doctor command

Quality of life
- approve / reject shortcuts
- classify command
- add knife command
- add/remove retailer commands
- tag add/remove
- append/replace notes
- delete records
- automatic backups before mutations
- backup listing
- restore command
- KNIVVES_DB override support
- cleaner JSON validation
```

Useful commands:

```bash
knivves
knivves dashboard
knivves list
knivves list -q bugout
knivves list -t clean
knivves list -c approved
knivves list --canadian
knivves list --sort price
knivves list --output csv > knives.csv
knivves show benchmade-bugout-axis-lock-535sl-13
knivves open benchmade-bugout-axis-lock-535sl-13
knivves approve chris-reeve-sebenza
knivves reject some-knife-id
knivves tag add benchmade-bugout-axis-lock-535sl-13 favorite
knivves note benchmade-bugout-axis-lock-535sl-13 "Great lightweight EDC reference."
knivves retailer add chris-reeve-sebenza --retailer "Example Canada" --url "https://example.ca" --price 500
knivves doctor
knivves backup before-next-research-pass
knivves backups
```

The live database still defaults to:

```text
~/.knivves/knives.json
```

And backups go to:

```text
~/.knivves/backups/
```
