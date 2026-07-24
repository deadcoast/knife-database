# CHANGELOG

## 011 — v0.15.0 (2026-07-24) — PLAIN LANGUAGE, EVERYWHERE

The owner's standing correction, applied for good this time: no
invented vocabulary anywhere a user reads. The instruments and motion
stay; every label now says what the thing is.

- **Page 0 is HOME** — module `pages/home.py`, `HomeScreen`, key
  `home`, footer key `0 Home`. Its plaques read COLLECTION / PAGES /
  BUY LIST; the state lines read KNIVES / GAPS / AVG / NEW CACHE. The
  brand is just KNIVVES — masthead, boot door, nameplate, CLI page.
- **Import Knives** — stations read PARSE / LEGAL CHECK / SAVE. The
  rule bank reads "7/7 RULES CLEAR — CLEAR TO PROCEED" / "BLOCKED ✗
  matched: …"; the title strip reads "N value(s) matched in the
  title"; the tally reads SAVED / FILED / REFUSED / REJECTED by the
  rules; statuses read "parsing ▸ / legal check ▸ / saving ▸ /
  saved ✓ / idle". "already in the database", "demo — nothing was
  saved".
- **Research** — stations read QUEUE / READ / SAVE; statuses count "N
  in queue"; summaries read "N fields filled — shown in amber",
  "saved to the database"; the map legend reads "dark = unknown ·
  +N off screen".
- **Compare / Library / Market** — "nothing to compare", "one knife
  placed", "missing data"; search reads "/ search — brand, steel,
  lock, tag …", "no knives match", buttons read Compare and Buy list;
  the side panel and home plaque read BUY LIST; "N knives within $25
  of the line"; every "blades"/"the vault" in stats and tips is now
  "knives"/"the collection"/"the database". The CLI welcome panel
  reads "commands".
- Eighteen shell proofs and all backend suites green after the rename
  (tests updated in lockstep); every exhibit regenerated; version
  stamps 0.15.0.

## 010 — v0.14.0 (2026-07-24) — STATION INSTRUMENTS

The lower halves stop being panels and become working hardware — every
station now carries an instrument fed by real data, finishing the
room-presence correction (009) across imports, market, and research.

- **The parse register** (`imports.py::ParseRegister`) — the extractor's
  lower bank: one slot per fact the parser can pull. A slot lights
  amber when its value came off the tape itself, steel when learned
  elsewhere on the page, and stays a dark socket with a channel dash
  when the listing never gave it up — the parse, honest, in one glance.
  Both transits and the demo stamp it; the line reset clears it.
- **The check log under the lock** — the legal station's lower half is
  a teletype: on entry it prints the rulebook itself (one bolt per
  rule, paced); during a transit it logs the check rule by rule —
  ● no match in steel, ✗ matched in FAIL — while the bolts animate
  above. The pseudo-terminal surface now works two rooms.
- **The vault tally** — the filing station counts its session: the
  ★new window as a mint meter over IN VAULT / FILED / REFUSED /
  REJECTED counters, incremented by live, file, and duplicate paths.
- **The $150 line as geography** — market's middle station draws the
  rule instead of listing near it: blades over the line descend onto
  the amber ━━ $150 ━━ cut, blades under it hang below in pass-green,
  with the band population counted. The survey station gains HISTORY
  and PRICED meters over the whole collection.
- **The stamp meters** — research's STAMP station carries COMPLETE
  (pass-green) and DOCKET-open (amber) meters, live through passes and
  refreshes. Suite still eighteen proofs green; exhibits regenerated
  and eyes-on; version stamps 0.14.0.

## 009 — v0.13.0 (2026-07-23) — ROOM PRESENCE

The rooms stop floating boxes on a void. Owner's verdict on the 008
frames: sparse layouts read as lazy, and restraint was the wrong read
of the design standard — a single frozen frame must look like machined
hardware. This release is the correction.

- **Material everywhere** — stations and plaques are raised machined
  plates, not outlines: surface metal for the body, top/left edges
  catching the light, bottom/right falling into shadow (per-edge border
  bevel in the stylesheets). Applies to every station on imports,
  research, and market, and to the hall's plaques.
- **The hall rebuilt as the showpiece** — a `BrandPlate` band of
  brushed steel with the brand stamped into it, bolt studs, and a
  machined groove (the door's own material); the vault state as an
  instrument bank — `MeterBar` gauges (approved in pass-green, 
  researched, priced, under-$150 in amber) over the spoken numbers;
  the doors as machined slabs with amber keycaps; and the entire
  collection drawn across the floor — the unknowns map as the hall's
  base band, powering on with the room and breathing on the idle
  cadence. `VaultState` grew `priced`/`affordable` to feed the meters.
- **Compare rebuilt around the full-width bed** — the calipers span
  the room: beams ride rails the length of the bench (Δ engraved in
  the amber span between distant jaws), and the instrument holds its
  shape at rest — open rails, parked jaws, disengaged linkages, honest
  about holding no work. The center panel carries the measurement
  verdict once a pair reads. The bed fills everything below the
  plates; no void survives an empty bench.
- Eyes-on iterations during the build: the brand plate's seam first
  rendered as a broken half-width bar (now a full channel groove); the
  reserve engraving clipped mid-word (renamed THE RESERVE); compare's
  empty state floated a small panel in black (the bed now takes the
  room). Suite still eighteen proofs green plus six backend suites;
  exhibits regenerated; version stamps 0.13.0.

## 008 — v0.12.0 (2026-07-23) — ONE BUILDING

The fixtures agree with each other. Case:
`docs/dev-spec/2026-07-23-one-building`, opened from the re-alignment's
triaged harvest (TA-2/3/4).

- **One reading of the vault's state** — `knivves/state.py`: the frozen
  `VaultState` and `vault_state(db)` are now the single derivation of
  blades / ★new / approved / unresearched / avg CAD / generation window
  / the acquisition ladder. The CLI welcome page (`render.home_page`
  now takes the state, text unchanged) and the TUI entry hall both
  speak it; neither computes. The two front doors cannot disagree —
  proven by `test_two_front_doors_agree`, which reads the hall's
  plaques and the rendered welcome page against the same reading.
- **The doors answer the hand** — each hall door is a `DoorRow`
  fixture: click it and its page opens (the click fires the same
  `action_room` the number key does), hover it and the row lifts
  through the cue law in `vault.tcss`. The plaque's reveal fade covers
  the rows.
- **The carrying law reaches the intake line** — `#forge-plate` is
  hidden until a transit's first `begin`; all three transits (live,
  file, demo) carry. A record plate now exists in every room only
  while it holds a record — the law the research desk set in 007.
- Suite grows to eighteen proofs (`test_state.py` new; agree/doors/
  carrying added to the shell suite); exhibits refreshed and reviewed
  eyes-on; version stamps bumped to 0.12.0 (pyproject, bundled DB).

## 007 — v0.11.0 (2026-07-23) — THE STANDARDS RE-ALIGNMENT

The source stops lying about the building. Case:
`docs/dev-spec/2026-07-23-standards-realignment` (in development),
steered by `revisions.md`.

- **Pages own their modules** — `knivves/vault/` is now `knivves/tui/`
  with a `pages/` package: one module per door, named as the door reads
  (`library`, `imports`, `compare`, `market`, `research`), screen
  classes and registry keys renamed to match (`KnivvesVault` →
  `KnivvesApp`). The two-ledger shadow (`vault/ledger.py` over
  `knivves/ledger.py`) is gone. Mechanics untouched; the Pilot suite
  drives every capability unchanged.
- **The vault is a page** — page 0, the entry hall: the machined door
  now parts onto the hall — vault state (blades / ★new / approved /
  unresearched gaps / avg CAD / generation window), the six doors with
  their keys, the acquisition ladder's top rungs — derived from the
  same backend reads as the CLI home page, so the two front doors
  cannot disagree. `0` returns home from any page. The hall carries the
  first per-page stylesheet (`pages/vault.tcss` via `Screen.CSS_PATH`)
  — the mechanism the rest of the re-alignment rides.
- **One theme, six stylesheets** — the house palette is now the
  registered `knivves` Theme, built in `laws.py` from the same constants
  (single Python source of truth) with every house color flowing into
  TCSS as `$variables`; `get_theme_variable_defaults` holds the palette
  law even if the theme menu is used. The monolith stylesheet dissolved:
  `app.tcss` keeps only building chrome (Screen base, Footer, station
  frames); each page carries its own stylesheet beside its module via
  `Screen.CSS_PATH` — `vault/library/imports/compare/market/research.tcss`.
  Zero raw colors remain in any stylesheet; the fixture widgets'
  `DEFAULT_CSS` (masthead, door, plate, reserve, tips) speak `$variables`
  too. Three machined tones the CSS had been carrying alone
  (`SURFACE_LOW/HIGH/RAISED`) and the body-text steel (`STEEL_BODY`)
  are now laws. All six page frames captured and reviewed eyes-on —
  no drift under the theme.
- **The motion law grows tiers** — REVEAL / IDLE / CUE codified in
  `laws.py`: tier constants (settle, stagger, cadence, cue duration)
  and the `Reveal` runner — a page's one opening performance, run once
  per entrance, re-armed on exit, `settle()` landing every remaining
  step instantly so a reveal never blocks the hand. CUE durations flow
  into TCSS as `$cue-duration`/`$cue-easing`; the pointer-facing pages
  answer the hand in their own stylesheets — hall plaques lift with an
  edge-catch, the search and intake slots light under hover and focus
  (`transition:` + pseudo-classes). Compare and market are keyboard
  instruments and stay still, per the balance law. Eyes on the hover
  frame caught a two-tone artifact (plaque lifted, its text rows
  didn't) — fixed by lifting the children with the plaque.
- **The unknowns map powers on** — entering Research runs the
  instrument's self-test, once per entrance: columns energize left to
  right on an accelerating cascade, the completeness gauge sweeps to
  its true value with the count climbing, the scale ticks ride the
  wavefront, and the rail's legend lands only at settle. Only truth is
  dramatized — a column, once lit, shows its real state — and the
  whole performance stands down during a pass. After settle the map
  breathes: a scan shimmer crosses the field on the long IDLE cadence,
  catching only lit dots, standing down for reveal and pass alike.
- **The desk is one instrument** — the card file rebuilt as hardware:
  each docket tab is a real widget that answers the hand. Hovering a
  card lights its column on the map (steel-bright, with a ▴ rail
  marker); hovering a map column lifts its card in return; the
  spotlight dies when the hand leaves. Card cues live in
  `research.tcss` through the cue law. Eyes on the mid-reveal frame
  caught a naked record plate floating over the card file before the
  demo pulled it — a plate now exists on the desk only while it
  carries a record.
- **The teletype surface** — some windows print their data instead of
  painting it: `surfaces.py::Teletype`, a reusable paced line-printer —
  lines land one per beat (`TELETYPE_CADENCE` in the laws), an amber
  block cursor rides the print head and exists only while the machine
  prints, and an interrupted print keeps exactly the lines that landed.
  The surface dramatizes arrival only: already-known context is handed
  in as a lead and renders instantly. The research page's READ station
  adopts it for live and demo transits both (the demo prints at a
  deliberate watched pace). Eyes on the mid-print frame caught the
  working column's ▲ marker landing inside the rail legend — markers
  and legend never share cells now; the legend stands down while a
  marker is up.
- **Every page opens** — one hero per page, all through `laws.Reveal`:
  the hall's plaques surface one by one as the door parts; the library's
  rack cascades in behind the door (four fast batches, the count
  climbing, sort and cursor seating last — any hand on the room lands
  it instantly, keeping the cursor's place); the intake line lights
  station by station in work order; the compare instrument warms while
  plates keep their own arrival choreography; the market's price scale
  draws itself left to right with the avg needle, endpoints, and the
  $150 cut landing last. Nothing else moves on open — the balance law.
  The compositor law grew a clause the hard way: **every segment
  carries a style** — Textual's opacity filter dies on unstyled
  segments, so every drawn instrument now styles its pads and blanks.
- The capture pipeline is `tests/capture_pages.py` (exhibits export as
  `page-<name>.svg`, all six pages, the hall included; the old
  `room-*.svg` frames retired with the README repointed); the shell
  suite is `tests/test_tui_shell.py` — fifteen proofs including the
  source↔door mapping, the hall's doors, theme/stylesheet laws, the
  Reveal contract, the map's power-on/idle/spotlight, the teletype,
  and one-hero-per-page. Eyes-on review caught and fixed what no test
  flagged: a wrapped door description, an orphaned generation-window
  line, the masthead reading VAULT twice, a two-tone hover lift, a
  naked plate over the card file, and the working marker colliding
  with the rail legend.
- **The Reveal runner is a sequence, not timers** — learned in the
  proof pass: Textual one-shot timers skip a firing they missed
  (`skip=True`, no override from `set_timer`), so under load a
  timer-driven cascade silently lost its tail. The performance now
  runs as one sequenced worker — late under load, never less — and a
  cascade landed by the hand follows the knife under the cursor, not
  the row number. Version stamps bumped to 0.11.0 (pyproject,
  bundled DB).

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
- **`knivves research`** — the CLI pass: concurrent docket reads with
  live "researching the unknowns" progress, then a summary naming every
  fill by kind, every unreachable record with its reason, every fetch
  failure, and every rulebook hit (reported only — the flag stays the
  user's). `--dry-run` prints the docket and the unreachable shelf with
  zero fetches and zero writes; `--id` narrows the pass to one record.
  Interrupting writes nothing; a completed pass backs up first.
- **The unknowns, visible** — the home page counts `N unresearched` in
  its stats line and lists the `knivves research` door;
  `knivves list --gaps` filters to records with open gaps
  (`--no-gaps` inverts to only complete ones).
- **Door 5 — Research** — the desk as a room, built around the
  **UNKNOWNS MAP**: the entire database drawn as a dot-matrix field,
  one column per knife, one row per fact (STEEL / LOCK / OPEN / LEN /
  PRICE / STOCK / TITLE). Lit dot = the vault knows; dark socket = a
  hole in a record — the collection's ignorance visible in one glance,
  with the machined completeness gauge riding on top and a scale rail
  underneath. During a live pass the map fills **live**: each learned
  fact burns an **amber wake**, the working column carries a ▲ marker,
  so the screen shows exactly what this pass discovered versus what
  was already known. The docket is a **card file** — each incomplete
  record a tab carrying its own punch-row (its map column in
  miniature), the active card marked with an amber edge bar — over the
  unreachable shelf with every reason said. `s` works the file for
  real: PULL, READ (the listing learned fact by fact), STAMP (only
  empty fields land), the map lighting as each fact does. `r` replays
  a no-network demo; the map never lies during it — nothing written,
  nothing lights. A fault reads on the plate in FAIL and the pass
  moves on; the database is backed up and saved once at the end, only
  if something filled.
- **The plate carries its incompleteness** — a record with open gaps
  shows `gaps  N unresearched` in accent on its plate, in every room
  it travels to (Library, Compare Models): the object knows what it
  doesn't know, and door 5 is where it gets filled.
- **The bench rebuilt as hardware** — the calipers are now the
  instrument the room is named for: for each numeric fact one drawn
  **beam** holds both knives' values as jaws on a single shared scale,
  the jaws travel in from the rail ends and close onto the work
  (animated), and the Δ engraves in the amber span between the jaw
  tips. The cheaper price reads pass-green; the longer blade reads
  bright; a tight lane reads in whole dollars, never clipped digits.
  Categorical facts are **linkages** — ● joined on a match, ╳ broken
  on a differ, truncation marked with an honest ellipsis. An open jaw
  still says "incomparable — missing measurement". A pair already read
  settles instantly; only a new pair animates.
- **The forge rebuilt as hardware** — the legal screen is now a
  **seven-bolt lock**, the same bolts the vault door throws: one drawn
  bolt per rule, each retracting into its housing as its rule clears
  (animated, cell by cell), the housing nub lighting pass-green; a hit
  throws the bolt full-red with the matched word on the header and the
  lock stays shut. EXTRACT is now a **tape reader**: the raw listing
  title runs as a tape and the exact substrings the parser pulled
  fields from light in amber underline as they stamp — a field learned
  off-tape stays unlit, because the tape never lies. Both transits
  (live and demo) drive the same hardware; the file intake's plan
  screen is untouched.
- **Compositor law, learned the hard way** — a `render_line` strip
  shorter than the widget's width shifts every widget sharing that
  screen line; declaring a false cell length hides it from
  `adjust_cell_length`. All drawn widgets (lock, tape, unknowns map)
  now pad every strip to exact width. Found by eyes on captured
  frames — no test flagged it.
- **The frame-capture pipeline is committed** —
  `tests/capture_rooms.py` drives every room to its demonstrative
  state headlessly and exports the `docs/media/room-*.svg` exhibits;
  all five refreshed (the old frames predated the room renames and
  the one-palette pass). Eyes-on review of the new frames caught and
  fixed what no test flagged: docket rows wrapped an orphaned
  "gap(s)" onto a second line (now one line, `×N`), the station name
  read twice, and plate titles sliced mid-SKU (now wrap whole).
  Version stamps bumped to 0.10.0 (pyproject, bundled DB).

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
