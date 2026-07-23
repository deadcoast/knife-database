<!-- { "DEV_SPEC": { "case": "2026-07-23-research-desk", "doc": "DS-3 TODO", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-1": "design.md", "DS-2": "requirements.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# The Research Desk — TODO (DS-3)

Case: `2026-07-23-research-desk` · Design: [design.md](design.md) · Hub: [requirements.md](requirements.md)

> These tasks are **comprehensive and module-scale** — each targets entire
> modules with effects across the source. They are not little changes.
> Work top-down; record every shipped change in the CHANGELOG; keep the
> [requirements ledger](requirements.md#requirements-ledger) statuses current.

## Tasks

### T1 — the research backend

- [x] **T1** Build `knivves/research.py`: the gap audit, the docket, the
  fill-only-empty merge with provenance, and the `run_research`
  orchestrator with injectable fetch — pure logic, no network in tests.
  - **Satisfies**: [REQ-RES-1](design.md#req-res-1--gap-audit),
    [REQ-RES-2](design.md#req-res-2--the-docket),
    [REQ-RES-3](design.md#req-res-3--fill-only-empty-merge-with-provenance)
  - **Touches**: `knivves/research.py` (create), `tests/test_research.py`
    (create; fixtures lifted from real listings for the two supported
    hosts), reads `knivves/models.py`, `knivves/scrape.py`,
    `knivves/ledger.py`
  - **Done when**: `test_audit_flags_gaps`,
    `test_docket_orders_buylist_first`, `test_fill_never_overwrites`,
    `test_rulebook_hit_reported_not_written` all pass offline; a
    user-entered field is never overwritten under any fixture.
  - **Proof**: `python -m pytest tests/test_research.py -q` → all pass,
    no network.

### T2 — the CLI surfaces

- [x] **T2** Wire the pass into the CLI: the `research` command
  (concurrent docket pass, live "researching the unknowns" progress,
  per-field summary, `--dry-run`, `--id`), `list --gaps`, and the home
  page completeness line with the Research door listed.
  - **Satisfies**: [REQ-RES-4](design.md#req-res-4--knivves-research-cli-pass),
    [REQ-RES-6](design.md#req-res-6--home-list-and-library-readouts)
  - **Touches**: `knivves/cli.py` (new command; `list` option; `home`),
    `knivves/render.py` (summary table if needed),
    `tests/test_cli_features.py` (extend)
  - **Done when**: `test_research_dry_run_no_network`,
    `test_list_gaps_filter`, `test_home_completeness_line` pass; dry-run
    leaves the DB byte-identical; summary names every fill, every
    unreachable, every rulebook hit.
  - **Proof**: `python -m pytest tests/test_cli_features.py -q` → all
    pass; `knivves research --dry-run` on the bundled DB prints the
    docket plan with zero writes.

### T3 — the Research room

- [x] **T3** Build `knivves/vault/desk.py::DeskScreen` — docket rack
  with gap chips, PULL → READ → STAMP stations, traveling worked plate,
  amber field-stamp flashes, masthead readout (docket depth · pass
  state · meter), unreachable shelf, `s` live pass, `r` no-network demo
  — and register it as door **5 — Research** (SCREENS, BINDINGS,
  palette command, TCSS). Add the Library plate `UNRESEARCHED n` chip.
  - **Satisfies**: [REQ-RES-5](design.md#req-res-5--deskscreen),
    [REQ-RES-6](design.md#req-res-6--home-list-and-library-readouts)
  - **Touches**: `knivves/vault/desk.py` (create),
    `knivves/vault/app.py`, `knivves/vault/vault.tcss`,
    `knivves/vault/plate.py`, `knivves/vault/masthead.py` (readout),
    `tests/test_vault_shell.py` (extend)
  - **Done when**: `test_desk_demo_transit` passes headless on a
    throwaway DB — room 5 opens through the door, the demo transit
    stamps learned fields, the docket count decreases, layout-law
    assertions hold; house laws obeyed (no new colors, travel only).
  - **Proof**: `python -m pytest tests/test_vault_shell.py -q` → all
    pass; eyes-on frame capture of the desk transit for `docs/media/`.

### T4 — the doors updated

- [ ] **T4** Update the building's paperwork to the five-room truth:
  README gains the Research room section with a captured exhibit,
  room count/door listings corrected everywhere they are stated
  (README, home page copy shipped in T2), and the CHANGELOG entry 006
  drafted as work ships (the living record stays current through the
  case, not after it).
  - **Satisfies**: supports [REQ-RES-5](design.md#req-res-5--deskscreen),
    [REQ-RES-6](design.md#req-res-6--home-list-and-library-readouts)
    (no new REQ — the documentation face of the case)
  - **Touches**: `README.md`, `docs/media/` (new exhibit via the
    frame-capture pipeline), `docs/CHANGELOG.md`
  - **Done when**: README describes five rooms with the Research
    exhibit rendering; CHANGELOG 006 lists every shipped change of this
    case in the house voice.
  - **Proof**: README renders correctly; `grep -n "Research" README.md
    docs/CHANGELOG.md` shows the room and the entry.

## THINK-ABOUT harvest

<!-- Improvements identified during edits (THINK-ABOUT subworkflow) are
noted here as TODOs the moment they are seen. They never block the
checkpoint; they are triaged when it fires — promoted to the next case,
or recorded and closed with this one. -->

- [ ] TA-3 — `list` grew `--gaps/--no-gaps` without the house single-dash
  alias (`-new`, `-section` have one) · seen while wiring T2 — decide the
  alias convention for paired bool options.
- [ ] TA-1 — CHANGELOG entries 001/002 still carry dead sandbox
  download links (`sandbox:/mnt/data/…`) · seen while reviewing the
  living record to open this case — candidates for an annotated tidy,
  never a silent rewrite.
- [ ] TA-2 — `import-knivves.md` sits at the repo root while
  `additions/` is the intake home · seen while surveying the ledgers —
  flag to the user (their file, their move); one intake directory
  would give the Research docket and future ingests a single door.

---

<!-- checkpointTriggerFooter -->
> [!IMPORTANT]
> ## ⛿ CHECKPOINT TRIGGER
> **When every task above is `[x]`, this footer fires. Execute exactly:**
>
> 1. **Close out this TODO** — closing-out-docs skill: CHANGELOG_REFERENCE
>    annotations at any tasks whose shipped form drifted from their canon,
>    CLOSED banner up top.
> 2. **Notify the user**: this TODO is **COMPLETE**, **CLOSED**, and a
>    **CHECKPOINT is reached**.
> 3. **State the direct next objective to the user**: you will now
>    (a) review the source code changes, (b) ensure `docs/CHANGELOG.md`
>    is up to date, and (c) close out the design and requirements docs
>    that accompany this TODO plan.
> 4. **Execute it**: review the diff · complete the CHANGELOG entry ·
>    close out [design.md](design.md) and [requirements.md](requirements.md)
>    against it · `git mv` this case folder to `docs/closed/<case>/` ·
>    add the case's row to [docs/closed/INDEX.md](../../closed/INDEX.md).
>
> A checkpoint is the only sanctioned end of this case.
