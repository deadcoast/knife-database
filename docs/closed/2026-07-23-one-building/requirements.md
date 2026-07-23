<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["008 — v0.12.0 (2026-07-23) — ONE BUILDING"] },
     "STATUS": "CLOSED (2026-07-23) — archived to docs/closed/ · ledger fully shipped (3/3 REQs)",
     "NOTE": "Canon below is the doc AS AUTHORED/WRITTEN. Drift since is annotated inline. Do not treat unannotated details as current without checking docs/CHANGELOG.md." } -->
<!-- { "DEV_SPEC": { "case": "2026-07-23-one-building", "doc": "DS-2 requirements", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-1": "design.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# One Building — Requirements Hub (DS-2)

Case: `2026-07-23-one-building` · The navigation hub: every document,
every requirement, every binding — one glance, one hop. **Read this
file first.**

## Document registry

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Doc | Role | Read it when |
|---|---|---|
| [design.md](design.md) | DS-1 — the design canon, REQ definitions | you need the WHY or the shape of a feature |
| [TODO.md](TODO.md) | DS-3 — module-scale tasks + checkpoint footer | you need what to do next |
| [../../CHANGELOG.md](../../CHANGELOG.md) | BUS-A living record | you need what is CURRENTLY true |
| [../../closed/2026-07-23-standards-realignment/](../../closed/2026-07-23-standards-realignment/) | the prior case whose harvest opened this one | history, standing rules |
| `knivves/state.py` | the vault-state provider (created at T1) | REQ-STA-1 |
| `knivves/tui/pages/vault.py` + `vault.tcss` | the hall: plaques + door rows | REQ-STA-1, REQ-HAL-1 |
| `knivves/tui/pages/imports.py` + `imports.tcss` | the intake line's plate law | REQ-IMP-1 |
| `tests/test_state.py` · `tests/test_tui_shell.py` | plain-python proof runners | every ACCEPTANCE |

## Requirements ledger

| REQ | Capability | Design | Tasks | Binds | Proof | Status |
|---|---|---|---|---|---|---|
| REQ-STA-1 | one vault-state provider | [§](design.md#req-sta-1--the-vault-state-provider) | [T1](TODO.md#t1--the-provider) | `state.py::vault_state` · `render.py::home_page` · `pages/vault.py` | `test_state.py` + `test_tui_shell.py::test_two_front_doors_agree` | shipped |
| REQ-HAL-1 | door rows as hardware | [§](design.md#req-hal-1--door-rows-as-hardware) | [T2](TODO.md#t2--the-doors-under-the-hand) | `pages/vault.py::DoorRow` · `vault.tcss` | `test_tui_shell.py::test_hall_doors_answer_the_hand` + eyes-on | shipped |
| REQ-IMP-1 | the plate carries or vanishes | [§](design.md#req-imp-1--the-plate-carries-or-vanishes) | [T3](TODO.md#t3--the-carrying-law--the-proof-pass) | `pages/imports.py` transits · `imports.tcss` | `test_tui_shell.py::test_imports_plate_carries` + eyes-on | shipped |

## Tag map

- `#coherence` — REQ-STA-1, REQ-HAL-1, REQ-IMP-1
- `#harvest-TA-2` — REQ-STA-1 · `#harvest-TA-3` — REQ-HAL-1 · `#harvest-TA-4` — REQ-IMP-1

## Standing rules in force

- All rules recorded at the 007 close-out: one palette through the
  theme; sequence performances, never one-shot timers; every segment
  carries a style; instruments never lie; proofs cite the plain-python
  runners; verify visuals by looking —
  [closed case](../../closed/2026-07-23-standards-realignment/TODO.md).
- The CLI welcome page's text is pinned by `tests/test_cli_features.py`
  (`test_bare_knivves_opens_the_home_page`, `test_home_completeness_line`).
