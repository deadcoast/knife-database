# KNIVVES VAULT — Featured-Bar Review

Date: 2026-07-20 · Scope: the complete application, judged as one piece
against the five questions of the MIVIM standard. Conducted as a critical
walkthrough; defects found during the review were fixed in the same pass
and are listed. Taste decisions are surfaced, not decided.

---

## Q1 — What's different?

**Object permanence.** The Plate is one widget class with one visual
identity across every room: stamped into existence on the Forge Line,
docked in the Rack, seated on the Bench. No TUI in the Textual gallery
treats records as persistent physical objects that travel between screens.
This is enforced structurally (one class, `plate.py`), not by styling
convention.

**The database does its own research, visibly.** Paste a URL, watch the
record get made: fields stamp as parsed, the legal gates execute the
database's own rulebook against the listing text, a cleared record files
into the real database. Ingestion rendered as a spatial production line
with a moving record-object — not status text, not a spinner.

**Rules as living interface.** The prohibited-mechanism rulebook and the
$150 affordable rule are not settings — they are places in the app. Gates
pass and slam; the $150 line shows every knife's exact distance to it;
surveys re-tag line-crossers automatically. The user watches their own
rules operate.

**The vault surveys its own market.** One keypress re-reads every live
listing, appends price history to every record, surfaces movers by
magnitude, and reports its lifecycle on the masthead — cancellable, with
partial observations honestly kept.

## Q2 — Is it designed well?

The house laws are code, not convention (`laws.py`): one palette, one
field grammar, one motion law. Verified behaviors:

- All four rooms carry the identical chrome: masthead with brand, room
  name, live stats, and a room-state readout (sort · line state · bench
  pairing · survey lifecycle).
- Motion only ever means something moved: plates travel, replacements
  visibly depart before successors arrive, seated objects never
  re-animate, nothing fades or teleports.
- Feedback for every action: live result counts, sort direction on the
  chrome, gate counters, verdict recoloring on classification.
- Honest states everywhere: designed zero-state in the Rack, fault/
  duplicate/rejected line states in the Forge, "incomparable — missing
  measurement" on the Bench, "survey stopped — observations kept" in the
  Ledger. The app never pretends to know what the database doesn't.
- Guidance that never chases the mouse: the tip rail sits beside the
  data's last column (position asserted in tests), expandable tips earn
  their ❯ mark, the capsule holds the depth.

## Q3 — Creative and unique implementation?

- The Forge Line's transit (the record as a traveling object through
  executing legal gates) — the application's signature.
- The calipers *take the measurement*: readings appear line by line when
  a new pair forms, instantly when re-visiting a measured pair.
- The tip rail/capsule system: a designed answer to tooltips that
  respects the mouse and the layout.
- The affordable rule as geography (the $150 line with distances).

## Q4 — Has it been seen before?

The honest inventory: a themed DataTable with search is table stakes and
claims nothing. Workers and streaming updates exist in dolphie and
posting. What has no precedent in the gallery: the traveling record-
object, the visible rulebook execution, and a personal database that
re-surveys its own market with recorded history. The application's case
rests on those three, and they are real.

## Q5 — Would it impress the devs?

The framework usage is the kind Textualize showcases: workers with
cancellation and honest partial results, screen choreography through the
animation system, custom widgets with co-located CSS, command palette
integration, a Pilot test suite that drives real clicks/keys/hovers
end-to-end against a throwaway database — including simulated-input
assertions for layout laws (the plate can never clip; the rail must sit
beside the data).

**The gap this review names plainly:** the first five seconds land on the
Rack — the most conventional room. The signature (the Forge) is one
keypress away. Options, in order of restraint: lead the README with the
Forge GIF so the first impression happens before install; or add a brief
one-time boot reveal (the brand plate traveling into the masthead, ~1s,
skippable). The second is a taste decision and is left to the owner.

---

## Defects found and fixed during this review

1. Forge plate position went stale on terminal resize while idle — now
   re-seats on every resize (`on_resize` → settle).

## Known limits, documented honestly

- Single-user, single-instance: two processes writing the database race;
  last write wins (atomic file replace, no corruption).
- Live intake supports two retailers (bladescanada.com, houseofknives.ca);
  unsupported URLs fault cleanly at EXTRACT.
- Price sparklines deliberately deferred until records carry ≥3
  observations — two points is a line, not a trend.
- With a plate open in the Rack, the tip rail is covered by the plate
  (the record takes priority); tips return when the plate is dismissed.

## Verdict

The application passes its own bar on capability and coherence. The
remaining distance to "featured" is presentation: the repo page must
carry the motion (GIF/SVGs), because the argument *is* the motion.
