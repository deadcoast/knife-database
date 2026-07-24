<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["004 — v0.8.0 (2026-07-23) — THE INTAKE DOCK", "005 — v0.9.0 (2026-07-23) — PLAIN WORDS ON THE DOORS"] },
     "STATUS": "CLOSED (2026-07-23) — archived to docs/closed/ · shipped in v0.8.0, amended through v0.9.0",
     "NOTE": "The canon below is the design AS AUTHORED. Post-authoring changes are annotated inline with CHANGELOG_REFERENCE comments at the exact sections they supersede. Do not treat unannotated details as current without checking docs/CHANGELOG.md." } -->

# Ingestion & Freshness — Design

Date: 2026-07-23 · Target release: v0.8.0 · Source of requirements: `TODO.md` (user-authored spec)

## Goal

Give knivves a complete intake ecosystem: a markdown ingestion file format
(the user writes links, the CLI ingests them), a freshness model (`NEW` under
a three-generation cache governed by `knivves update`), the `SectionID`
vocabulary (formally replacing `tag`, which stays as an alias), and a BuyList
priority display on the vault and list pages.

## Vocabulary

| Term | Meaning |
|---|---|
| **SLI** | Section Line Indicator — a line of exactly 31 `-` characters. |
| **SectionID** | The application's formal word for a knife's group identifiers (filters, grouping). Replaces `tag` in UI language; `tag` remains a quality-of-life alias. Storage stays in the existing `user_tags` field for full backward compatibility. |
| **NEW** | Freshness state. A knife is NEW while `generation - added_generation < keep_generations`. |
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "005 — v0.9.0", "bullet": "Freshness ages by batches" },
     "CHANGES": ["SUPERSEDED RULE: is_new is now `0 <= generation - added_generation <= keep_generations` — the batch SURVIVES the update that seals it (the original `<` rule aged out the very batch the first update tagged; fixed in commit 57441fb).",
                 "An update that files nothing HOLDS the generation line (advance returns None); `knivves update --force` ages the window deliberately (commit 31aec84)."] } -->
| **Generation** | A counter advanced by `knivves update`. Additions stamp the open generation. |
| **BuyList** | Ordered acquisition priority list, sourced from a BuyList section in an ingestion file. |

## 1. Markdown ingestion format (the contract)

```markdown
# FILE TITLE

-------------------------------
// SectionID *OptionalTag*, *AnotherTag*

-------------------------------

> optional prose note for the section

- [Brand Model, Steel, Handle, SKU](https://retailer/product)
// Inline Source Annotation *NewSource*, *AffordableSource*
- [Another Knife - SKU](https://retailer/other)

-------------------------------
```

Grammar rules (each violation is a *diagnostic warning*, never a parse abort):

- SLI is exactly 31 dashes. Other standalone dash runs (≥3) are accepted as
  SLI with a warning naming the actual count.
- The file title is the only `#` heading, at the top. All other headings are
  `// SectionID` lines.
- A SectionID line has an SLI directly above it (no blank line between), a
  blank line after it, then an SLI closing the heading.
- `*Word*` markers on a SectionID line attach tags to every entry in that
  section.
- A `//` line *inside* a section body (not SLI-fenced) is an **inline
  annotation**: it names a source and/or attaches `*Tag*` markers to the
  entries that follow it, until the section ends.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "004 — v0.8.0", "bullet": "knivves add <file.md> — markdown ingestion" },
     "CHANGES": ["ADDED AFTER AUTHORING: bullet-form annotations `- // Name *Tag*` are also recognized, and scope ONLY to their indented child entries (a sibling at the same or shallower indent closes the annotation). Bare `//` annotations keep the rest-of-section scope described above. Added in commit f4940f8 for the user's evolved ledger format."] } -->
- Fenced code blocks (```` ``` ````) are example material and are skipped
  entirely (with a note).

### Entry lexing and repair

Entries are `- [label](url)` list items. The lexer/parser is
tolerant-by-design and records every repair it makes:

1. **Continuation join** — a link whose URL was split across lines (unbalanced
   brackets) absorbs following lines until balanced.
2. **Swapped link** — `[https://…](Title)` is recognized and swapped.
3. **Angle form** — `[Title]<https://…()>` and `(<https://…>)` variants are
   unwrapped; stray `<>`/`()` stripped from URLs.
4. **Reference normalization** — trailing `(SKU)` and `#SKU` in labels are
   normalized to dash separation (`Title - SKU`), per the REF2 rule.
5. **URL-derived titles** — labels that are TODO markers (`TODO:GET-KNIFE-DATA`)
   or raw URLs get a display title derived from the URL slug.

### Title → record parsing

`Brand`, `Model`, `SKU` are extracted from labels using: a known-brand prefix
table (seeded + learned from the live DB), SKU detection (trailing `, SKU`,
` - SKU`, `(SKU)`, `#SKU`; token must contain a digit), and existing DB model
convention `Model … (SKU)`.

### Section classification

- Normalized name contains `buylist` / (`buy` + `list`) → **BUYLIST** (entry
  order = descending priority, 1 is most sought).
- Contains `source` → **SOURCES** (registered into a top-level `sources`
  block; no knife records are created).
- Otherwise → **KNIVES**.

### Dedupe & merge

Within a document: key = SKU, else normalized URL, else label slug. First
occurrence wins; later occurrences merge their sections/tags and the best
(lowest) buy priority. Against the DB: entries matching an existing knife (by
SKU in model/id, or by saved retailer URL) merge sections/buylist rank onto
the existing record instead of duplicating.

### Pipeline shape (pure, testable)

```
parse_document(text)  -> Document(title, sections, diagnostics)
build_plan(doc, db)   -> IngestPlan(new_records, merges, sources, buylist, diagnostics)
apply_plan(plan, db)  -> IngestReport(counts, repairs, diagnostics)
```

`knivves add file.md --dry-run` runs parse+plan and renders the report
without writing.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["005 — v0.9.0 (Import Knives takes ingestion files)", "005 — v0.9.0 (One palette everywhere)"] },
     "CHANGES": ["ADDED AFTER AUTHORING: the Vault's Import Knives room (formerly The Forge Line) also runs ingestion .md paths through its station line — sections at EXTRACT, plan at LEGAL SCREEN, batch files at VAULT (forge.file_transit).",
                 "The CLI report described here was later redesigned: rule header + SectionID tree + proportional outcome meter + ★ filed result panel (commit 6c9d8fa)."] } -->

## 2. Freshness: `update`, `new`, three-generation cache

DB top-level block:

```json
"updates": { "generation": 1, "keep_generations": 1, "history": [] }
```

- Every added knife is stamped `added_generation` (current open generation),
  `date_added`, and materialized `new: true`.
- `knivves update` advances the generation, re-materializes every knife's
  `new` flag (`generation - added_generation < keep_generations`; knives
  without a stamp are never NEW), appends a history entry, and reports:
  newly NEW, aged out, totals. `--survey` optionally re-scrapes live prices.
- `knivves new` lists NEW knives; `-oneg/-twog/-threeg` (and `--gens N`,
  clamped 1–3) set the cache depth and retag immediately.
- `knivves list -new/--new` filters NEW. NEW renders as an accent chip in CLI
  tables, the interactive browser, and the Vault rack; the masthead and
  summary cards count it.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["005 — v0.9.0 (Freshness ages by batches)", "005 — v0.9.0 (--survey → --prices)", "005 — v0.9.0 (One palette everywhere)"] },
     "CHANGES": ["SUPERSEDED: the is_new rule is `0 <= gen - added <= keep` — the sealed batch survives its own update; empty updates hold the line; `update --force` ages the window.",
                 "SUPERSEDED: the `--survey` flag is now `--prices` / `-prices`; progress reads 'reading market prices'; the read is concurrent (6 workers) with a live progress bar; first prices are counted in the summary, never streamed; observations go through ledger.observe (price_history) and retag_affordable — parity with the Market Prices room.",
                 "SUPERSEDED: NEW renders as ★new in the FRESH mint color (laws.FRESH #5fd3bc), not the amber accent — placed at the END of Brand (new maker, via models.new_brands) and the START of Model (new blade), aligned in the gutter."] } -->

## 3. SectionID command surface

- `knivves section …` — canonical sub-app (list/add/remove); `knivves tag …`
  stays, documented as the alias.
- `knivves list --section/-section X` — filter (merges with `--tag`).
- `knivves sections` — aggregate view (alias of `tags`).
- Section slugs are stored in `user_tags` using the existing
  `lowercase_underscore` convention.

## 4. BuyList

DB top-level block:

```json
"buy_list": { "updated": "2026-07-23", "items": [{ "id": "…", "priority": 1 }] }
```

- Ingesting a BUYLIST section replaces the ordering with the file's order
  (the file is the source of truth for priority); members gain the
  `buy_list` section and a materialized `buy_priority` on the record.
- `knivves buylist` — priority table with price and **cumulative CAD**
  (running acquisition cost of the top-N).
- `knivves list` shows a compact BuyList window above the table when the
  list is non-empty; the Vault rack gains **The Reserve** — a panel toggled
  with `y`, styled by the house laws, listing priorities with NEW chips.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "005 — v0.9.0", "bullet": "Rooms renamed" },
     "CHANGES": ["RENAMED AFTER AUTHORING: the room is now 'Library' (The Rack), alongside 'Import Knives' (The Forge Line), 'Compare Models' (The Bench), 'Market Prices' (The Ledger). The Reserve keeps its name and its `y` toggle; screen ids and modules (rack.py etc.) are unchanged."] } -->

## 5. Error handling

- Parser never throws on malformed input: diagnostics with line numbers,
  severities, and applied repairs are part of the report.
- All DB writes go through the existing backup-then-atomic-save path.
- Unknown retailers still ingest (URL kept in `source_input` and retailer
  entry omitted; research stays pending).

## 6. Testing

Plain-python runners (repo convention, no pytest):

- `tests/test_ingest.py` — lexer tokens, grammar diagnostics, every repair
  case from TODO.md (swapped link, split URL, angle form, `(REF)`/`#REF`),
  section classification, dedupe/merge, plan building against a fixture DB.
- `tests/test_generations.py` — stamp/advance/keep math, aging table across
  keep=1..3, legacy records never NEW.
- `tests/test_buylist.py` — ordering, merge, cumulative pricing.
- `tests/test_cli_features.py` — typer CliRunner: add file.md (dry-run and
  real), update, new, section alias, list filters, buylist.
- `tests/test_vault_shell.py` — extended: NEW chip present, Reserve toggles.
- Fixture: `tests/fixtures/knife-additions.md` mirroring the real TODO data
  (including its malformed lines, deliberately).

The real additions file (`additions/2026-07-23-knife-additions.md`) is
ingested only after all features pass — it is the acceptance test.
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "004/005 context — see also memory: knivves-ingestion-semantics" },
     "CHANGES": ["SUPERSEDED / CORRECTED INTENT: the agent-side 'acceptance ingestion' described here was WRONG and was reverted (both DB copies reset to the pre-ingestion 166; commit f21a3cf). The knives were reserved so the USER runs the true first ingestion with their own file — which they did, successfully, with their ledger (now `import-knivves.md`). The `additions/*.md` files remain in the repo as format documentation and fixtures only.",
                 "STANDING RULE: ingestion .md files are one-shot intake batches, never 'master ledgers' or sync sources; the JSON database is the source of truth after intake. Data a user reserves for testing must never be pre-consumed by an agent."] } -->
