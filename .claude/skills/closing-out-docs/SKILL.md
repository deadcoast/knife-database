---
name: closing-out-docs
description: Use when a design spec, plan, or review has shipped or drifted from reality, or when the user says "close out the docs / closing out documentation / these docs are closed". Annotates the doc with hidden CHANGELOG_REFERENCE notes at every drifted section (canon untouched) and archives it to docs/closed/.
---

# Closing Out Documentation

## WHAT IT IS

Every document is a **case**. Opening a doc (writing a spec, a plan, a
review) creates burden and accountability: someone must eventually close
it. A doc is **closed out** when:

1. Every drift between its canon and current reality is annotated inline
   with a hidden `<!-- CHANGELOG_REFERENCE -->` note at the exact section
   it supersedes — citing `docs/CHANGELOG.md` entries (and commits where
   precision helps). **The canon text itself is never edited.**
2. A STATUS banner at the top declares it CLOSED, dates the closure, and
   warns readers not to treat unannotated details as current.
3. The file is moved to `docs/closed/` and listed in `docs/closed/INDEX.md`.

**Purpose** (the owner's words): relieve documentation bloat by holding
each and every document accountable to both opening and closing. Docs
carry absolute authority, so they are left as history — corrected where
necessary, closed out when relevant.

**Effect**: (a) accurate archiving without conflating what is LEGACY,
what was FLAWED DESIGN, and what was ALREADY CORRECTED — an agent can
assess canon, conflict, and flaw precisely; (b) frees space for new
documentation, no dead/drifted/detached design; (c) better workflow —
a design/plan doc is created, developed with the CHANGELOG as the
up-to-date record, then the CHANGELOG changes are ADDED to the outdated
spec by closing it out.

## THE NOTATION (exact syntax)

Top-of-file banner (before the H1):

```markdown
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entries": ["NNN — vX.Y.Z (date) — TITLE", ...] },
     "STATUS": "CLOSED (YYYY-MM-DD) — archived to docs/closed/ · <one-line fate>",
     "NOTE": "Canon below is the doc AS AUTHORED/WRITTEN. Drift since is annotated inline. Do not treat unannotated details as current without checking docs/CHANGELOG.md." } -->
```

Inline note, placed directly under the drifted section/claim:

```markdown
<!-- { "CHANGELOG_REFERENCE": { "file": "docs/CHANGELOG.md", "entry": "NNN — vX.Y.Z", "bullet": "<bullet name>" },
     "CHANGES": ["<VERB>: <what changed, precisely — include the shipped rule/name/signature and a commit hash when it pins the change>"] } -->
```

Controlled verbs for `CHANGES` entries — pick the honest one:

- `SUPERSEDED:` — the canon claim was true, then replaced.
- `SUPERSEDED RULE / SIGNATURE / FLAG / OUTPUT:` — precise variants.
- `ADDED AFTER AUTHORING:` — reality grew beyond the canon.
- `RENAMED AFTER AUTHORING/REVIEW:` — same thing, new name.
- `CORRECTED INTENT:` — the canon itself was a mistake (say so plainly).
- `VERSION MOVED ON:` — version/date facts that aged.
- `STANDING RULE:` — a durable rule extracted from the correction.

## HOW TO OPERATE (the procedure)

1. **Read the doc fully.** List every claim that could have drifted:
   rules, names, flags, signatures, counts, versions, verdicts, "next
   steps".
2. **Diff each claim against reality**: `docs/CHANGELOG.md` first, then
   code/tests when the changelog is coarse. Never annotate from memory.
3. **Write inline notes** at the exact drifted sections — few and
   load-bearing beats many and noisy. Canon text stays byte-identical.
4. **Write the STATUS banner** at the top.
5. **Archive**: `git mv <doc> docs/closed/` (git mv, never delete —
   history is preserved). Fix any companion-doc paths inside banners.
6. **Index**: add a row to `docs/closed/INDEX.md` (closed date, doc,
   what it was, which CHANGELOG entries it closed against).
7. **Commit** with a `docs:` message naming the closed doc(s).

## HOW TO UTILIZE (when it fires)

- The user says any of: *close out the docs, closing out documentation,
  closing the docs out, closing the docs, the docs are closed, these
  docs are closed* → run this workflow on the named doc(s).
- A spec/plan finished shipping → close it out as the final step of the
  feature (the CHANGELOG entry you just wrote is the citation source).
- You catch a doc contradicting current behavior → flag it to the user
  as a candidate for closing; don't silently rewrite its canon.
- **Reading side**: when any doc in `docs/closed/` (or any doc carrying
  a CHANGELOG_REFERENCE banner) is used as context, trust the inline
  annotations over the canon, and the CHANGELOG over both.

## HOW TO LEARN (study the exhibits)

Worked examples live in `docs/closed/`:

- `2026-07-23-ingestion-freshness-design.md` — a spec whose freshness
  rule shipped wrong and was corrected: see how SUPERSEDED RULE cites
  the exact replacement expression and commit.
- `2026-07-23-ingestion-freshness-plan.md` — a plan whose Task 9 was a
  genuine mistake, reverted: see CORRECTED INTENT + STANDING RULE
  (canon preserved, error named, rule extracted).
- `featured-bar-review.md` — a point-in-time review closed against two
  later releases: history kept accurate without rewriting the verdict.

The test of a good close-out: a future agent reading only the closed doc
must never mistake legacy for current, and must be able to find the
current truth in one hop (the cited CHANGELOG entry).
