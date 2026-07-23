# KNIVVES ╱╱ VAULT

**A personal knife-research database built as a place you enter, not an app you open.**

`knivves` is a local-first terminal application for folding-knife research in
Canada — built with [Textual](https://github.com/Textualize/textual), designed
as one coherent machine: rooms behind a vault door, records as physical
objects, your own acquisition rules executing visibly on screen.

![The Forge Line](docs/media/room-forge.svg)

## The building

Everything lives in one building with four rooms. You arrive through a
machined vault door — drawn steel leaves, a bolt cascade, staged parting —
and every record is a **plate**: one physical object with one visual
identity that travels between rooms.

### The Rack — browse

![The Rack](docs/media/room-rack.svg)

The collection. Click a column header to sort (again reverses — the active
sort reads on the masthead). `/` is a live filter across everything a
record knows. Click a knife and its plate travels in while the rack
recedes behind it. Judge from the chair: `a` approves, `x` rejects — the
row recolors, the database writes, the counts tick.

### The Forge Line — intake

The room the app is named for. Paste a retailer listing URL and watch the
vault do its own research: a blank plate appears at EXTRACT and the
listing's actually-parsed fields stamp on as they arrive; the plate
travels to LEGAL SCREEN where the database's own prohibited-mechanism
rulebook executes gate by gate — a hit slams the gate and stamps the
plate REJECTED; a cleared plate travels on and files into the real
database, already in the rack when you return. `r` replays a
deterministic no-network demo of the transit.

### The Bench — compare

![The Bench](docs/media/room-bench.svg)

Send any knife from the rack with `b` — its plate follows you here.
Between two plates, the calipers **take the measurement**: readings appear
line by line — price delta with the cheaper blade marked, blade length
delta in millimetres, spec match/differ — and hold. Gaps read
"incomparable — missing measurement": honest gaps, never guesses.

### The Ledger — price intelligence

![The Ledger](docs/media/room-ledger.svg)

The vault's money on drawn instruments: the average price rides a
machined scale with the $150 affordable rule cut into it in accent; the
price distribution is gradient-lit bars. Press `s` and the vault
**surveys its own market** — every live listing re-read, price history
appended to every record, movers surfacing by magnitude, and the
affordable rule re-tagging whatever crossed the line. Cancel anytime;
observations made are kept.

## Why it looks the way it does

The design is governed by house laws that are code, not convention
([knivves/vault/laws.py](knivves/vault/laws.py)):

1. **One palette.** Machined darks, steel text, classification colors,
   a single amber accent. No room introduces a color.
2. **One field grammar.** Every labeled value everywhere renders through
   the same function — the plate, the gates, the masthead, the bench.
3. **One motion law.** Objects travel; they never teleport and never
   fade. Every animation shares one easing.

The surfaces are drawn, not styled: the vault door's leaves, the
masthead's brushed grain, the engraved station headers, and the Ledger's
instruments are all custom `render_line` widgets that own every cell
they paint.

## Quickstart

```bash
# from this folder
uv sync          # or: python -m pip install -e .
knivves vault
```

Keys, everywhere: `1`–`4` rooms · `ctrl+p` command palette · `t` expands
the tip rail's ❯ mark into a capsule · `esc` closes/clears · `q` quits.
The mouse works on everything the keyboard does.

Your live database is a plain JSON file at `~/.knivves/knives.json`
(first run copies the bundled starter). Point elsewhere with
`KNIVVES_DB=...`. Writes are atomic; backups land in `~/.knivves/backups/`.

## The classic CLI

The original Rich CLI ships alongside the vault and works on the same
database:

```bash
knivves                          # classic interactive table
knivves list -q bugout           # search
knivves list -t affordable       # filter by tag
knivves list --min-price 200 --max-price 600 --sort price
knivves list --output csv > knives.csv
knivves show <id>                # one record
knivves approve <id>             # classification from the shell
knivves add / tag / note / retailer …
knivves backup / restore / import / export / doctor
```

## Data model

A top-level `knives` array of records:

```json
{
  "id": "brand-model-key-variant",
  "brand": "Brand",
  "model": "Model (SKU)",
  "user_classification": "approved",
  "user_tags": ["clean"],
  "research_status": "canadian_retailer_verified",
  "acquisition_status": "approved_for_further_research",
  "mechanism": {
    "opening_method": "Manual thumb stud",
    "lock_type": "Frame lock",
    "assist_type": "manual",
    "blade_length": "3.5 in",
    "blade_steel": "M390",
    "clear_prohibited_mechanism_found": false
  },
  "canadian_online_retailers": [
    {
      "retailer": "Canadian retailer name",
      "url": "https://example.ca/knife",
      "listed_price_cad": 300.0,
      "availability": "in stock",
      "source_date": "YYYY-MM-DD"
    }
  ],
  "price_history": [{ "date": "YYYY-MM-DD", "price_cad": 300.0 }],
  "notes": "Freeform notes"
}
```

The `affordable` tag is the only auto-assigned tag: any knife whose best
price sits under $150 CAD carries it; surveys re-apply the rule.

## Development notes

- **Tested by driving, not by mocking the UI**: a headless
  [Pilot suite](tests/test_vault_shell.py) boots the app against a
  throwaway database copy and drives real clicks, keys, and hovers
  through every capability — including layout laws (the traveling plate
  can never clip off-screen; the tip rail must sit beside the data's
  last column; the depth nudge must return).
- **Eyes-on verification**: during development every visual change was
  captured headlessly (`App.export_screenshot`), rendered, and examined
  before judgment — the frames in `docs/media/` are produced by that
  pipeline, not by hand.
- Scope honesty: single-user local app; live intake currently supports
  bladescanada.com and houseofknives.ca; unsupported URLs fault cleanly
  at EXTRACT.
