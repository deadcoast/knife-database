<!-- { "DEV_SPEC": { "case": "<YYYY-MM-DD>-<slug>", "doc": "DS-1 design", "bus": "BUS-B" },
     "STATUS": "OPEN (<YYYY-MM-DD>) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-2": "requirements.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# <Case Title> — Design (DS-1)

Case: `<YYYY-MM-DD>-<slug>` · Opened: <date> · Target: v<X.Y.Z>
Hub: [requirements.md](requirements.md) · Tasks: [TODO.md](TODO.md)

## Scope

<What this case builds and what it deliberately does not. 3–8 sentences.
Name the boundary: which modules are in play, which are untouched.>

## Tech stack & context

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Layer       | What                                                  | Where                                 |
|-------------|-------------------------------------------------------|---------------------------------------|
| <e.g. TUI>  | <e.g. Textual 8.x — rooms, motion law, house palette> | `knivves/vault/`                      |
| <e.g. CLI>  | <e.g. typer/click + rich, palette mirrored>           | `knivves/cli.py`, `knivves/render.py` |
| <e.g. data> | <e.g. JSON DB, atomic writes, backups>                | `knivves/store.py`, `~/.knivves/`     |

<Context an agent needs before touching anything: standing rules, house
laws, prior closed cases that bear on this one — link them:
[closed case](../../closed/<doc>.md).>

## Design features

<One subsection per feature. Each REQ heading is an anchor other docs
link to. BINDS names exact code; ACCEPTANCE names the exact proof.>

### <Feature name>

<The feature's design in prose — the WHY and the shape. Dense, no filler.>

#### REQ-<AREA>-1 — <capability name>

- **WHAT**: <one testable capability>
- **WHY**: <the user-visible reason; cite TODO/user spec if it exists>
- **BINDS**: `<module.py>::<function/class>` · `<module.py>::<symbol>`
- **ACCEPTANCE**: `<tests/test_x.py::test_name>` — <the observable proof>

#### REQ-<AREA>-2 — <capability name>

- **WHAT**: …
- **WHY**: …
- **BINDS**: …
- **ACCEPTANCE**: …

## Cross-cutting constraints

<Rules every REQ obeys — palette laws, storage compatibility, naming,
error-handling posture. One line each, exact values.>

## Out of scope / deferred

<Named non-goals so future agents don't mistake omission for oversight.>
