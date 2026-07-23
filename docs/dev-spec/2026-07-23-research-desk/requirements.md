<!-- { "DEV_SPEC": { "case": "2026-07-23-research-desk", "doc": "DS-2 requirements", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-1": "design.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# The Research Desk — Requirements Hub (DS-2)

Case: `2026-07-23-research-desk` · The navigation hub: every document,
every requirement, every binding — one glance, one hop. **Read this
file first.**

## Document registry

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Doc | Role | Read it when |
|---|---|---|
| [design.md](design.md) | DS-1 — the design canon, REQ definitions | you need the WHY or the shape of a feature |
| [TODO.md](TODO.md) | DS-3 — module-scale tasks + checkpoint footer | you need what to do next |
| [../../CHANGELOG.md](../../CHANGELOG.md) | BUS-A living record | you need what is CURRENTLY true |
| `knivves/research.py` (NEW) | audit, docket, fill-only-empty merge, orchestrator | the pure backend of this case |
| `knivves/cli.py` | `research` command, `list --gaps`, home readout | the CLI surfaces |
| `knivves/vault/desk.py` (NEW) | DeskScreen — the Research room | the vault surface |
| `knivves/vault/app.py` | room registration, binding `5`, palette command | shell wiring |
| `knivves/scrape.py` | `fetch_listing` / `is_supported` — reused, not modified | what the pass pulls with |
| `knivves/ledger.py` | `seed_history` / `retag_affordable` — reused on price fills | pricing side-effects |
| [../../closed/2026-07-23-ingestion-freshness-design.md](../../closed/2026-07-23-ingestion-freshness-design.md) | prior closed case — repair-report posture inherited | history, standing rules |
| [../../closed/2026-07-23-ingestion-freshness-plan.md](../../closed/2026-07-23-ingestion-freshness-plan.md) | prior closed case — Task 9 reserved-data rule | history, standing rules |

## Requirements ledger

| REQ | Capability | Design | Tasks | Binds | Proof | Status |
|---|---|---|---|---|---|---|
| REQ-RES-1 | gap audit | [§](design.md#req-res-1--gap-audit) | [T1](TODO.md#t1--the-research-backend) | `research.py::audit_record`, `::audit_database` | `test_research.py::test_audit_flags_gaps` | shipped |
| REQ-RES-2 | the docket | [§](design.md#req-res-2--the-docket) | [T1](TODO.md#t1--the-research-backend) | `research.py::build_docket` | `test_research.py::test_docket_orders_buylist_first` | shipped |
| REQ-RES-3 | fill-only-empty merge | [§](design.md#req-res-3--fill-only-empty-merge-with-provenance) | [T1](TODO.md#t1--the-research-backend) | `research.py::research_record` | `test_research.py::test_fill_never_overwrites`, `::test_rulebook_hit_reported_not_written` | shipped |
| REQ-RES-4 | `knivves research` CLI | [§](design.md#req-res-4--knivves-research-cli-pass) | [T2](TODO.md#t2--the-cli-surfaces) | `cli.py::research`, `research.py::run_research` | `test_cli_features.py::test_research_dry_run_no_network` | shipped |
| REQ-RES-5 | DeskScreen (Research room) | [§](design.md#req-res-5--deskscreen) | [T3](TODO.md#t3--the-research-room) | `vault/desk.py::DeskScreen`, `vault/app.py::KnivvesVault` | `test_vault_shell.py::test_desk_demo_transit` | open |
| REQ-RES-6 | completeness readouts | [§](design.md#req-res-6--home-list-and-library-readouts) | [T2](TODO.md#t2--the-cli-surfaces), [T3](TODO.md#t3--the-research-room) | `cli.py::home`, `cli.py::list --gaps`, `vault/plate.py` | `test_cli_features.py::test_home_completeness_line`, `::test_list_gaps_filter` | building |

Grep the join key anywhere:
`grep -rn "REQ-RES-" docs/dev-spec knivves tests`

## Tag map

- `#backend` — REQ-RES-1, REQ-RES-2, REQ-RES-3
- `#cli` — REQ-RES-4, REQ-RES-6
- `#vault` — REQ-RES-5, REQ-RES-6
- `#data-honesty` — REQ-RES-2 (unreachable shelf), REQ-RES-3
  (fill-only-empty, rulebook hits reported not written)

## Standing rules in force

- The live DB is richer than the bundled DB — never overwrite; ingest
  both when merging (memory: knivves DB layout).
- Ingestion `.md` files are one-shot intake batches, never sync
  ledgers; the DB is truth after intake — research enriches, never
  re-imports (memory: ingestion semantics).
- `additions/2026-07-23-knife-additions-2.md` is reserved for the
  user's own ingestion test — never pre-consume
  ([closed plan, Task 9 note](../../closed/2026-07-23-ingestion-freshness-plan.md)).
- First prices are counted in the summary, never streamed — nothing to
  compare against ([CHANGELOG 005](../../CHANGELOG.md)).
- Freshness ages by batches of arrivals, not update count; research
  fills do not seal generations ([CHANGELOG 005](../../CHANGELOG.md)).
- Plain words on the doors: proprietary titles normalized to function —
  the new door reads **Research** ([CHANGELOG 005](../../CHANGELOG.md)).
- House laws are code: one palette, one field grammar, one motion law
  (`knivves/vault/laws.py`).
- Linter coexistence: minimally spaced tables; on-disk realignment by
  markdownlint is normal operation, never revert
  (`.claude/skills/mivim-agent-spec/SKILL.md`).
