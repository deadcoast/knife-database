<!-- { "DEV_SPEC": { "case": "<YYYY-MM-DD>-<slug>", "doc": "DS-3 TODO", "bus": "BUS-B" },
     "STATUS": "OPEN (<YYYY-MM-DD>) — this case must be closed out at checkpoint",
     "STEERED_BY": ["MIVIM-spec.yaml", ".claude/skills/mivim-agent-spec/SKILL.md", ".claude/skills/closing-out-docs/SKILL.md"],
     "LINKS": { "DS-1": "design.md", "DS-2": "requirements.md", "LIVING_RECORD": "../../CHANGELOG.md" } } -->

# <Case Title> — TODO (DS-3)

Case: `<YYYY-MM-DD>-<slug>` · Design: [design.md](design.md) · Hub: [requirements.md](requirements.md)

> These tasks are **comprehensive and module-scale** — each targets entire
> modules with effects across the source. They are not little changes.
> Work top-down; record every shipped change in the CHANGELOG; keep the
> [requirements ledger](requirements.md#requirements-ledger) statuses current.

## Tasks

### T1 — <task name>

- [ ] **T1** <the deliverable in one sentence>
  - **Satisfies**: [REQ-<AREA>-1](design.md#req-area-1--capability-name), [REQ-<AREA>-2](design.md#req-area-2--capability-name)
  - **Touches**: `<module.py>` (create/modify), `<module.py>:<region>`
  - **Done when**: <observable condition — the acceptance test(s) pass, named exactly>
  - **Proof**: `<command to run>` → <expected outcome>

### T2 — <task name>

- [ ] **T2** <deliverable>
  - **Satisfies**: [REQ-<AREA>-3](design.md#req-area-3--capability-name)
  - **Touches**: …
  - **Done when**: …
  - **Proof**: …

### T3 — <task name>

- [ ] **T3** <deliverable>
  - **Satisfies**: …
  - **Touches**: …
  - **Done when**: …
  - **Proof**: …

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
