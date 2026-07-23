<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["008 — v0.12.0 (2026-07-23) — ONE BUILDING"] },
     "STATUS": "CLOSED (2026-07-23) — archived to docs/closed/ · all three REQs shipped; one acceptance approach annotated inline",
     "NOTE": "Canon below is the doc AS AUTHORED/WRITTEN. Drift since is annotated inline. Do not treat unannotated details as current without checking docs/CHANGELOG.md." } -->
<!-- { "DEV_SPEC": { "case": "2026-07-23-one-building", "doc": "DS-1 design", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-2": "requirements.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# One Building — Design (DS-1)

Case: `2026-07-23-one-building` · Opened: 2026-07-23 · Target: v0.12.0
Hub: [requirements.md](requirements.md) · Tasks: [TODO.md](TODO.md)
Steering source: the triaged THINK-ABOUT harvest of the closed
[standards re-alignment case](../../closed/2026-07-23-standards-realignment/TODO.md)
— TA-2, TA-3, TA-4, promoted here.

## Scope

The re-alignment gave the building its laws; this case makes the
building agree with itself under them. Three coherence fixes, each
small in surface and structural in kind: **one reading of the vault's
state** shared by both front doors (the CLI welcome page and the TUI
entry hall derive the same numbers from one provider — they cannot
disagree because neither derives its own); **the hall's doors answer
the hand** (a door row is a real fixture: click it and it opens, hover
it and it lifts — the click is the key); **the carrying law reaches
the intake line** (a record plate exists on the imports page only
while it carries a record, the same law the research desk already
obeys). In play: `knivves/state.py` (new), `knivves/render.py::home_page`,
`knivves/cli.py::home`, `knivves/tui/pages/vault.py` + `vault.tcss`,
`knivves/tui/pages/imports.py` + `imports.tcss`, the shell suite, one
new backend suite. Untouched: the data layer's schema, every other
page, the CLI command surface.

## Tech stack & context

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Layer | What | Where |
|---|---|---|
| Backend | pure state derivation, plain-python tested | `knivves/state.py` (new), `tests/test_state.py` (new) |
| CLI | welcome page derives from the provider, output unchanged | `knivves/render.py::home_page`, `knivves/cli.py::home` |
| TUI | hall plaques + door rows; imports plate law | `knivves/tui/pages/vault.py`/`.tcss`, `pages/imports.py`/`.tcss` |
| Proof | plain-python runners + capture pipeline, eyes-on | `tests/test_tui_shell.py`, `tests/capture_pages.py` |

Standing rules in force (from 007's close-out): one palette through the
`knivves` theme; sequence performances, never one-shot timers; every
segment carries a style; instruments never lie; proofs cite the
plain-python runners; verify visuals by looking.

## Design features

### One reading of the vault's state

Today the CLI welcome page and the TUI hall each derive blades / ★new /
approved / unresearched / avg / generation window / ladder from the
same backend calls, independently. Two derivations of one truth is a
disagreement waiting for a refactor. `knivves/state.py` becomes the
single reading: a frozen `VaultState` dataclass built by
`vault_state(db)`, carrying every number both doors speak. The CLI's
`home_page` and the hall's plaques render *from* it; neither computes.

#### REQ-STA-1 — the vault-state provider

- **WHAT**: `knivves/state.py::VaultState` (frozen dataclass: blades,
  fresh, approved, unresearched, average_cad, generation,
  keep_generations, version, ladder, ladder_totals) and
  `vault_state(db, knives=None)`; `render.py::home_page` and
  `pages/vault.py` consume it; CLI output text unchanged.
- **WHY**: TA-2 — the two front doors can never disagree if there is
  only one reading.
- **BINDS**: `knivves/state.py::vault_state` · `knivves/render.py::home_page` ·
  `knivves/cli.py::home` · `knivves/tui/pages/vault.py::VaultScreen._surface`
- **ACCEPTANCE**: `tests/test_state.py` (provider unit reading) and
  `tests/test_tui_shell.py::test_two_front_doors_agree` — the hall's
  plaques and the provider report the same numbers.

### The doors answer the hand

The hall's doors plaque is one Static — readable, not touchable. Each
door becomes a `DoorRow` fixture: click it and the page opens (the
click IS the key — same `action_room` the binding fires), hover it and
the row lifts through the cue law in `vault.tcss`. The plaque's reveal
fade covers the rows like everything else.

#### REQ-HAL-1 — door rows as hardware

- **WHAT**: `pages/vault.py::DoorRow` widgets replace the doors Static;
  click opens the row's page via `action_room`; `:hover` lift +
  `transition` declared in `vault.tcss`; the cold-fade covers all
  plaque descendants.
- **WHY**: TA-3 — a door you can see but not touch is a picture, not a
  door.
- **BINDS**: `knivves/tui/pages/vault.py::DoorRow` ·
  `knivves/tui/pages/vault.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_hall_doors_answer_the_hand`
  — click a door row, land on its page; hover state declared; eyes-on
  hover frame.

### The carrying law reaches the intake line

A record plate on the research desk exists only while it carries a
record (007). The imports page still parks an empty plate at its CSS
offset before a transit begins. Same law, same mechanism: hidden until
the transit's first `begin`, carried thereafter.

#### REQ-IMP-1 — the plate carries or vanishes

- **WHAT**: `imports.tcss` hides `#forge-plate` until `.carrying`; all
  three transits (live, file, demo) set carrying at their first
  `plate.begin`.
- **WHY**: TA-4 — an empty plate is not hardware; the law holds in
  every room or it is not a law.
- **BINDS**: `knivves/tui/pages/imports.py::live_transit/file_transit/demo_transit` ·
  `knivves/tui/pages/imports.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_imports_plate_carries`
  — fresh entry shows no plate; the demo's first begin shows it.

<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "008 — v0.12.0", "bullet": "The carrying law reaches the intake line" },
     "CHANGES": ["SUPERSEDED: the acceptance approach — 'fresh entry shows no plate' is untestable as a sampled state because the demo transit carries within milliseconds of mount; the shipped test proves the law's CSS binding directly (remove .carrying -> not displayed, add -> displayed) after the demo settles, which is the stronger claim: no carry, no plate, ever."] } -->

## Cross-cutting constraints

- The CLI welcome page's rendered text does not change — only where its
  numbers come from (the existing CLI tests pin this).
- All 007 standing rules hold; no new colors, no new timers-as-sequences.
- Every visual claim closes on captured frames, eyes on.

## Out of scope / deferred

- Any new page, instrument, or data feature.
- The web front end (unchanged milestone).
- Reworking other pages' plates (library/compare plates are always
  carrying by construction — they open on selection).
