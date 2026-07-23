<!-- { "DEV_SPEC": { "case": "2026-07-23-standards-realignment", "doc": "DS-3 TODO", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md", "revisions.md"],
     "LINKS": { "DS-1": "design.md", "DS-2": "requirements.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# The Standards Re-Alignment — TODO (DS-3)

Case: `2026-07-23-standards-realignment` · Design: [design.md](design.md) · Hub: [requirements.md](requirements.md)

> These tasks are **comprehensive and module-scale** — each targets entire
> modules with effects across the source. They are not little changes.
> Work top-down; record every shipped change in the CHANGELOG; keep the
> [requirements ledger](requirements.md#requirements-ledger) statuses current.

## Tasks

### T1 — the restructure

- [x] **T1** `knivves/vault/` becomes `knivves/tui/` with a `pages/`
  package — one module per door named as the door reads — and the vault
  becomes page 0, the entry hall the app opens on.
  - **Satisfies**: [REQ-ARC-1](design.md#req-arc-1--pages-own-their-modules), [REQ-ARC-2](design.md#req-arc-2--the-vault-is-a-page-the-entry-hall)
  - **Touches**: `knivves/vault/*` → `knivves/tui/*` (git mv; `rack.py`→`pages/library.py`, `forge.py`→`pages/imports.py`, `bench.py`→`pages/compare.py`, `ledger.py`→`pages/market.py`, `desk.py`→`pages/research.py`); screen classes + registry keys renamed to match; `pages/vault.py::VaultScreen` (create — hall: vault state, five doors with keys, next acquisitions; key `0` returns); `app.py::KnivvesApp` (rename, bindings, on_mount → hall); `__main__.py`; `knivves/cli.py` (launcher import); `pyproject.toml` (package-data → `tui/*.tcss`, `tui/pages/*.tcss`); `tests/test_vault_shell.py`→`tests/test_tui_shell.py`; `tests/capture_rooms.py`→`tests/capture_pages.py` (+ hall capture added)
  - **Done when**: `test_tui_shell.py::test_pages_map_to_doors` and `::test_entry_hall_doors` pass; full suite green post-move; `python -m knivves.tui` boots to the hall
  - **Proof**: `python -m pytest tests/ -x -q` → all pass; `python tests/capture_pages.py` → six page frames including the hall

### T2 — one theme, six stylesheets

- [x] **T2** The house palette becomes the registered `knivves` Theme
  built in `laws.py`; the monolith stylesheet dissolves into `app.tcss`
  (building chrome only) + one `.tcss` beside each page module, all
  speaking `$variables`, zero hex literals.
  - **Satisfies**: [REQ-CSS-1](design.md#req-css-1--the-knivves-theme), [REQ-CSS-2](design.md#req-css-2--per-page-stylesheets)
  - **Touches**: `knivves/tui/laws.py` (KNIVVES_THEME + variables from palette constants); `knivves/tui/app.py` (register_theme, theme=, CSS_PATH→`app.tcss`); `vault.tcss` → split into `app.tcss` + `pages/{vault,library,imports,compare,market,research}.tcss`; each page Screen gains `CSS_PATH`; widget `DEFAULT_CSS` blocks migrate their hex to variables
  - **Done when**: `test_tui_shell.py::test_theme_is_the_only_palette` and `::test_pages_own_stylesheets` pass; no `#rrggbb` in any `.tcss`
  - **Proof**: `python -m pytest tests/test_tui_shell.py -q` → pass; `grep -rn "#[0-9a-f]\{6\}" knivves/tui --include=*.tcss` → empty

### T3 — the motion tiers

- [x] **T3** `laws.py` gains the REVEAL/IDLE/CUE vocabulary and the
  `Reveal` once-per-open runner; every interactive surface on every page
  declares its hover/focus states and `transition:`s in its page's
  stylesheet.
  - **Satisfies**: [REQ-MOT-1](design.md#req-mot-1--three-tiers-in-the-laws), [REQ-MOT-2](design.md#req-mot-2--cues-live-in-the-stylesheets)
  - **Touches**: `knivves/tui/laws.py` (tier constants, `Reveal`); `knivves/tui/app.tcss` + `pages/*.tcss` (transitions, pseudo-class states across inputs, tables, cards, doors, capsules)
  - **Done when**: `test_tui_shell.py::test_reveal_runs_once_per_open` and `::test_cues_declared_in_css` pass; hover frames captured and reviewed eyes-on
  - **Proof**: `python -m pytest tests/test_tui_shell.py -q` → pass; captured cue frames viewed

### T4 — the research showcase

- [ ] **T4** The unknowns map powers on (gauge sweep + column energize +
  rail draw, once per open, suppressed during a pass), idles with a
  subliminal scan shimmer after settle, and cross-links with the card
  file — card lights column, column answers card.
  - **Satisfies**: [REQ-RES-1](design.md#req-res-1--the-maps-power-on-reveal), [REQ-RES-2](design.md#req-res-2--idle-after-settle), [REQ-RES-3](design.md#req-res-3--the-desk-is-one-instrument)
  - **Touches**: `knivves/tui/pages/research.py` (UnknownsMap reveal/idle/highlight channels, CardFile hover/selection wiring); `knivves/tui/pages/research.tcss`; `knivves/tui/laws.py::Reveal` (consumer)
  - **Done when**: `test_tui_shell.py::test_map_power_on`, `::test_idle_stands_down`, `::test_card_lights_column` pass; reveal + cross-link frames captured and reviewed eyes-on; live pass unaffected (amber wake owns the screen)
  - **Proof**: `python -m pytest tests/test_tui_shell.py -q` → pass; capture pipeline reveal frames viewed

### T5 — the teletype

- [ ] **T5** A reusable `Teletype` surface — paced line printing, block
  cursor, honest truncation, compositor-law-exact strips — adopted by the
  research page's READ station for live and demo transits both.
  - **Satisfies**: [REQ-TRM-1](design.md#req-trm-1--the-teletype)
  - **Touches**: `knivves/tui/surfaces.py` (Teletype widget); `knivves/tui/pages/research.py` (READ station adoption); `knivves/tui/laws.py` (cadence constants)
  - **Done when**: `test_tui_shell.py::test_teletype_paces_and_truncates` passes; print-in-motion frames captured and reviewed eyes-on
  - **Proof**: `python -m pytest tests/test_tui_shell.py -q` → pass

### T6 — every page opens

- [ ] **T6** Each remaining page performs its one named hero reveal
  through `laws.Reveal` — hall fixtures stagger, library rows cascade,
  import stations engrave in sequence, caliper rails draw, the price
  scale draws with the $150 line cut last — nothing else moves on open.
  - **Satisfies**: [REQ-REV-1](design.md#req-rev-1--one-hero-per-page)
  - **Touches**: `knivves/tui/pages/vault.py`, `library.py`, `imports.py`, `compare.py`, `market.py` (reveal hooks); their `.tcss` files (reveal states)
  - **Done when**: `test_tui_shell.py::test_one_hero_per_page` passes; all six open-frames captured and reviewed eyes-on; reveals never block input (keypress jumps to settled)
  - **Proof**: `python -m pytest tests/test_tui_shell.py -q` → pass; six open-frames viewed

### T7 — the proof pass

- [ ] **T7** The whole re-alignment proven: full suite green, every
  `docs/media/` exhibit re-captured from the restructured pages and
  reviewed eyes-on, CHANGELOG entry 007 written, version stamped 0.11.0.
  - **Satisfies**: closes the loop on every REQ above (proof-of-record)
  - **Touches**: `tests/capture_pages.py` (full exhibit refresh); `docs/media/*` (regenerated, renamed to page names); `docs/CHANGELOG.md` (entry 007); `pyproject.toml` + bundled DB version stamp → 0.11.0
  - **Done when**: `python -m pytest tests/ -q` all green; every exhibit frame viewed and honest; CHANGELOG 007 records the shipped truth
  - **Proof**: `python -m pytest tests/ -q` → all pass; `git status` shows refreshed exhibits; CHANGELOG diff

## THINK-ABOUT harvest

<Improvements identified during edits (THINK-ABOUT subworkflow) are noted
here as TODOs the moment they are seen. They never block the checkpoint;
they are triaged when it fires — promoted to the next case, or recorded
and closed with this one.>

- [ ] TA-1 — `revisions.md` is this case's steering source; when the
  checkpoint fires it is satisfied and should be closed out to
  `docs/closed/` alongside the case · seen while opening the case
- [ ] TA-2 — the hall (REQ-ARC-2) and the CLI home page render the same
  vault state; consider one shared stats provider in the backend so the
  two front doors can never disagree · seen while designing REQ-ARC-2

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
