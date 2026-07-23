---
name: mivim-agent-spec
description: The MIVIM agent-spec — the central-hub development workflow for MIVIM projects. Use when opening substantial development work (a dev-spec case with design.md / requirements.md / TODO.md), when the user says "open a dev-spec", "MIVIM", mentions requirement tags or the checkpointTriggerFooter, or when a TODO's checkpoint fires. Templates ship in this skill's templates/ directory.
---

# MIVIM Agent-Spec — the Central Hub Workflow

MIVIM is always the reference for a MIVIM development project. This skill
is the hub: it defines how development documentation is opened, linked,
developed against, and closed — so an agent lands on **direct mapping in a
developmental format** instead of scouring the codebase. The data in these
docs is catered to what an agent can utilize: important details,
contextually linked, weighted — comprehensive, never frivolous.

## THE TWO BUSES

```
[BUS-A] WORKFLOW — global steering (never closes; steers every case)
  ├─ MIVIM-spec.yaml                     the quality law: impress the devs of Textual
  ├─ .claude/skills/mivim-agent-spec/    this hub
  ├─ .claude/skills/closing-out-docs/    the close-out mechanism
  └─ docs/CHANGELOG.md                   the LIVING RECORD — always current truth

[BUS-B] dev-spec (DS) — one case per development effort, three files:
  docs/dev-spec/<YYYY-MM-DD>-<slug>/
  ├─ DS-1  design.md        large-scope design: stack, context, REQ-tagged features
  ├─ DS-2  requirements.md  the navigation hub / MOC — everything linked
  └─ DS-3  TODO.md          data-dense module-scale tasks + checkpointTriggerFooter
```

BUS-A steers BUS-B. BUS-B docs are **cases**: opening one creates the
accountability to close it (see closing-out-docs). The CHANGELOG is the
only doc that is always current; DS docs are canon-of-intent and are
corrected by close-out annotation, never by silent rewriting.

## THE REQUIREMENT TAG SYSTEM (the linking spine)

Every design feature gets a grep-able ID: `REQ-<AREA>-<N>` (e.g.
`REQ-ING-1`). The ID is the join key across all three docs and the code:

- **design.md** declares it as a heading — `#### REQ-ING-1 — SLI lexer` —
  with WHAT / WHY / BINDS (exact modules & functions, e.g.
  `knivves/ingest.py::lex`) / ACCEPTANCE (the test that proves it).
- **requirements.md** indexes it in the ledger table, linking back to the
  design heading anchor and forward to its TODO tasks.
- **TODO.md** tasks cite the REQ ids they satisfy.
- Anchors: markdown heading auto-anchors (`design.md#req-ing-1--sli-lexer`);
  the raw ID stays grep-able for agents reading plain text:
  `grep -rn "REQ-ING-1" docs/dev-spec knivves tests`.

One REQ = one testable capability bound to named code. If a REQ can't
name the module it binds or the test that proves it, it is not a
requirement yet — it is scope, and belongs in design.md prose.

## HOW TO OPERATE

### Opening a case

1. Create `docs/dev-spec/<YYYY-MM-DD>-<slug>/` and instantiate the three
   templates from this skill's `templates/` directory, in order:
   design.md → requirements.md → TODO.md (each links the previous).
2. Every DS doc opens with the OPEN banner (in the templates): case id,
   DS number, status OPEN, steered-by list. Opening is a commitment —
   this case must be closed at checkpoint.
3. Commit the opened case before writing implementation code.

### Developing under an open case

- Work the TODO top-down. Tasks are **module-scale and comprehensive** —
  they target entire modules with effects across the source; never treat
  them as little changes.
- The CHANGELOG is the up-to-date record: ship a task, record the change
  there. Drift between DS canon and reality accumulates in the CHANGELOG
  — do NOT rewrite DS canon mid-case.
- Keep requirements.md's ledger statuses current (open → building →
  shipped) — it is the one glance that answers "where is this case".

### The checkpoint (the footer fires)

When every task in TODO.md is `[x]`, the `checkpointTriggerFooter` at the
bottom of TODO.md fires. Execute its protocol exactly:

1. **Close out the TODO** (closing-out-docs: CHANGELOG_REFERENCE
   annotations at drifted tasks, CLOSED banner, archive).
2. **Notify the user**: the TODO is COMPLETE, CLOSED, and a CHECKPOINT is
   reached.
3. **State the direct next objective to the user**: you will review the
   source code changes, ensure docs/CHANGELOG.md is up to date, and close
   out the design and requirements docs that accompany this TODO.
4. Execute that objective: review the diff, complete the CHANGELOG entry,
   close out DS-1 and DS-2 against it, `git mv` the whole case folder to
   `docs/closed/<case>/`, and add its row to `docs/closed/INDEX.md`.

A checkpoint is the ONLY sanctioned end of a case. Abandoning a case
without closing it is an open case with unaccounted drift — flag it.

## HOW TO UTILIZE (when this skill fires)

- The user opens substantial development ("build X", a TODO of features,
  "open a dev-spec") in a MIVIM project → open a case; don't scatter
  ad-hoc specs.
- You finish the last TODO task → the footer fires; run the checkpoint
  protocol unprompted.
- You need context mid-development → read the case's requirements.md
  FIRST (it maps documents, REQs, modules, tasks); grep REQ ids before
  searching the codebase. That is the point of the hub: direct mapping
  over discovery.
- Small fixes with no design surface (a typo, a one-line bug) do NOT open
  a case — they go straight to code + CHANGELOG. Weighted balance:
  comprehensive where it matters, never ceremonial.

## HOW TO LEARN

- Worked close-outs: `docs/closed/` — a spec whose rule shipped wrong
  (SUPERSEDED RULE), a plan task that was a mistake (CORRECTED INTENT +
  STANDING RULE), a point-in-time review aged honestly.
- The knivves v0.8.0→v0.9.0 cycle is the origin case study: design/plan
  authored → developed with the CHANGELOG carrying every correction →
  closed out against entries 004/005. This spec formalizes exactly that
  loop with the linking layer (REQ tags, requirements.md) added.
- Templates in `templates/` are canonical — instantiate, don't improvise
  the formats. The formats ARE the contract that future agents parse.
