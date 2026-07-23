<!-- { "DEV_SPEC": { "case": "2026-07-23-standards-realignment", "doc": "DS-1 design", "bus": "BUS-B" },
     "STATUS": "OPEN (2026-07-23) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md", "revisions.md"],
     "LINKS": { "DS-2": "requirements.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# The Standards Re-Alignment — Design (DS-1)

Case: `2026-07-23-standards-realignment` · Opened: 2026-07-23 · Target: v0.11.0
Hub: [requirements.md](requirements.md) · Tasks: [TODO.md](TODO.md)
Steering source: [revisions.md](../../../revisions.md) — the user's re-alignment
directive. Every REQ below traces to a numbered point in it.

## Scope

This case re-aligns the TUI to the standard the project was founded on:
work that would impress the developers of Textual. Three failures are
named in the steering doc and corrected here. **Structure** ([1]): the
vault is conflated with the application — `knivves/vault/` houses every
page under proprietary module names the doors no longer use; the source
is reorganized so the application is KNIVVES, pages are modules named as
their doors read, and the vault becomes literally a page (the entry
hall). **Surfaces** ([2]): one thin static `.tcss` serves five pages;
each page gets its own stylesheet under one registered Textual theme, and
the CSS system is used as its authors built it — variables, per-screen
stylesheets, transitions, pseudo-classes. **Motion** ([5]): animation
becomes a designed three-tier system (REVEAL / IDLE / CUE) instead of ad
hoc choreography, with the research page's unknowns map as the showcase
asset and a reusable teletype surface for live-printing data. In play:
`knivves/vault/` (restructured to `knivves/tui/`), `pyproject.toml`
packaging, `tests/test_vault_shell.py`, `tests/capture_rooms.py`.
Untouched: the data layer (`store`, `models`, `ingest`, `research`,
`ledger`, `generations`, `buylist`, `scrape`), the CLI's command surface,
the web stack (not begun).

## Tech stack & context

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Layer | What | Where |
|---|---|---|
| TUI | Textual >=8.0.0 (reference checkout 8.2.8) — Screens, per-screen CSS_PATH, Theme + variables, TCSS transition/pseudo-classes, styles.animate | `knivves/tui/` (post-restructure; today `knivves/vault/`) |
| House laws | palette / field grammar / motion law as code | `knivves/tui/laws.py` |
| CLI | typer + rich, palette mirrored; launches the TUI | `knivves/cli.py`, `knivves/render.py` |
| Data | JSON DB, atomic writes, backups — untouched | `knivves/store.py`, `~/.knivves/` |
| Proof | headless Pilot suite + frame-capture pipeline, eyes-on review | `tests/test_vault_shell.py`, `tests/capture_rooms.py`, `docs/media/` |

Context an agent needs first:

- **The steering doc**: [revisions.md](../../../revisions.md). Its
  DESIGN_WORK_STANDARDS govern every visual decision: robust designs done
  well where necessary, minimal accents to compliment them; too much retro
  is a trope, too little is lazy; cohesion and critical placement over
  quantity. Its [6] assigns initiative: identify weak visual integrations
  and raise them — never dismiss a weak integration to finish faster.
- **The reference library**: the local Textual checkout at
  `C:/Users/ryanf/github/ASSETS/textual/` (docs/guide/*.md +
  src/textual/) and https://textual.textualize.io/guide/ — consult BEFORE
  designing, not after. Facts already verified there: `Screen.CSS_PATH`
  is first-class (`src/textual/screen.py:165`); `Theme.variables` flows
  custom `$variables` into every stylesheet (`src/textual/theme.py`);
  `transition:` is a real TCSS property (`css/styles.py::TransitionsProperty`).
- **Prior canon**: [the research-desk case](../../closed/2026-07-23-research-desk/)
  (CHANGELOG 006) built the instruments this case animates; the
  compositor law (pad every `render_line` strip to exact width) was paid
  for there. The v0.9.0 door renames (CHANGELOG 005) started the plain-words
  normalization this case finishes in the source tree.
- **J-SPACE**, applied per stage: the WHO/WHAT/WHERE/WHY of each visual
  decision is asked before it is built ([5.2.2.5]). The bar: would the
  Textual devs, seeing the frame, recognize their own system used at
  full depth — themes, per-screen CSS, transitions — plus integrations
  they have not seen before?

## Design features

### The application and its pages ([1])

The building metaphor stays — it is the product's soul — but the source
stops lying about it. KNIVVES is the application; the vault is its entry
hall, a page like the others; the five working pages are modules named
exactly as their doors read. An agent (or a Textual dev reading the repo)
maps menu → module with zero translation:

```text
knivves/tui/                     the application
├─ app.py        KnivvesApp — shell, screen registry, door keys
├─ app.tcss      building chrome only: Screen base, Footer, shared classes
├─ laws.py       house laws: palette→Theme, field grammar, motion tiers
├─ masthead.py, door.py, plate.py, tips.py, gauges.py, surfaces.py   shared fixtures
└─ pages/        one page = one module + one stylesheet
   ├─ vault.py      + vault.tcss      page 0 — the entry hall
   ├─ library.py    + library.tcss    door 1 (was rack.py)
   ├─ imports.py    + imports.tcss    door 2 (was forge.py)
   ├─ compare.py    + compare.tcss    door 3 (was bench.py)
   ├─ market.py     + market.tcss     door 4 (was ledger.py)
   └─ research.py   + research.tcss   door 5 (was desk.py)
```

Screen classes rename with their modules (`LibraryScreen`,
`ImportsScreen`, `CompareScreen`, `MarketScreen`, `ResearchScreen`,
`VaultScreen`); screen-registry keys match module names. The backend
module `knivves/ledger.py` is untouched — the rename removes the
`vault/ledger.py` shadow that made two ledgers.

#### REQ-ARC-1 — pages own their modules

- **WHAT**: `knivves/vault/` restructured to `knivves/tui/` with a
  `pages/` package; one module per door, named as the door reads; screen
  classes and registry keys renamed to match; all importers
  (`cli.py`, `__main__.py`, tests, capture pipeline) and
  `pyproject.toml` package-data follow.
- **WHY**: revisions [1] — the source organization must match the
  represented application: a knife database with distinct pages, not a
  vault housing everything.
- **BINDS**: `knivves/tui/app.py::KnivvesApp` · `knivves/tui/pages/*` ·
  `pyproject.toml::[tool.setuptools.package-data]` ·
  `tests/test_tui_shell.py` · `tests/capture_pages.py`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_pages_map_to_doors` —
  every registry key, module name, and door label agree; full suite green
  post-move.

#### REQ-ARC-2 — the vault is a page: the entry hall

- **WHAT**: a `VaultScreen` home page the app opens on: the machined
  door parts onto the hall — vault state (blades / approved / avg CAD /
  ★new window), the five doors with their keys, the next acquisitions
  (top BuyList rungs). Keys 1–5 leave the hall; `0` returns from any
  page. Stats derive from the same backend calls the CLI home page uses.
- **WHY**: revisions [1] — "the vault is a page on the application";
  make it literally true. The TUI gains the front door the CLI got in
  v0.9.0.
- **BINDS**: `knivves/tui/pages/vault.py::VaultScreen` ·
  `knivves/tui/app.py::KnivvesApp.on_mount` · `knivves/tui/pages/vault.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_entry_hall_doors` —
  boot lands on the hall, each key opens its page, `0` returns.

### One theme, six stylesheets ([2.a], [2.c])

The reason Textual was chosen was its visual system; this case uses it
at native depth. The house palette becomes a registered `Theme` named
`knivves` — built in `laws.py` from the same constants, so Python and
CSS can never drift — with every house color flowing into TCSS as
`$variables` (`$edge`, `$steel-bright`, `$steel-mid`, `$steel-dim`,
`$fresh`, plus the standard `$primary`/`$accent`/`$success`/`$error`
mappings). `vault.tcss`-the-monolith dissolves: `app.tcss` keeps only
building chrome; each page's layout, states, and transitions live in its
own stylesheet beside its module, where a page is free to be designed
as itself ([3]: isolating the `.tcss` buys comprehensive freedom).

#### REQ-CSS-1 — the KNIVVES theme

- **WHAT**: `laws.py` builds and exports a Textual `Theme` ("knivves")
  from the palette constants with `variables` for every house color;
  `KnivvesApp` registers it and sets `theme = "knivves"`; zero raw hex
  literals remain in any `.tcss`.
- **WHY**: revisions [2] — the palette lived twice (Python + hex copies
  in CSS, "mirrors laws.py" by comment only); the theme system is the
  Textual-native single source of truth, and it puts the house palette
  in the same registry the devs' own themes live in.
- **BINDS**: `knivves/tui/laws.py::KNIVVES_THEME` ·
  `knivves/tui/app.py::KnivvesApp` · every `*.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_theme_is_the_only_palette` —
  theme registered and active; grep of all `.tcss` finds no `#rrggbb`.

#### REQ-CSS-2 — per-page stylesheets

- **WHAT**: every page Screen declares `CSS_PATH` to its sibling
  `<page>.tcss`; `app.tcss` (App-level) carries only what every page
  shares (Screen base, Footer, station/plate frame classes); packaging
  ships `tui/*.tcss` and `tui/pages/*.tcss`.
- **WHY**: revisions [2.a]/[2.c] — different pages have different
  layouts and purposes and deserve their own design files; one file for
  five pages was the drift.
- **BINDS**: `knivves/tui/pages/<page>.py::<Page>Screen.CSS_PATH` (all
  six) · `knivves/tui/app.tcss` · `pyproject.toml`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_pages_own_stylesheets` —
  each screen resolves its own stylesheet; app CSS contains no
  page-specific selectors.

### The motion law grows tiers ([5.2], [7])

Today `laws.py` has one motion primitive (`travel()`); the revisions
demand a *system*: loud where the eye should go, silent everywhere else.
Three tiers, codified as constants and used by every page:

- **REVEAL** — once, on page open. The page's one hero instrument
  performs; everything else holds still. Loud, designed, settled in
  ≤ ~1.2s. Never re-runs on data refresh; never runs during a live
  operation.
- **IDLE** — after settle. Subliminal, long-cadence, barely noticeable
  unless looked for ([5.2.2.3]); suspended during REVEAL and during any
  live pass. Placed only where it serves a purpose.
- **CUE** — the machine answers the hand: hover/focus/selection feedback
  declared in TCSS (`transition:` + `:hover`/`:focus`), immediate and
  quiet.

The balance law ([7]) rules the tiers: each page names exactly one
REVEAL hero; IDLE is opt-in per page and defaults to none; CUE is
everywhere interactive. Instruments never lie — a REVEAL may only
dramatize true data (the 006 law: nothing lights that is not known).

#### REQ-MOT-1 — three tiers in the laws

- **WHAT**: `laws.py` gains the tier vocabulary — REVEAL/IDLE/CUE
  durations, easings, cadences, and a `Reveal` runner that sequences a
  page's opening performance and guarantees once-per-open; `travel()`
  remains the movement primitive under it.
- **WHY**: revisions [5.2]/[7] — animation as a balanced, designed
  ecosystem, not per-widget improvisation; one vocabulary so every page
  moves in the same dialect.
- **BINDS**: `knivves/tui/laws.py::REVEAL/IDLE/CUE constants` ·
  `knivves/tui/laws.py::Reveal`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_reveal_runs_once_per_open` —
  a page's reveal fires on open, does not re-fire on refresh, re-arms on
  re-entry.

#### REQ-MOT-2 — cues live in the stylesheets

- **WHAT**: every interactive surface (inputs, tables, docket cards,
  doors on the hall, capsules) declares its hover/focus states and
  `transition:`s in its page's `.tcss` — response under the hand, in CSS,
  where the Textual devs built it to live.
- **WHY**: revisions [2.c] — the `.tcss` was largely ignored; CUE-tier
  motion is exactly what its `transition:` + pseudo-class system is for.
- **BINDS**: `knivves/tui/pages/*.tcss` (all) · `knivves/tui/app.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_cues_declared_in_css` —
  each page's stylesheet declares `transition:` rules; captured hover
  frames reviewed eyes-on.

### The research page — the showcase ([5.2.1], [5.2.2])

The unknowns map with its completeness gauge is named in the steering
doc as the asset with the largest potential — and the largest risk. The
design: **the instrument powers on**. On page open the map runs a
one-time self-test the way real dot-matrix hardware announces itself:
the gauge sweeps 0 → its true value as the columns energize left to
right (staggered, accelerating), the scale rail draws in beneath, and
the whole field settles into stillness ([5.2.2.1]). After settle, IDLE:
a slow scan shimmer traverses the map on a long cadence — felt more
than seen ([5.2.2.2–3]). CUE makes the desk one instrument: hovering or
selecting a card in the card file lights that record's column on the
map (and the column answers back with the card), so the eye travels
between docket and map on rails ([3]: an integration, not a
re-arrangement). During a live research pass the reveal and idle stand
down — the amber wake of real learned facts (006) owns the screen, and
the map never lies.

#### REQ-RES-1 — the map's power-on reveal

- **WHAT**: once per page open: gauge sweeps 0→N%, columns energize
  left→right staggered, scale rail draws; settled ≤ ~1.2s; suppressed
  entirely when a pass is running; only true data is dramatized.
- **WHY**: revisions [5.2.2.1] — highlight the feature on opening,
  bringing the eyes to it; the showcase of what the standards mean.
- **BINDS**: `knivves/tui/pages/research.py::UnknownsMap` (reveal
  states) · `knivves/tui/laws.py::Reveal` · `knivves/tui/pages/research.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_map_power_on` — reveal
  sequences and settles, once; captured reveal frames reviewed eyes-on.

#### REQ-RES-2 — idle after settle

- **WHAT**: post-settle ambient motion on the map only: a slow scan
  shimmer at long cadence (IDLE constants); imperceptible at a glance,
  visible when watched; suspended during reveal and live pass.
- **WHY**: revisions [5.2.2.2–3] — comprehensive but minimally executed;
  background motion must never intrude.
- **BINDS**: `knivves/tui/pages/research.py::UnknownsMap` ·
  `knivves/tui/laws.py::IDLE constants`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_idle_stands_down` —
  idle active when settled, suspended during pass; cadence from laws.

#### REQ-RES-3 — the desk is one instrument

- **WHAT**: hover/selection on a docket card lights its column on the
  map (bright + marker); the active card's column and the card's punch-row
  agree at all times; declared as CUE-tier states in `research.tcss` +
  a highlight channel on the map widget.
- **WHY**: revisions [3] — users see re-arrangement instantly; a
  cross-linked instrument is the unique integration that reads as new.
- **BINDS**: `knivves/tui/pages/research.py::CardFile` ·
  `knivves/tui/pages/research.py::UnknownsMap` ·
  `knivves/tui/pages/research.tcss`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_card_lights_column` —
  selecting card N highlights column N; captured frame reviewed eyes-on.

### The teletype surface ([5.1])

Some windows should *print* their data, not paint it. A reusable
`Teletype` surface: lines arrive at a paced cadence (laws constant,
tuned per the animation guide — not too fast, not too slow), a block
cursor rides the print head, and completion is honest (interrupting
shows exactly what printed). First integration: the READ station on the
research page — the record's listing prints fact by fact as it is
learned, live and demo both driving the same surface. The pacing law:
a teletype dramatizes *arrival*; data already known renders instantly —
the surface never fakes latency that is not there.

#### REQ-TRM-1 — the teletype

- **WHAT**: a reusable paced line-printer widget (worker/timer-driven,
  cadence + cursor from laws, exact-width strips per the compositor
  law); READ station adopts it; interruption truncates honestly.
- **WHY**: revisions [5.1] — the mini pseudo-terminal effect, executed
  per Textual docs and DESIGN_WORK_STANDARDS.
- **BINDS**: `knivves/tui/surfaces.py::Teletype` ·
  `knivves/tui/pages/research.py::READ station`
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_teletype_paces_and_truncates` —
  lines land on cadence, interrupt leaves only printed lines; frames
  reviewed eyes-on.

### Every page opens ([5.2.1] generalized, [7] enforced)

The highlight-on-opening strategy applies to every page, under the
one-hero law — each page names its single REVEAL instrument; everything
else on the page holds still while it performs:

| Page | Hero | The reveal |
|---|---|---|
| Vault (hall) | the door → the hall | door parts (exists), hall fixtures surface in one stagger |
| Library | the rack | rows surface in a fast cascade, cursor seats |
| Imports | the intake line | stations engrave their headers in sequence, cold → lit |
| Compare | the caliper beams | rails draw, jaws park at rest |
| Market | the price scale | scale draws, the $150 line cuts in accent last |
| Research | the unknowns map | REQ-RES-1 |

#### REQ-REV-1 — one hero per page

- **WHAT**: each page implements its named hero reveal through
  `laws.Reveal`; no page animates more than its hero on open; reveals
  settle ≤ ~1.2s and never block input.
- **WHY**: revisions [5.2.1]/[7] — bring the eyes to the feature on
  opening; balance is a requirement, overstimulation is a failure mode.
- **BINDS**: `knivves/tui/pages/library.py` · `imports.py` ·
  `compare.py` · `market.py` · `vault.py` (each screen's reveal hook)
- **ACCEPTANCE**: `tests/test_tui_shell.py::test_one_hero_per_page` —
  every page registers exactly one reveal; captured open-frames of all
  six pages reviewed eyes-on.

## Cross-cutting constraints

- **One palette**: all color through the `knivves` theme's variables; no
  `.tcss` may introduce a hex literal; FRESH mint stays ★new-only.
- **The compositor law** (CHANGELOG 006): every `render_line` strip pads
  to exact widget width; declared cell lengths never lie.
- **Instruments never lie**: reveals/idle dramatize only true data;
  demo transits write nothing and light nothing false.
- **Motion only through the laws**: `travel()` / `Reveal` / tier
  constants — no page invents durations or easings.
- **Reveals never block**: input is live during any REVEAL; a keypress
  mid-reveal completes it instantly (jump-to-settled).
- **Development over deletion** (MIVIM): the restructure moves and
  renames; no capability is dropped.
- **Linter coexistence**: tables authored minimally spaced; on-disk
  realignment by markdownlint is normal operation.
- **Verify visuals by looking**: no animation/visual REQ closes on green
  tests alone — captured frames, eyes on, every time.

## Out of scope / deferred

- The web front end (post-CLI-completion milestone, unchanged).
- CLI command surface and classic browser — no behavior changes beyond
  the TUI launcher import path.
- Data-layer modules and DB schema — untouched.
- New pages beyond the entry hall; new data features (this case is
  standards, not scope).
- Textual version bump beyond `>=8.0.0` (reference facts verified
  against 8.2.8; no 8.x-only API is required that the pin excludes).
