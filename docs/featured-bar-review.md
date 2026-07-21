# KNIVVES VAULT — Featured-Bar Review (v2)

Date: 2026-07-21 · Scope: the complete application after the escalation
slate (Vault Door, Instrument Cluster, Machined Surfaces, Rack Depth).
The v1 review is void — it graded a version the owner correctly ruled
off-radar. Every claim below is evidence-based: this review was conducted
by capturing the running app and examining the rendered frames
(docs/media/room-*.svg are the review's own exhibits).

---

## Q1 — What's different?

Unchanged from v1 and still the spine: object permanence (one Plate class
traveling every room), the self-researching database (live intake through
executing legal gates), rules as living interface, the self-surveying
market. What the escalations added is that these are now *delivered
visually*, not just architecturally:

- Rooms are **entered, not switched**: a machined vault door — drawn
  steel leaves, bolt cascade, staged parting — plays on boot (with the
  engraved brand) and on every arrival.
- The Ledger reads on **drawn instruments**: the average price rides a
  machined scale with the $150 rule cut into it in accent; the price
  distribution is gradient-lit bars with sub-cell tips.
- The chrome is **material**: the masthead is a single custom-rendered
  surface (deterministic brushed grain with the chrome stamped in);
  station headers are engravings — letterspaced caps over a bright rule.
- The rack has **depth**: the collection recedes when a plate arrives.

## Q2 — Is it designed well?

The house laws held through every escalation because they are code
(`laws.py`): one palette, one field grammar, one motion law. Verified in
the current captures: consistent chrome in all four rooms with live
state readouts; motion only where meaning is; honest states everywhere;
guidance in a reserved rail that never chases the mouse.

## Q3 — Creative and unique implementation?

The custom-render inventory now includes: SteelLeaf (door), PriceScale,
GradientBars, BrushedSteel/Engraving, plus the Plate/transit/calipers
choreography. All draw their own cells; none are styled stock widgets.

## Q4 — Has it been seen before?

The honest inventory stands: themed tables and workers exist everywhere.
No gallery project has: a record-object with cross-screen permanence, a
compliance rulebook that executes visibly, a personal database that
re-surveys its own market with recorded history — now wrapped in an
identity (machined vault) rendered rather than described.

## Q5 — Would it impress the devs?

The framework depth is the kind Textualize showcases: six custom
`render_line` widgets, staged worker choreography with honest
cancellation, screen transitions built from primitives the framework
doesn't ship, command palette integration, and a Pilot suite that
asserts layout *laws* (the plate can never clip; the tip rail must sit
beside the data; the depth nudge must return). The verification loop —
headless frame capture examined before every judgment — is itself a
development practice worth writing up in the README.

## Defects found and fixed during this review

1. **Forge eclipse**: `#forge-line` carried an explicit `layer: base`
   while the masthead and intake slot did not — the stations painted
   over both. The line is now un-layered; verified restored in
   room-forge.svg.

## Known gaps, honestly stated

- The vault door was ruled "good enough to move on, revisit later" —
  its mechanical fidelity has one more pass in it (seam detail, cadence).
- With a plate open in the Rack, the CAD column's right edge sits under
  the plate (standard drawer overlap; the plate border separates it).
  An option exists to shed covered columns instead.
- Long plate field values (SOURCE) wrap to a second line mid-grammar.
- Sparklines remain deferred until records hold ≥3 observations.
- Single-instance writes; two supported retailers; both documented.

## Verdict

The application now argues its own case on screen. The remaining
distance to "featured" is entirely release engineering: the repo page
must carry the motion — a transit GIF, the room exhibits, and a README
written as the pitch. That is the next and final phase before submission.
