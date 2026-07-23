<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["008 — v0.12.0 (2026-07-23) — ONE BUILDING"] },
     "STATUS": "CLOSED (2026-07-23) — archived to docs/closed/ · all three tasks shipped and verified; checkpoint executed same day",
     "NOTE": "Canon below is the doc AS AUTHORED/WRITTEN. Drift since is annotated inline. Do not treat unannotated details as current without checking docs/CHANGELOG.md." } -->
<!-- { "DEV_SPEC": { "case": "2026-07-23-one-building", "doc": "DS-3 TODO", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-1": "design.md", "DS-2": "requirements.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# One Building — TODO (DS-3)

Case: `2026-07-23-one-building` · Design: [design.md](design.md) · Hub: [requirements.md](requirements.md)

> These tasks are **comprehensive and module-scale** — each targets entire
> modules with effects across the source. They are not little changes.
> Work top-down; record every shipped change in the CHANGELOG; keep the
> [requirements ledger](requirements.md#requirements-ledger) statuses current.

## Tasks

### T1 — the provider

- [x] **T1** One reading of the vault's state: `knivves/state.py` with
  the frozen `VaultState` and `vault_state(db)`; the CLI welcome page
  and the TUI hall both render from it, text unchanged.
  - **Satisfies**: [REQ-STA-1](design.md#req-sta-1--the-vault-state-provider)
  - **Touches**: `knivves/state.py` (create); `knivves/render.py::home_page` (derive from state); `knivves/cli.py::home`; `knivves/tui/pages/vault.py::_state_text/_reserve_text/_surface`; `tests/test_state.py` (create); `tests/test_tui_shell.py::test_two_front_doors_agree` (add)
  - **Done when**: both new proofs pass; `test_cli_features.py` home tests still pass unchanged
  - **Proof**: `python tests/test_state.py` · `python tests/test_cli_features.py` · `python tests/test_tui_shell.py` → all pass

### T2 — the doors under the hand

- [x] **T2** The hall's doors become `DoorRow` fixtures: click opens the
  page (the click is the key), hover lifts the row through the cue law;
  the plaque's cold-fade covers the rows.
  - **Satisfies**: [REQ-HAL-1](design.md#req-hal-1--door-rows-as-hardware)
  - **Touches**: `knivves/tui/pages/vault.py` (DoorRow, compose, doors plaque rebuild); `knivves/tui/pages/vault.tcss` (row cue states, cold-fade descendants)
  - **Done when**: `test_tui_shell.py::test_hall_doors_answer_the_hand` passes; hover frame captured and reviewed eyes-on
  - **Proof**: `python tests/test_tui_shell.py` → pass; hover frame viewed

### T3 — the carrying law + the proof pass

- [x] **T3** The imports plate obeys the carrying law (hidden until a
  transit's first `begin`), and the case is proven: full suites green,
  exhibits refreshed and reviewed eyes-on, CHANGELOG entry 008,
  version 0.12.0.
  - **Satisfies**: [REQ-IMP-1](design.md#req-imp-1--the-plate-carries-or-vanishes) + proof-of-record for the case
  - **Touches**: `knivves/tui/pages/imports.py` (three transit entry begins); `knivves/tui/pages/imports.tcss`; `tests/test_tui_shell.py::test_imports_plate_carries` (add); `tests/capture_pages.py` run; `docs/media/*`; `docs/CHANGELOG.md` (entry 008); `pyproject.toml` + bundled DB → 0.12.0
  - **Done when**: all suites green via the plain-python runners; exhibits viewed and honest; CHANGELOG 008 records the shipped truth
  - **Proof**: `python tests/test_tui_shell.py` + backend suites → all pass; frames viewed

## THINK-ABOUT harvest

<Improvements identified during edits (THINK-ABOUT subworkflow) are noted
here as TODOs the moment they are seen. They never block the checkpoint;
they are triaged when it fires — promoted to the next case, or recorded
and closed with this one.>

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
