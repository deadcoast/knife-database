# knivves

`knivves` is a local-first terminal database for folding knife research in Canada.

It reads and writes a plain JSON database, gives you a Rich-powered terminal UI, and supports search, filters, sorting, stats, validation, backups, import/export, retailer URLs, and small edits without leaving the CLI.

## Install natively

From inside this folder:

```bash
# with pip
# --------------------------
python -m pip install -e .

# with uv
# --------------------------
uv tool install -e .
```

Then call it from any terminal:

```bash
knivves
```

The first run copies the bundled starter database to:

```text
~/.knivves/knives.json
```

That file is your live database. Write operations create backups under:

```text
~/.knivves/backups/
```

You can also point the app at another database with:

```bash
export KNIVVES_DB=~/research/knives.json
knivves list
```

## Daily commands

```bash
knivves                         # interactive menu
knivves dashboard               # non-interactive dashboard
knivves list                    # table view
knivves list -q bugout          # search across all fields
knivves list -t clean           # filter by tag
knivves list -c approved        # approved only
knivves list --canadian         # has Canadian retailer saved
knivves list --sort price       # price sort
knivves show benchmade-bugout-axis-lock-535sl-13
knivves open benchmade-bugout-axis-lock-535sl-13
```

## Filters and output formats

```bash
knivves list --brand kizer
knivves list --steel s90v
knivves list --lock frame
knivves list --assist manual
knivves list --retailer "Blades Canada"
knivves list --flag no
knivves list --min-price 200 --max-price 600 --sort price

knivves list --output compact
knivves list --output ids
knivves list --output json
knivves list --output jsonl
knivves list --output csv > knives.csv
```

## Database views

```bash
knivves stats                   # summary cards and counts
knivves tags                    # tag index
knivves retailers               # retailer index
knivves steels                  # blade steel index
knivves urls                    # all saved retailer URLs
knivves urls bugout             # saved retailer URLs for one knife
knivves doctor                  # database health check
knivves validate                # alias for doctor
```

## Editing from the CLI

```bash
knivves add --brand Spyderco --model "Para 3" -c approved -t clean --steel S45VN
knivves classify kizer-drop-bear-zero approved
knivves approve chris-reeve-sebenza
knivves reject some-knife-id
knivves tag add benchmade-bugout-axis-lock-535sl-13 favorite
knivves tag remove benchmade-bugout-axis-lock-535sl-13 clean
knivves note benchmade-bugout-axis-lock-535sl-13 "Great lightweight EDC reference."
knivves note benchmade-bugout-axis-lock-535sl-13 "Replace the old note." --replace
```

## Retailer management

```bash
knivves retailer add benchmade-bugout-axis-lock-535sl-13 \
  --retailer "Blades Canada" \
  --url "https://example.ca/knife" \
  --price 495 \
  --availability "available"

knivves add-retailer benchmade-bugout-axis-lock-535sl-13 \
  --retailer "Blades Canada" \
  --url "https://example.ca/knife" \
  --price 495

knivves remove-retailer benchmade-bugout-axis-lock-535sl-13 1
```

## Backups, import, export

```bash
knivves path                    # active database path
knivves edit                    # open JSON in your editor
knivves backup before-research  # create timestamped backup
knivves backups                 # list backups
knivves restore ~/.knivves/backups/knives-YYYYMMDD-HHMMSS-label.json
knivves export ./knives.backup.json
knivves import ./other.knivves.json
knivves import ./other.knivves.json --replace-existing
knivves import ./other.knivves.json --replace-database
knivves reset                   # reset to bundled starter JSON, backup first
```

## Interactive controls

Inside `knivves`:

```text
number      open a row detail
s           search text
f           filter wizard
sort        sort wizard
n / p       next / previous page
o           open retailer URL for a row
stats       stats dashboard
clear       reset filters
reload      reload JSON from disk
path        show database path
?           help
q           quit
```

## JSON model

`knivves` expects a top-level `knives` array. Each knife should look like:

```json
{
  "id": "brand-model-key-variant",
  "brand": "Brand",
  "model": "Model / variant",
  "user_classification": "approved",
  "user_tags": ["clean", "fancy"],
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
      "availability": "available",
      "source_date": "YYYY-MM-DD"
    }
  ],
  "notes": "Freeform notes"
}
```
