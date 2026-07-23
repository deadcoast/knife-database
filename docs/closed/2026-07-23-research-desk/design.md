<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["006 — v0.10.0 (2026-07-23) — THE RESEARCH DESK"] },
     "STATUS": "CLOSED (2026-07-23) — archived to docs/closed/ · every REQ shipped with its named acceptance test green",
     "NOTE": "Canon below is the doc AS AUTHORED/WRITTEN. Drift since is annotated inline. Do not treat unannotated details as current without checking docs/CHANGELOG.md." } -->
<!-- { "DEV_SPEC": { "case": "2026-07-23-research-desk", "doc": "DS-1 design", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-2": "requirements.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# The Research Desk — Design (DS-1)

Case: `2026-07-23-research-desk` · Opened: 2026-07-23 · Target: v0.10.0
Hub: [requirements.md](requirements.md) · Tasks: [TODO.md](TODO.md)

## Scope

v0.9.0 left the vault knowing exactly what it doesn't know: ingestion
stamps `TODO:` placeholder titles from URL slugs, `import-knivves.md`
carries 40+ `TODO:GET-KNIFE-DATA` entries, and Compare Models reads
"incomparable — missing measurement" wherever a field is absent. This
case builds the answer: **the vault researches its own unknowns**. A
pure audit names every gap in every record; a deterministic docket
orders what to research first; a completion pass pulls each record's
own listing and fills ONLY what is empty; and a fifth room — plain
words on the door: **Research** — makes the work visible as plates
traveling a desk. In play: a new `knivves/research.py` backend,
`knivves/cli.py` (new `research` command, `list --gaps`, home-page
readout), a new `knivves/vault/desk.py` room with `app.py` wiring,
and the test suites. Untouched: `ingest.py`, `generations.py`,
`buylist.py`, the store schema (additive fields only), and the
existing rooms beyond shared chrome.

The bar (J-SPACE): a database that visibly does its own research — a
docket of incomplete plates worked one by one through a desk, fields
stamping as they are learned, the completion meter rising — is a thing
the Textual gallery does not have. Self-completing data with object
permanence is the case's featured-bar claim; if a station on the desk
would not impress, it is not done.

## Tech stack & context

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Layer | What | Where |
|---|---|---|
| TUI | Textual — rooms behind the vault door, house laws, motion law | `knivves/vault/` (`app.py`, `laws.py`, `masthead.py`, `door.py`) |
| CLI | typer + rich, palette mirrored from the vault | `knivves/cli.py`, `knivves/render.py` |
| data | JSON DB, atomic writes, backups, live DB at `~/.knivves/` | `knivves/store.py`, `knivves/models.py` |
| research | listing parser (2 supported hosts) + NEW pure completion logic | `knivves/scrape.py`, NEW `knivves/research.py` |
| pricing | price history, movers, the $150 affordable rule | `knivves/ledger.py` |

Context an agent needs before touching anything: the house laws are
code ([laws.py](../../../knivves/vault/laws.py)) — one palette, one
`LABEL value` field grammar, one motion law (objects travel, never
teleport, no fades). The prohibited-mechanism rulebook lives in the
database itself (`workflow_rules.canadian_online_retailer_rule.
only_reject_or_fail_if_clear_prohibited_mechanism`, read today by
`knivves/vault/forge.py::ForgeScreen._rules`). Prior closed cases that
bear on this one: the v0.8.0 ingestion/freshness spec and plan —
[design](../../closed/2026-07-23-ingestion-freshness-design.md),
[plan](../../closed/2026-07-23-ingestion-freshness-plan.md) — whose
repair-report posture (every fix named, nothing silent) this case
inherits for research.

## Design features

### The unknowns audit — the vault names its gaps

A record's incompleteness becomes a first-class, testable fact instead
of a rendering detail. One pure function reads a record and returns its
gaps: placeholder titles (`TODO`-derived model names), `Unknown`/nullish
mechanism fields (per `models.NULLISH`), missing prices, absent listing
titles. The audit is the single source of truth every other feature
consumes — CLI filters, the docket, the room, the meter.

#### REQ-RES-1 — gap audit

- **WHAT**: `audit_record(record)` returns the exact list of gaps
  (field, kind, fillable-from which retailer URL, host supported or
  not); `audit_database(db)` aggregates per-record and vault-wide
  completeness counts. Pure functions, no network, no writes.
- **WHY**: `TODO:GET-KNIFE-DATA` entries and slug-derived titles exist
  in the production ledgers; the Bench renders "incomparable" for
  missing measurements — the vault must know its unknowns before it can
  research them.
- **BINDS**: `knivves/research.py::audit_record` ·
  `knivves/research.py::audit_database` · reads `knivves/models.py::NULLISH`,
  `knivves/models.py::KnifeView`
- **ACCEPTANCE**: `tests/test_research.py::test_audit_flags_gaps` — a
  record with a TODO title, Unknown steel, and no price yields exactly
  those gaps; a complete record yields none.

#### REQ-RES-2 — the docket

- **WHAT**: `build_docket(knives)` orders auditable records
  deterministically: BuyList rank first (`buy_priority` ascending),
  then ★new, then most-gaps-first, then id. Records with no
  supported-host listing URL (`scrape.is_supported`) are returned in a
  separate **unreachable** shelf — listed honestly, never dropped.
- **WHY**: research effort should land on the knives the user wants
  next (The Reserve) before the archive; honesty law — a record that
  cannot be researched is said so, not skipped silently.
- **BINDS**: `knivves/research.py::build_docket` ·
  `knivves/scrape.py::is_supported` · reads `knivves/models.py::KnifeView.buy_priority`,
  `KnifeView.is_new`
- **ACCEPTANCE**: `tests/test_research.py::test_docket_orders_buylist_first` —
  given mixed records, docket order is buy-rank → new → gap-count, and
  the unsupported-URL record appears only on the unreachable shelf.

### The completion pass — fill only what is empty

The pass pulls a docket record's own listing (`scrape.fetch_listing`)
and merges it into the record under one law: **only empty fields are
written, user data is never overwritten**. Every fill is recorded with
provenance; a first price seeds history quietly (the v0.9.0 law: first
prices are counted, never streamed); mechanism text learned by the pass
is re-screened against the database's own rulebook — a hit is
**reported, never auto-written**: the flag stays the user's decision.

#### REQ-RES-3 — fill-only-empty merge with provenance

- **WHAT**: `research_record(record, listing)` fills only
  nullish/absent fields (title, brand/model from placeholder, steel,
  lock, opening, blade length, price, availability), stamps provenance
  into an additive `record["research"]` sub-dict (`last_pass`,
  `filled: {field: host}`), and returns a per-field report. A filled
  first price also runs `ledger.seed_history` + `ledger.retag_affordable`.
  Rulebook re-screen of learned mechanism text reports hits in the
  return value; `clear_prohibited_mechanism_found` is never written by
  the pass. `research_status` semantics stay user-owned — untouched.
- **WHY**: the DB is truth after intake (standing rule) — research must
  enrich it, never fight the user for it; the repair-report posture
  from v0.8.0 ingest applies: every change named, nothing silent.
- **BINDS**: `knivves/research.py::research_record` ·
  `knivves/scrape.py::fetch_listing` · `knivves/ledger.py::seed_history` ·
  `knivves/ledger.py::retag_affordable`
- **ACCEPTANCE**: `tests/test_research.py::test_fill_never_overwrites` —
  a record with user-entered steel keeps it when the listing disagrees;
  and `tests/test_research.py::test_rulebook_hit_reported_not_written` —
  a listing whose lock text matches a rulebook term yields a reported
  hit with the record's flag unchanged.

#### REQ-RES-4 — `knivves research` (CLI pass)

- **WHAT**: a `research` command runs the docket concurrently (the
  `update --prices` machinery pattern) with live progress reading
  "researching the unknowns", then a summary: records completed, fields
  filled by kind, unreachable count, rulebook hits. `--dry-run`
  previews the full plan without network writes; `--id <knife-id>`
  researches one record.
- **WHY**: the pass must be runnable headless and scriptable, exactly
  like `update`/`add` — the vault room is the show, the CLI is the tool.
- **BINDS**: `knivves/cli.py::research` (new `@app.command()`) ·
  `knivves/research.py::run_research` (orchestrator, injectable fetch
  for tests)
- **ACCEPTANCE**: `tests/test_cli_features.py::test_research_dry_run_no_network` —
  dry-run over a throwaway DB prints the docket plan and summary with
  zero network calls (fetch injected), DB byte-identical after.

### The Research room — the desk where the work is visible

Door **5 — Research** (plain words on the doors). Left: the docket as
a rack of incomplete plates, each carrying its gap-count chip. The
worked plate travels the desk stations — **PULL → READ → STAMP** — in
the Import-line grammar: fields flash amber as they are learned and
stamp onto the plate; the completion meter on the masthead readout
rises as gaps close; unreachable plates sit on their own shelf saying
why. `s` runs the live pass; `r` replays a deterministic no-network
demo transit (the forge's replay law). Motion is travel; nothing fades.

#### REQ-RES-5 — DeskScreen

- **WHAT**: a new `DeskScreen` registered as room `"desk"` with binding
  `"5"`, palette command, masthead per-room state readout (docket
  depth · pass state · meter), live pass wired to `run_research`, and
  the `r` demo transit.
- **WHY**: the featured-bar claim of this case — self-completing data,
  watched — lives or dies in this room.
- **BINDS**: NEW `knivves/vault/desk.py::DeskScreen` ·
  `knivves/vault/app.py::KnivvesVault.SCREENS` ·
  `knivves/vault/app.py::KnivvesVault.BINDINGS` ·
  `knivves/vault/app.py::KnivvesVault.get_system_commands` ·
  `knivves/vault/vault.tcss`
- **ACCEPTANCE**: `tests/test_vault_shell.py::test_desk_demo_transit` —
  headless Pilot on a throwaway DB: room 5 opens, demo transit stamps
  learned fields, docket count decreases, layout laws hold.

<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "006 — v0.10.0", "bullet": "Door 5 — Research" },
     "CHANGES": ["ADDED AFTER AUTHORING: the meter shipped as a dedicated drawn CompletenessMeter render_line widget (gradient-lit, eighth-block tip — the gauges vocabulary) riding above the line, in addition to the masthead readout named in WHAT; masthead.py itself needed no modification (set_context sufficed)."] } -->

### Completeness readouts — the unknowns visible everywhere

#### REQ-RES-6 — home, list, and Library readouts

- **WHAT**: the home page gains a completeness line (records complete /
  gaps outstanding, the Research door listed with its command);
  `knivves list --gaps` filters to records with gaps; the Library
  plate shows an `UNRESEARCHED n` chip sourced from the audit.
- **WHY**: v0.9.0's home page is the front door — the vault's unknowns
  belong on it next to the ★new window; one glance answers "is my data
  whole".
- **BINDS**: `knivves/cli.py::home` · `knivves/cli.py::list` (new
  `--gaps` option) · `knivves/vault/plate.py` (chip) ·
  `knivves/research.py::audit_database`
- **ACCEPTANCE**: `tests/test_cli_features.py::test_home_completeness_line`
  and `tests/test_cli_features.py::test_list_gaps_filter` — home prints
  the completeness line; `--gaps` returns exactly the incomplete records.

<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "006 — v0.10.0", "bullet": "The plate carries its incompleteness" },
     "CHANGES": ["SUPERSEDED: the 'UNRESEARCHED n chip' shipped in the field grammar instead of as a chip element — a `gaps  N unresearched` row in accent rendered by laws.field on the Plate, carried into every room the object travels (vault/plate.py::Plate.set_knife, commit 396c23d)."] } -->

## Cross-cutting constraints

- House laws (`knivves/vault/laws.py`): steel text, machined edges,
  single amber accent, mint ★new — no new colors, any room.
- One field grammar: `LABEL value` — desk stations, chips, summaries.
- One motion law: objects travel; no fades, no teleports.
- Fill-only-empty: user-entered data is NEVER overwritten by research.
- Honest gaps: unreachable/unparseable is recorded and said, never
  guessed, never silently skipped.
- Rulebook hits are reported, never auto-written — the flag is the
  user's decision.
- All tests run offline: network isolated behind `fetch_listing`,
  injected in tests; fixtures lifted from real listings.
- Live DB (`~/.knivves/`) is richer than bundled — never overwrite;
  the pass writes through `store.save_database` (atomic + backups).
- Reserved data: `additions/2026-07-23-knife-additions-2.md` is the
  user's own ingestion test — read nothing, consume nothing.
- Windows-safe output (UTF-8 posture as shipped in v0.7.0+).
- Linter coexistence: tables authored minimally spaced; markdownlint
  realignment on disk is normal operation.

## Out of scope / deferred

- **Ingesting `import-knivves.md` or any additions file** — intake is
  the user's action; this case builds capability, it does not consume
  the user's batches.
- **New retailer parsers** — the two supported hosts stay the parse
  surface; other hosts land on the unreachable shelf honestly.
- **Auto-writing `clear_prohibited_mechanism_found` or
  `research_status`** — both stay user-owned decisions.
- **Web/front-end anything** — the terminal is the medium (standing
  decision from the design phase).
- **Scheduled/background research** — the pass runs when invoked.
