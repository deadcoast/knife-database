<!-- { "DEV_SPEC": { "case": "<YYYY-MM-DD>-<slug>", "doc": "DS-2 requirements", "bus": "BUS-B" },
     "STATUS": "OPEN (<YYYY-MM-DD>) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-1": "design.md", "DS-3": "TODO.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# <Case Title> — Requirements Hub (DS-2)

Case: `<YYYY-MM-DD>-<slug>` · The navigation hub: every document, every
requirement, every binding — one glance, one hop. **Read this file first.**

## Document registry

<!-- tables are authored minimally spaced; the user's markdownlint realigns them on disk — NORMAL OPERATION, never revert -->

| Doc                                        | Role                                          | Read it when                               |
|--------------------------------------------|-----------------------------------------------|--------------------------------------------|
| [design.md](design.md)                     | DS-1 — the design canon, REQ definitions      | you need the WHY or the shape of a feature |
| [TODO.md](TODO.md)                         | DS-3 — module-scale tasks + checkpoint footer | you need what to do next                   |
| [../../CHANGELOG.md](../../CHANGELOG.md)   | BUS-A living record                           | you need what is CURRENTLY true            |
| `<source module>`                          | <one row per module this case touches>        | <what lives there>                         |
| [../../closed/<related>.md](../../closed/) | prior closed case(s) bearing on this one      | history, standing rules                    |

## Requirements ledger

<The dense joint table. Status: open → building → shipped. Keep current —
this table is the case's single glance.>

| REQ          | Capability | Design                                     | Tasks                              | Binds                   | Proof               | Status |
|--------------|------------|--------------------------------------------|------------------------------------|-------------------------|---------------------|--------|
| REQ-<AREA>-1 | <name>     | [§](design.md#req-area-1--capability-name) | [T1](TODO.md#t1)                   | `<module.py>::<symbol>` | `<test file::name>` | open   |
| REQ-<AREA>-2 | <name>     | [§](design.md#req-area-2--capability-name) | [T1](TODO.md#t1), [T3](TODO.md#t3) | `<module.py>::<symbol>` | `<test file::name>` | open   |

## Tag map

<SectionID-style tags grouping REQs by theme, so agents can pull a slice:>

- `#<tag>` — REQ-<AREA>-1, REQ-<AREA>-2
- `#<tag>` — REQ-<AREA>-3

## Standing rules in force

<Rules from BUS-A / memory / prior close-outs that constrain this case —
one line each, with links. e.g. "ingestion .md files are one-shot intake
batches — docs/closed/2026-07-23-ingestion-freshness-plan.md (Task 9 note)".>
