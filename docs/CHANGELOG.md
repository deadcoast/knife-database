# CHANGELOG

## 002 — v0.5.0 (2026-07-18) — checkpoint release

Database:

- Imported all 53 knives from TODO.md into the database, deduplicated, with section provenance in notes.
- Scraped every retailer product page (Blades Canada, House of Knives) to populate CAD prices, availability, blade steel, lock type, opening method, and blade length. 64/67 knives now priced; the only unpriced records are the three without a Canadian product listing (Kunwu Albatross, Miguron Karok Teal, Kubey Zephyr).
- Renamed all records to short scannable model names ("Bel Air XL (KE-6110)"); the original verbose retailer listing title is preserved per record in `listing_title`.
- New tag rule: `affordable` is auto-assigned to any knife priced under $150 CAD and is the only non-user-assigned tag. All other tags (clean, fancy, tiered) remain user-assigned.
- Resolved all pending records with confirmed retailer links (Kizer T1-BD, Drop Bear Zero, Sebenza 31 Insingo L31-1124); added CRKT Zephyr and Kubey Gurkha; removed Kissing Crane (dead listing); Kubey Zephyr and Miguron Karok Teal kept on US/brand sources pending Canadian availability.

Interactive UI:

- Redraw now clears terminal scrollback — no more stacked stale frames.
- Page size adapts to terminal height instead of a fixed 8 rows.
- Replaced the boxed banner/summary/filter panels with a compact 2-line header.
- Table rows are always one line per knife (ellipsis truncation).
- Footer documents that typing any text is a live substring search.

## 001

The Current Repository has built out the supporting CLI, and will continue developing the CLI untill it is in a complete and working state. After the CLI is complete and the development is in a stable state, the front end web stack work will begin.

CLI Install:

```bash
cd knivves
python -m pip install -e .
```

Run the interactive CLI:

```bash
knivves
```

Useful direct commands:

```bash
knivves list
knivves list --tag clean
knivves list --classification approved
knivves list --canadian
knivves list --sort price
knivves show benchmade-bugout-axis-lock-535sl-13
knivves path
knivves export ./knives.backup.json
knivves reset
```

It creates/uses your live database here:

```text
~/.knivves/knives.json
```

What I included:

```text
knivves/
├── pyproject.toml
├── README.md
└── knivves/
    ├── __init__.py
    ├── cli.py
    ├── models.py
    ├── render.py
    ├── store.py
    └── data/
        └── knives.json
```

The CLI uses a JSON structure, with knife-name slug IDs like:

```json
"benchmade-bugout-axis-lock-535sl-13"
```

and supports filtering by:

```text
classification
tag
research status
Canadian retailer presence
search text
price / brand / model / steel sorting
```

---

## 002

Built the second-pass **`knivves` v0.2.0** CLI.

Download: [knivves-v0.2.0.zip](sandbox:/mnt/data/knivves-v0.2.0.zip)

Also kept the standard filename updated here: [knivves.zip](sandbox:/mnt/data/knivves.zip)

Install:

```bash
cd knivves
python -m pip install -e .
```

Run:

```bash
knivves
```

Major upgrades included:

```text
CLI UI
- Cleaner Rich dashboard
- Responsive table layout for narrow terminals
- Better detail panels
- Stats dashboard
- Interactive pagination
- Interactive search/filter/sort flow
- Help panel inside the interactive menu

Database output
- table / compact / json / jsonl / csv / ids outputs
- tag, retailer, steel, status indexes
- filtered exports
- CSV-friendly flattened rows
- retailer URL printing/opening
- validation/doctor command

Quality of life
- approve / reject shortcuts
- classify command
- add knife command
- add/remove retailer commands
- tag add/remove
- append/replace notes
- delete records
- automatic backups before mutations
- backup listing
- restore command
- KNIVVES_DB override support
- cleaner JSON validation
```

Useful commands:

```bash
knivves
knivves dashboard
knivves list
knivves list -q bugout
knivves list -t clean
knivves list -c approved
knivves list --canadian
knivves list --sort price
knivves list --output csv > knives.csv
knivves show benchmade-bugout-axis-lock-535sl-13
knivves open benchmade-bugout-axis-lock-535sl-13
knivves approve chris-reeve-sebenza
knivves reject some-knife-id
knivves tag add benchmade-bugout-axis-lock-535sl-13 favorite
knivves note benchmade-bugout-axis-lock-535sl-13 "Great lightweight EDC reference."
knivves retailer add chris-reeve-sebenza --retailer "Example Canada" --url "https://example.ca" --price 500
knivves doctor
knivves backup before-next-research-pass
knivves backups
```

The live database still defaults to:

```text
~/.knivves/knives.json
```

And backups go to:

```text
~/.knivves/backups/
```
