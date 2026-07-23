<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["004 — v0.8.0 (2026-07-23) — THE INTAKE DOCK", "005 — v0.9.0 (2026-07-23) — PLAIN WORDS ON THE DOORS"] },
     "STATUS": "CLOSED (2026-07-23) — archived to docs/closed/ · executed and shipped in v0.8.0, deliverables amended through v0.9.0",
     "NOTE": "Canon below is the plan AS AUTHORED. Post-execution changes are annotated inline at the tasks they supersede. Companion spec: docs/closed/2026-07-23-ingestion-freshness-design.md (closed the same way)." } -->

# Ingestion & Freshness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Markdown ingestion (`knivves add file.md`), NEW freshness under a three-generation cache (`knivves update`, `knivves new`), SectionID vocabulary (replacing `tag`, alias kept), and BuyList priority displays (CLI + Vault).

**Architecture:** Three new pure backend modules (`ingest.py` lexer/parser/planner, `generations.py` freshness math, `buylist.py` ordering) feed the existing store/models layer; CLI and Vault are thin presentation over them. Parsing is tolerant-by-design: diagnostics and repairs are data, never exceptions.

**Tech Stack:** Python 3.10+, typer/click, rich, textual. No new dependencies. Tests are plain-python runners (repo convention — no pytest).

## Global Constraints

- SLI = line of exactly 31 `-`; other dash runs ≥3 accepted with warning diagnostic.
- Storage compatibility: sections live in the existing `user_tags` field; slugs use `lowercase_underscore`.
- NEW rule: `generation - added_generation < keep_generations`; unstamped records are never NEW; keep clamped to 1..3, default 1.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "005 — v0.9.0", "bullet": "Freshness ages by batches" },
     "CHANGES": ["SUPERSEDED RULE: shipped rule is `0 <= generation - added_generation <= keep_generations` — the sealed batch survives its own update. Empty updates hold the line (generations.advance returns None); `knivves update --force` ages the window. Commits 57441fb, 31aec84."] } -->
- All DB writes go through backup + atomic save (existing store paths).
- Test runners must work as `python tests/test_X.py` (no pytest) and stay pytest-compatible (`test_*` functions).
- Version bump to 0.8.0 (pyproject + bundled DB `version`).
- Real knife additions are ingested ONLY in Task 9, after all features pass.

---

### Task 1: `knivves/generations.py` — freshness math

**Files:** Create `knivves/generations.py`, `tests/test_generations.py`. Modify `knivves/store.py` (stamp on add).

**Interfaces (Produces):**
- `meta(db) -> dict` — returns/creates `db["updates"] = {"generation": 1, "keep_generations": 1, "history": []}`.
- `stamp_new(db, record) -> None` — sets `added_generation`, `date_added` (ISO), `new: True`.
- `retag(db) -> tuple[list[str], list[str]]` — recompute every record's `new`; returns (now_new_ids, aged_out_ids vs previous flags).
- `advance(db, note: str = "") -> dict` — generation += 1, retag, append history entry `{generation, date, added, now_new, aged_out}`; returns that entry.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "005 — v0.9.0", "bullet": "Freshness ages by batches" },
     "CHANGES": ["SUPERSEDED SIGNATURE: `advance(db, note='', *, force=False) -> dict | None` — returns None (line holds, no history entry) when nothing was filed since the last update and force is False."] } -->
- `set_keep(db, keep: int) -> int` — clamp 1..3, store, retag, return effective keep.
- `is_new(record, meta_block) -> bool` — pure rule.
- `store.add_knife` stamps every new record via `stamp_new`.

**Steps:**
- [ ] Failing tests: fresh add is NEW immediately; one advance ages it out at keep=1; survives 2 advances at keep=3 and dies on the 3rd; unstamped legacy record never NEW; set_keep clamps 0→1, 9→3; history grows; add_knife stamps.
- [ ] Run `python tests/test_generations.py` → NameError/ImportError.
- [ ] Implement module; wire `store.add_knife`.
- [ ] Tests pass. Commit `feat: three-generation NEW freshness core`.

### Task 2: `knivves/ingest.py` — lexer, parser, planner

**Files:** Create `knivves/ingest.py`, `tests/test_ingest.py`, `tests/fixtures/knife-additions.md` (mirrors TODO.md real sections, malformed lines kept verbatim).

**Interfaces (Produces):**
- `lex(text) -> list[Token]`, Token = `(line_no, kind, text)`, kinds: `SLI H1 SECTION ENTRY BLANK PROSE` (fenced blocks skipped).
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "004 — v0.8.0", "bullet": "knivves add <file.md> — markdown ingestion" },
     "CHANGES": ["EXTENDED AFTER AUTHORING: Token gained an `indent` field and an ANNOTATION kind — bullet-form `- // Name *Tag*` lines are inline annotations scoped to their indented children only (commit f4940f8). Kansept seeded into KNOWN_BRANDS."] } -->
- `parse_document(text) -> Document` — `Document(title, sections: list[Section], diagnostics: list[Diagnostic])`; `Section(name, slug, kind: KNIVES|SOURCES|BUYLIST, tags, notes, entries)`; `Entry(label, url, line_no, brand, model, sku, tags, source_name, repairs)`; `Diagnostic(line, severity, message)`.
- `parse_title(label, known_brands) -> (brand, model, sku)`.
- `build_plan(doc, db) -> IngestPlan` — `new_records` (full knife dicts, unstamped), `merges` (`(knife_id, add_sections, buy_priority)`), `sources`, `buylist_ids` (ordered), `diagnostics`, `skipped` (in-file duplicates).
- `apply_plan(plan, db) -> IngestReport` — stamps via generations, writes sections/buy_list/sources blocks; counts added/merged/sources/duplicates.
- `RETAILERS` domain map: bladescanada.com, houseofknives.ca, canadiantire.ca, kershawcanada.com.

**Test cases (all from TODO.md real data):** exact-31 SLI vs 12-dash warning; SectionID grammar diagnostics (blank-above, missing blank after); `*Tag*` extraction on section and inline `//` annotation (`Canadian Tire *NewSource*, *AffordableSource*` applies to following entries only); swapped `[url](label)` (Duoz BG65F); split URL continuation (Psyop A2204); `[label]<url()>` angle form (Batwing JM10S-BG-14); `(BG64C)`→`- BG64C` normalization; `#175-2469-8` Canadian Tire ref; `TODO:GET-KNIFE-DATA` label → URL-slug title (Cobber BG68A); buylist section detected from `BUY LIST DESCENDING PRIORITY`; sources sections produce no knives; in-file dupes (S25104-3 ×3) collapse; DB-merge by SKU and by URL; fenced example block ignored.

- [ ] Write failing tests (grouped runner `main()`), run → ImportError.
- [ ] Implement lexer → tests for lex pass. Commit `feat: ingestion lexer`.
- [ ] Implement parser+repairs → parse tests pass. Commit `feat: ingestion parser with repair pipeline`.
- [ ] Implement planner/apply → all pass. Commit `feat: ingestion planner and apply`.

### Task 3: `knivves/buylist.py` — priority model

**Files:** Create `knivves/buylist.py`, `tests/test_buylist.py`.

**Interfaces (Produces):**
- `set_buylist(db, ids: list[str]) -> None` — file order is truth; writes `db["buy_list"] = {"updated", "items": [{"id", "priority"}]}`, materializes `buy_priority` + `buy_list` section on members, clears stale `buy_priority` from ex-members.
- `buylist_views(db) -> list[tuple[int, KnifeView]]` — ordered, skips missing ids.
- `cumulative(views) -> list[float | None]` — running CAD total (None-price rows carry previous total).

- [ ] Failing tests: ordering, re-set replaces priorities and clears stale, cumulative math with a None price in the middle.
- [ ] Implement; pass; commit `feat: buylist priority model`.

### Task 4: models/store surface

**Files:** Modify `knivves/models.py` (`sections` alias property, `is_new`, `buy_priority`, haystack gains `new`/`buylist` markers, `flat()` gains columns), `knivves/store.py` (already stamped in Task 1). Tests appended to `tests/test_generations.py`/`test_buylist.py`.

- [ ] Failing tests → implement → pass. Commit `feat: KnifeView freshness and section surface`.

### Task 5: CLI commands

**Files:** Modify `knivves/cli.py`, `knivves/render.py`. Create `tests/test_cli_features.py` (typer CliRunner; redirect `store.APP_DIR/USER_DB/BACKUP_DIR` to a temp dir per test).

**Produces:**
- `add` gains optional positional `source` (path to `.md`) → ingestion flow with `--dry-run`, `--yes`; rich report (sections, added/merged, repairs, diagnostics).
- `update [--gens N] [--note TEXT] [--survey]` → advance + report renderer.
- `new` lists NEW; `-oneg/-twog/-threeg/--gens N` set keep; `--status` cache state.
- `list` gains `--section/-section` (merged with `--tag`) and `--new/-new`; BuyList window above table when non-empty (suppressed by `--no-summary`).
- `section` sub-app (canonical: list/add/remove) with `tag` kept as alias; `sections` top-level alias; `buylist` command with cumulative CAD.
- `render.py`: NEW chip in tables, `buylist_panel`, `ingest_report`, `update_report`, summary cards NEW count.

- [ ] Failing CLI tests (add md dry-run + real, update ages NEW, new -oneg, list -new, section add, buylist) → implement → pass. Commit `feat: ingestion/freshness/section/buylist CLI`.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["005 — v0.9.0 (--survey → --prices)", "005 — v0.9.0 (A real home page)", "005 — v0.9.0 (One palette everywhere)"] },
     "CHANGES": ["SUPERSEDED FLAG: `update --survey` shipped, then renamed to `--prices` / `-prices`; the market read is concurrent with a rich progress bar; first prices are summary-counted, not streamed; observations go through ledger.observe + retag_affordable.",
                 "SUPERSEDED OUTPUT: the ingest report became rule header + SectionID tree + proportional outcome meter + ★ filed panel (commit 6c9d8fa).",
                 "ADDED AFTER AUTHORING: bare `knivves` opens a home page (render.home_page); the classic interactive browser moved to `knivves browse`; the classic CLI palette was normalized to the vault house laws; ★new is FRESH mint at end-of-Brand / start-of-Model (models.new_brands)."] } -->

### Task 6: Vault surfaces

**Files:** Create `knivves/vault/reserve.py` (The Reserve — BuyList panel). Modify `knivves/vault/rack.py` (NEW chip in tags cell, `y` binding, tip), `knivves/vault/masthead.py` (NEW count stat), `knivves/vault/vault.tcss`.

- [ ] Extend `tests/test_vault_shell.py`: NEW chip renders for a stamped record; `y` opens/closes Reserve. Run headless suite. Commit `feat: vault NEW chips and The Reserve buylist panel`.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["005 — v0.9.0 (Rooms renamed)", "005 — v0.9.0 (Import Knives takes ingestion files)"] },
     "CHANGES": ["RENAMED AFTER AUTHORING: room display names normalized — Library (The Rack), Import Knives (The Forge Line), Compare Models (The Bench), Market Prices (The Ledger); screen ids/modules unchanged.",
                 "ADDED AFTER AUTHORING: Import Knives accepts ingestion .md paths in its intake slot (forge.file_transit) — sections at EXTRACT, plan at LEGAL SCREEN, batch files ★new at VAULT; headless suite gained test_file_import_transit.",
                 "SUPERSEDED CHIP: ★new left the Tags column — end of Brand marks a new maker, start of Model marks a new blade, in laws.FRESH mint."] } -->

### Task 7: Docs & version

**Files:** Modify `pyproject.toml` (0.8.0), `knivves/data/knives.json` (`version`), `README.md` (ingestion format contract, update/new/section/buylist), `docs/CHANGELOG.md`.

- [ ] Full test suite green. Commit `docs: v0.8.0 ingestion ecosystem`.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "005 — v0.9.0" },
     "CHANGES": ["VERSION MOVED ON: shipped as v0.8.0, then bumped to v0.9.0 with the room normalization / home page / --prices release (commit 9611e3a)."] } -->

### Task 8: Full-suite verification

- [ ] `python tests/test_generations.py && python tests/test_ingest.py && python tests/test_buylist.py && python tests/test_cli_features.py && python tests/test_vault_shell.py` all green. Fix anything. Commit fixes.

### Task 9: Real data ingestion (acceptance)

**Files:** Create `additions/2026-07-23-knife-additions.md` from TODO.md's real sections (BUY LIST DESCENDING PRIORITY, MAIN SOURCES, NEW SOURCES, UNSORTED ×2, TODO:GET-KNIFE-DATA entries — malformed lines verbatim; the fenced ForCamping example excluded).

- [ ] `knivves add additions/… --dry-run` against a copy — review report.
- [ ] Ingest into the bundled repo DB (KNIVVES_DB→repo file) and the live `~/.knivves/knives.json` (both, kept in sync; live backed up first).
- [ ] Verify: `knivves new`, `knivves buylist`, `knivves list -new`, doctor clean. Commit `data: ingest 2026-07-23 knife additions`.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "004/005 context — see also memory: knivves-ingestion-semantics" },
     "CHANGES": ["TASK 9 SUPERSEDED — THIS TASK WAS A MISTAKE AND WAS REVERTED. The knife additions were reserved so the USER could run the first real ingestion with their own file against a clean database; the agent-side ingestion spoiled that test. Both DB copies were reset to the pre-ingestion 166 (commit f21a3cf; live survey prices/history preserved), and the user then ran `knivves add` on their own ledger (now `import-knivves.md`) successfully.",
                 "STANDING RULES: (1) ingestion .md files are one-shot intake batches — never master ledgers or sync sources; the JSON database is the source of truth after intake. (2) Data a user reserves 'for testing' is theirs to consume — an agent must never pre-run the user's test. `additions/*.md` remain as format documentation and fixtures only."] } -->
