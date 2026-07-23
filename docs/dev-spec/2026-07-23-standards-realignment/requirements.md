<!-- { "DEV_SPEC": { "case": "2026-07-23-standards-realignment", "doc": "DS-2 requirements", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md", "revisions.md"],
     "LINKS": { "DS-1": "design.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# The Standards Re-Alignment — Requirements Hub (DS-2)

Case: `2026-07-23-standards-realignment` · The navigation hub: every
document, every requirement, every binding — one glance, one hop.
**Read this file first.**

## Document registry

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Doc | Role | Read it when |
|---|---|---|
| [design.md](design.md) | DS-1 — the design canon, REQ definitions | you need the WHY or the shape of a feature |
| [TODO.md](TODO.md) | DS-3 — module-scale tasks + checkpoint footer | you need what to do next |
| [../../CHANGELOG.md](../../CHANGELOG.md) | BUS-A living record | you need what is CURRENTLY true |
| [../../../revisions.md](../../../revisions.md) | the user's steering directive this case executes | you need the standard being enforced |
| [../../../MIVIM-spec.yaml](../../../MIVIM-spec.yaml) | the quality law (J-SPACE) | you need the bar |
| `knivves/vault/` → `knivves/tui/` | the TUI package this case restructures (T1 renames it) | any REQ binding below |
| `knivves/tui/laws.py` | house laws: palette→Theme, motion tiers | REQ-CSS-1, REQ-MOT-1 |
| `knivves/tui/pages/` | one module + one `.tcss` per page (post-T1) | REQ-ARC-1..2, REQ-CSS-2, page REQs |
| `tests/test_tui_shell.py` | headless Pilot suite (renamed from `test_vault_shell.py` at T1) | every ACCEPTANCE |
| `tests/capture_pages.py` | frame-capture pipeline (renamed from `capture_rooms.py` at T1) | eyes-on proofs |
| `C:/Users/ryanf/github/ASSETS/textual/` | local Textual 8.2.8 reference (src + docs/guide) | before designing anything visual |
| [../../closed/2026-07-23-research-desk/](../../closed/2026-07-23-research-desk/) | prior case — built the instruments this case animates | history, the compositor law |

Binding paths in this case are **post-restructure** (`knivves/tui/...`);
until T1 lands they read `knivves/vault/` on disk with the old module
names (`rack.py`, `forge.py`, `bench.py`, `ledger.py`, `desk.py`).

## Requirements ledger

| REQ | Capability | Design | Tasks | Binds | Proof | Status |
|---|---|---|---|---|---|---|
| REQ-ARC-1 | pages own their modules | [§](design.md#req-arc-1--pages-own-their-modules) | [T1](TODO.md#t1--the-restructure) | `knivves/tui/pages/*` · `pyproject.toml` | `test_tui_shell.py::test_pages_map_to_doors` | open |
| REQ-ARC-2 | the vault is a page: the entry hall | [§](design.md#req-arc-2--the-vault-is-a-page-the-entry-hall) | [T1](TODO.md#t1--the-restructure) | `pages/vault.py::VaultScreen` | `test_tui_shell.py::test_entry_hall_doors` | open |
| REQ-CSS-1 | the KNIVVES theme | [§](design.md#req-css-1--the-knivves-theme) | [T2](TODO.md#t2--one-theme-six-stylesheets) | `laws.py::KNIVVES_THEME` · all `.tcss` | `test_tui_shell.py::test_theme_is_the_only_palette` | open |
| REQ-CSS-2 | per-page stylesheets | [§](design.md#req-css-2--per-page-stylesheets) | [T2](TODO.md#t2--one-theme-six-stylesheets) | `pages/<page>.py::CSS_PATH` · `app.tcss` | `test_tui_shell.py::test_pages_own_stylesheets` | open |
| REQ-MOT-1 | three motion tiers in the laws | [§](design.md#req-mot-1--three-tiers-in-the-laws) | [T3](TODO.md#t3--the-motion-tiers) | `laws.py::Reveal` + tier constants | `test_tui_shell.py::test_reveal_runs_once_per_open` | open |
| REQ-MOT-2 | cues live in the stylesheets | [§](design.md#req-mot-2--cues-live-in-the-stylesheets) | [T3](TODO.md#t3--the-motion-tiers) | `pages/*.tcss` transitions | `test_tui_shell.py::test_cues_declared_in_css` + eyes-on | open |
| REQ-RES-1 | the map's power-on reveal | [§](design.md#req-res-1--the-maps-power-on-reveal) | [T4](TODO.md#t4--the-research-showcase) | `pages/research.py::UnknownsMap` | `test_tui_shell.py::test_map_power_on` + eyes-on | open |
| REQ-RES-2 | idle after settle | [§](design.md#req-res-2--idle-after-settle) | [T4](TODO.md#t4--the-research-showcase) | `pages/research.py::UnknownsMap` | `test_tui_shell.py::test_idle_stands_down` | open |
| REQ-RES-3 | the desk is one instrument | [§](design.md#req-res-3--the-desk-is-one-instrument) | [T4](TODO.md#t4--the-research-showcase) | `pages/research.py::CardFile`+`UnknownsMap` | `test_tui_shell.py::test_card_lights_column` + eyes-on | open |
| REQ-TRM-1 | the teletype | [§](design.md#req-trm-1--the-teletype) | [T5](TODO.md#t5--the-teletype) | `surfaces.py::Teletype` | `test_tui_shell.py::test_teletype_paces_and_truncates` | open |
| REQ-REV-1 | one hero per page | [§](design.md#req-rev-1--one-hero-per-page) | [T6](TODO.md#t6--every-page-opens) | all page modules' reveal hooks | `test_tui_shell.py::test_one_hero_per_page` + eyes-on | open |

## Tag map

- `#structure` — REQ-ARC-1, REQ-ARC-2
- `#stylesheets` — REQ-CSS-1, REQ-CSS-2, REQ-MOT-2
- `#motion` — REQ-MOT-1, REQ-MOT-2, REQ-REV-1
- `#showcase` — REQ-RES-1, REQ-RES-2, REQ-RES-3, REQ-TRM-1
- `#steering-[1]` — REQ-ARC-1, REQ-ARC-2 (revisions [1])
- `#steering-[2]` — REQ-CSS-1, REQ-CSS-2, REQ-MOT-2 (revisions [2.a]/[2.c])
- `#steering-[5]` — REQ-TRM-1, REQ-RES-1..3, REQ-MOT-1, REQ-REV-1 (revisions [5.1]/[5.2])

## Standing rules in force

- **J-SPACE**: if it would not impress the Textual devs, raise the bar —
  [MIVIM-spec.yaml](../../../MIVIM-spec.yaml).
- **DESIGN_WORK_STANDARDS**: strategic retro — robust where necessary,
  minimal accents, cohesion, critical placement; too much is a trope,
  too little is lazy — [revisions.md](../../../revisions.md) [4]/[7].
- **One palette, one accent**: FRESH mint is ★new-only; no room
  introduces a color — `knivves/tui/laws.py`.
- **The compositor law**: every `render_line` strip pads to exact widget
  width — CHANGELOG 006, learned by eyes.
- **Instruments never lie**: nothing lights that is not known; demo
  transits write nothing — CHANGELOG 006 (the map "never lies").
- **Verify visuals by looking**: capture frames and view them before any
  visual claim; green tests are not visual verification.
- **Development over deletion**: restructure moves, never drops —
  [MIVIM-spec.yaml](../../../MIVIM-spec.yaml).
- **Linter coexistence**: minimally-spaced tables; on-disk realignment
  is normal operation — never revert.
