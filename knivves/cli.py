from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import webbrowser
from datetime import date
from io import StringIO
from pathlib import Path
from shutil import which
from typing import Annotated, Any, Optional

import typer
from rich import box
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from .models import KnifeView
from .render import (
    aggregate_table,
    backups_table,
    console,
    detail_panel,
    filter_bar,
    help_panel,
    interactive_header,
    knives_table,
    raw_json_panel,
    stats_tables,
    summary_cards,
    title,
    validation_table,
)
from .store import (
    add_knife,
    backup_database,
    ensure_user_db,
    find_knife_index,
    knives_list,
    list_backups,
    load_database,
    make_knife_id,
    merge_database,
    reset_user_db,
    save_database,
    validate_database,
)

app = typer.Typer(
    name="knivves",
    help="A local, JSON-backed CLI database for folding knife research.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
)
tag_app = typer.Typer(help="Manage user tags on knives.", add_completion=False, rich_markup_mode="rich")
retailer_app = typer.Typer(help="Manage Canadian retailer entries.", add_completion=False, rich_markup_mode="rich")
app.add_typer(tag_app, name="tag")
app.add_typer(retailer_app, name="retailer")

SORT_KEYS = {"id", "brand", "model", "price", "classification", "research", "steel", "status", "retailer", "flag", "tags"}
OUTPUT_FORMATS = {"table", "compact", "json", "jsonl", "csv", "ids"}
CLASSIFICATIONS = {"approved", "rejected", "unclassified"}
FLAG_VALUES = {"yes", "no", "unknown"}


def knife_views(db: dict[str, Any]) -> list[KnifeView]:
    return [KnifeView(k) for k in db.get("knives", []) if isinstance(k, dict)]


def parse_multi(values: list[str] | None) -> list[str]:
    parsed: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                parsed.append(part)
    return parsed


def split_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def normalize_classification(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    value = value.strip().lower()
    if value not in CLASSIFICATIONS:
        raise typer.BadParameter("classification must be approved, rejected, or unclassified")
    return None if value == "unclassified" else value


def filter_knives(
    knives: list[KnifeView],
    *,
    query: str | None = None,
    classification: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    canadian: bool | None = None,
    brand: str | None = None,
    steel: str | None = None,
    lock: str | None = None,
    assist: str | None = None,
    retailer: str | None = None,
    flag: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[KnifeView]:
    result = knives
    if query:
        q = query.lower().strip()
        result = [k for k in result if q in k.haystack()]
    if classification:
        c = classification.lower().strip()
        result = [k for k in result if k.classification == c]
    if tags:
        wanted = {tag.lower().strip() for tag in tags if tag.strip()}
        result = [k for k in result if wanted.issubset({tag.lower() for tag in k.tags})]
    if status:
        s = status.lower().strip()
        result = [k for k in result if s in k.research_status.lower() or s in k.acquisition_status.lower()]
    if canadian is not None:
        result = [k for k in result if k.has_canadian_retailer == canadian]
    if brand:
        b = brand.lower().strip()
        result = [k for k in result if b in k.brand.lower()]
    if steel:
        st = steel.lower().strip()
        result = [k for k in result if st in k.blade_steel.lower()]
    if lock:
        l = lock.lower().strip()
        result = [k for k in result if l in k.lock_type.lower()]
    if assist:
        a = assist.lower().strip()
        result = [k for k in result if a in k.assist_type.lower() or a in k.opening_method.lower()]
    if retailer:
        r = retailer.lower().strip()
        result = [k for k in result if any(r in name.lower() for name in k.retailer_names)]
    if flag:
        f = flag.lower().strip()
        if f not in FLAG_VALUES:
            raise typer.BadParameter("flag must be yes, no, or unknown")
        result = [k for k in result if k.prohibited_flag == f]
    if min_price is not None:
        result = [k for k in result if k.price is not None and k.price >= min_price]
    if max_price is not None:
        result = [k for k in result if k.price is not None and k.price <= max_price]
    return result


def sort_knives(knives: list[KnifeView], sort_by: str = "brand", reverse: bool = False) -> list[KnifeView]:
    if sort_by not in SORT_KEYS:
        raise typer.BadParameter(f"sort must be one of: {', '.join(sorted(SORT_KEYS))}")

    def price_key(k: KnifeView) -> tuple[bool, float, str]:
        return (k.price is None, k.price if k.price is not None else 0.0, k.brand)

    key_map = {
        "id": lambda k: (k.id,),
        "brand": lambda k: (k.brand.lower(), k.model.lower()),
        "model": lambda k: (k.model.lower(), k.brand.lower()),
        "price": price_key,
        "classification": lambda k: (k.classification, k.brand.lower(), k.model.lower()),
        "research": lambda k: (k.research_status, k.brand.lower(), k.model.lower()),
        "steel": lambda k: (k.blade_steel.lower(), k.brand.lower(), k.model.lower()),
        "status": lambda k: (k.acquisition_status, k.brand.lower(), k.model.lower()),
        "retailer": lambda k: (k.retailer_count == 0, (k.retailer_names[0].lower() if k.retailer_names else ""), k.brand.lower()),
        "flag": lambda k: (k.prohibited_flag, k.brand.lower(), k.model.lower()),
        "tags": lambda k: (",".join(k.tags).lower(), k.brand.lower(), k.model.lower()),
    }
    return sorted(knives, key=key_map[sort_by], reverse=reverse)


def resolve_knife(db: dict[str, Any], identifier: str) -> tuple[int, KnifeView] | None:
    key = identifier.lower().strip()
    raw_knives = knives_list(db)
    views = [KnifeView(k) for k in raw_knives]
    exact = [(i, k) for i, k in enumerate(views) if k.id.lower() == key]
    if exact:
        return exact[0]
    matches = [(i, k) for i, k in enumerate(views) if key in k.haystack()]
    if len(matches) == 1:
        return matches[0]
    if matches:
        console.print(knives_table([k for _, k in matches], show_id=True))
        console.print("[yellow]Multiple matches. Use the exact ID from the table.[/]")
    return None


def render_or_emit(knives: list[KnifeView], output: str, *, compact: bool = False, show_id: bool = False) -> None:
    if output not in OUTPUT_FORMATS:
        raise typer.BadParameter(f"output must be one of: {', '.join(sorted(OUTPUT_FORMATS))}")
    if output == "json":
        console.print_json(json.dumps([k.raw for k in knives], ensure_ascii=False))
    elif output == "jsonl":
        for knife in knives:
            sys.stdout.write(json.dumps(knife.raw, ensure_ascii=False) + "\n")
    elif output == "csv":
        rows = [k.flat() for k in knives]
        if not rows:
            return
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        sys.stdout.write(buffer.getvalue())
    elif output == "ids":
        for knife in knives:
            sys.stdout.write(knife.id + "\n")
    else:
        console.print(knives_table(knives, compact=compact or output == "compact", show_id=show_id))


def current_filter_dict(**kwargs: object) -> dict[str, object]:
    return {key: value for key, value in kwargs.items() if value not in (None, "", [], {})}


def run_list(
    *,
    query: str | None = None,
    classification: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    canadian: bool | None = None,
    brand: str | None = None,
    steel: str | None = None,
    lock: str | None = None,
    assist: str | None = None,
    retailer: str | None = None,
    flag: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort_by: str = "brand",
    reverse: bool = False,
    limit: int | None = None,
    output: str = "table",
    compact: bool = False,
    show_id: bool = False,
    summary: bool = True,
) -> list[KnifeView]:
    db = load_database()
    all_knives = knife_views(db)
    filtered = filter_knives(
        all_knives,
        query=query,
        classification=classification,
        tags=tags,
        status=status,
        canadian=canadian,
        brand=brand,
        steel=steel,
        lock=lock,
        assist=assist,
        retailer=retailer,
        flag=flag,
        min_price=min_price,
        max_price=max_price,
    )
    filtered = sort_knives(filtered, sort_by, reverse=reverse)
    if limit is not None:
        filtered = filtered[: max(limit, 0)]
    if output in {"table", "compact"}:
        console.print(title())
        if summary:
            console.print(filter_bar(current_filter_dict(query=query, classification=classification, tags=tags, status=status, canadian=canadian, brand=brand, steel=steel, lock=lock, assist=assist, retailer=retailer, flag=flag, min_price=min_price, max_price=max_price, sort=sort_by, reverse=reverse), len(filtered), len(all_knives)))
    render_or_emit(filtered, output, compact=compact, show_id=show_id)
    if output in {"table", "compact"}:
        console.print(f"[dim]{len(filtered)} result(s)[/]")
    return filtered


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Open the interactive database when called as plain [bold]knivves[/]."""
    if ctx.invoked_subcommand is None:
        interactive()


@app.command(name="list")
def list_command(
    query: Annotated[Optional[str], typer.Option("--query", "-q", help="Search text across all knife fields.")] = None,
    classification: Annotated[Optional[str], typer.Option("--classification", "-c", help="approved, rejected, or unclassified.")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Filter by tag. Repeat or comma-separate.")] = None,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter by research/acquisition status text.")] = None,
    canadian: Annotated[Optional[bool], typer.Option("--canadian/--not-canadian", help="Filter by saved Canadian retailer presence.")] = None,
    brand: Annotated[Optional[str], typer.Option("--brand", "-b", help="Filter by brand text.")] = None,
    steel: Annotated[Optional[str], typer.Option("--steel", help="Filter by blade steel text.")] = None,
    lock: Annotated[Optional[str], typer.Option("--lock", help="Filter by lock type text.")] = None,
    assist: Annotated[Optional[str], typer.Option("--assist", help="Filter by assist/opening text.")] = None,
    retailer: Annotated[Optional[str], typer.Option("--retailer", "-r", help="Filter by Canadian retailer name.")] = None,
    flag: Annotated[Optional[str], typer.Option("--flag", help="Filter clear prohibited mechanism flag: yes, no, unknown.")] = None,
    min_price: Annotated[Optional[float], typer.Option("--min-price", help="Minimum listed CAD price.")] = None,
    max_price: Annotated[Optional[float], typer.Option("--max-price", help="Maximum listed CAD price.")] = None,
    sort_by: Annotated[str, typer.Option("--sort", help="id, brand, model, price, classification, research, steel, status, retailer, flag, tags.")] = "brand",
    reverse: Annotated[bool, typer.Option("--reverse", help="Reverse sort order.")] = False,
    limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="Limit result count.")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="table, compact, json, jsonl, csv, or ids.")] = "table",
    compact: Annotated[bool, typer.Option("--compact", help="Use compact table columns.")] = False,
    show_id: Annotated[bool, typer.Option("--show-id", help="Show slug IDs in table.")] = False,
    no_summary: Annotated[bool, typer.Option("--no-summary", help="Hide filter summary above the table.")] = False,
) -> None:
    """List knives with search, filters, sorting, and multiple output formats."""
    c = normalize_classification(classification) if classification else None
    c = "unclassified" if classification == "unclassified" else c
    run_list(
        query=query,
        classification=c,
        tags=parse_multi(tag),
        status=status,
        canadian=canadian,
        brand=brand,
        steel=steel,
        lock=lock,
        assist=assist,
        retailer=retailer,
        flag=flag,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        reverse=reverse,
        limit=limit,
        output=output,
        compact=compact,
        show_id=show_id,
        summary=not no_summary,
    )


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Text to search across the database.")],
    output: Annotated[str, typer.Option("--output", "-o", help="table, compact, json, jsonl, csv, or ids.")] = "table",
    sort_by: Annotated[str, typer.Option("--sort", help="Sort key.")] = "brand",
) -> None:
    """Fast search shortcut."""
    run_list(query=query, output=output, sort_by=sort_by, show_id=True)


@app.command()
def dashboard() -> None:
    """Show a polished database overview without entering interactive mode."""
    db = load_database()
    knives = knife_views(db)
    console.print(title())
    console.print(summary_cards(db, knives))
    console.print(stats_tables(knives))


@app.command()
def show(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    raw: Annotated[bool, typer.Option("--json", help="Print raw JSON for this knife.")] = False,
    open_url: Annotated[bool, typer.Option("--open", help="Open the first saved retailer URL in your browser.")] = False,
) -> None:
    """Show full details for one knife."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    _, knife = found
    if raw:
        console.print_json(json.dumps(knife.raw, ensure_ascii=False))
    else:
        console.print(detail_panel(knife, include_json=False))
    if open_url:
        open_first_url(knife)


@app.command(name="open")
def open_command(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    retailer_index: Annotated[int, typer.Option("--retailer", "-r", help="Retailer number from the detail view, starting at 1.")] = 1,
    print_only: Annotated[bool, typer.Option("--print", help="Print the URL instead of opening a browser.")] = False,
) -> None:
    """Open a saved retailer URL for a knife."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    _, knife = found
    retailers = knife.retailers
    if not retailers:
        console.print("[yellow]No retailer URL saved for that knife.[/]")
        raise typer.Exit(code=1)
    idx = retailer_index - 1
    if idx < 0 or idx >= len(retailers):
        console.print(f"[red]Retailer index out of range. Saved retailers: {len(retailers)}[/]")
        raise typer.Exit(code=1)
    url = str(retailers[idx].get("url") or "")
    if not url:
        console.print("[yellow]Selected retailer has no URL.[/]")
        raise typer.Exit(code=1)
    if print_only:
        console.print(url)
    else:
        webbrowser.open(url)
        console.print(f"[green]Opened:[/] {url}")


@app.command()
def urls(
    identifier: Annotated[Optional[str], typer.Argument(help="Optional knife search. Omit to print all saved URLs.")] = None,
) -> None:
    """Print saved Canadian retailer URLs."""
    db = load_database()
    knives = knife_views(db)
    if identifier:
        found = resolve_knife(db, identifier)
        if not found:
            console.print(f"[red]No unique knife found for:[/] {identifier}")
            raise typer.Exit(code=1)
        knives = [found[1]]
    for knife in knives:
        for retailer in knife.retailers:
            url = retailer.get("url")
            if url:
                console.print(f"[bold]{knife.id}[/]  [cyan]{retailer.get('retailer', 'retailer')}[/]\n{url}")


@app.command()
def stats() -> None:
    """Show database statistics."""
    db = load_database()
    knives = knife_views(db)
    console.print(title())
    console.print(summary_cards(db, knives))
    console.print(stats_tables(knives))


@app.command()
def tags() -> None:
    """Show all user tags and counts."""
    db = load_database()
    console.print(aggregate_table(knife_views(db), "tags"))


@app.command()
def retailers() -> None:
    """Show all Canadian retailers and counts."""
    db = load_database()
    console.print(aggregate_table(knife_views(db), "retailers"))


@app.command()
def steels() -> None:
    """Show blade steels and counts."""
    db = load_database()
    console.print(aggregate_table(knife_views(db), "steels"))


@app.command()
def path() -> None:
    """Print the active JSON database path."""
    console.print(str(ensure_user_db()))


@app.command()
def edit() -> None:
    """Open the active JSON database in your editor."""
    db_path = ensure_user_db()
    candidates = []
    if os.environ.get("EDITOR"):
        candidates.append(os.environ["EDITOR"])
    candidates.extend(["code", "cursor", "nano", "vim", "notepad"])
    for candidate in candidates:
        exe = candidate.split()[0]
        if which(exe):
            subprocess.run(candidate.split() + [str(db_path)], check=False)
            return
    console.print(f"[yellow]Open manually:[/] {db_path}")


@app.command()
def export(
    output: Annotated[Path, typer.Argument(help="Output JSON path.")],
    minified: Annotated[bool, typer.Option("--minified", help="Write compact JSON instead of pretty JSON.")] = False,
) -> None:
    """Export the active database to another JSON path."""
    db = load_database()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        if minified:
            json.dump(db, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(db, f, indent=2, ensure_ascii=False)
            f.write("\n")
    console.print(f"[green]Exported:[/] {output}")


@app.command(name="import")
def import_command(
    input_path: Annotated[Path, typer.Argument(help="Input JSON file containing a full database or top-level knives list.")],
    replace_existing: Annotated[bool, typer.Option("--replace-existing", help="Update records with matching IDs during merge.")] = False,
    replace_database: Annotated[bool, typer.Option("--replace-database", help="Replace the entire active database.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")] = False,
) -> None:
    """Import or merge another knivves JSON database."""
    with input_path.open("r", encoding="utf-8") as f:
        incoming = json.load(f)
    if isinstance(incoming, list):
        incoming = {"knives": incoming}
    if not isinstance(incoming, dict):
        console.print("[red]Input JSON must be an object or a list of knife objects.[/]")
        raise typer.Exit(code=1)

    if replace_database:
        if not yes and not Confirm.ask("Replace the entire active database?", default=False):
            raise typer.Exit(code=0)
        backup = backup_database("before-replace")
        save_database(incoming)
        console.print(f"[green]Replaced database.[/] Backup: {backup}")
        return

    db = load_database()
    backup = backup_database("before-import")
    added, updated = merge_database(db, incoming, replace_existing=replace_existing)
    save_database(db)
    console.print(f"[green]Imported.[/] Added {added}, updated {updated}. Backup: {backup}")


@app.command()
def backup(label: Annotated[Optional[str], typer.Argument(help="Optional backup label.")] = None) -> None:
    """Create a timestamped backup of the active database."""
    backup_path = backup_database(label or "manual")
    console.print(f"[green]Backup created:[/] {backup_path}")


@app.command()
def backups() -> None:
    """List saved database backups."""
    console.print(backups_table(list_backups()))


@app.command()
def reset(yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False) -> None:
    """Reset ~/.knivves/knives.json to the bundled starter database."""
    if yes or Confirm.ask("Reset your local knivves database to the bundled starter JSON?", default=False):
        backup = backup_database("before-reset") if ensure_user_db().exists() else None
        console.print(f"[green]Reset:[/] {reset_user_db()}")
        if backup:
            console.print(f"[dim]Backup: {backup}[/]")


@app.command()
def doctor() -> None:
    """Validate the active JSON database and show structural issues."""
    db = load_database()
    issues = validate_database(db)
    console.print(title())
    console.print(validation_table(issues))
    errors = sum(1 for issue in issues if issue.severity == "error")
    if errors:
        raise typer.Exit(code=1)


@app.command()
def add(
    brand: Annotated[Optional[str], typer.Option("--brand", "-b", help="Knife brand.")] = None,
    model: Annotated[Optional[str], typer.Option("--model", "-m", help="Knife model.")] = None,
    classification: Annotated[Optional[str], typer.Option("--classification", "-c", help="approved, rejected, or unclassified.")] = None,
    tags: Annotated[Optional[str], typer.Option("--tags", "-t", help="Comma-separated tags.")] = None,
    retailer: Annotated[Optional[str], typer.Option("--retailer", "-r", help="Canadian retailer name.")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Retailer or source URL.")] = None,
    price: Annotated[Optional[float], typer.Option("--price", help="Listed CAD price.")] = None,
    availability: Annotated[Optional[str], typer.Option("--availability", help="Retailer availability text.")] = None,
    opening: Annotated[Optional[str], typer.Option("--opening", help="Opening method.")] = None,
    lock: Annotated[Optional[str], typer.Option("--lock", help="Lock type.")] = None,
    assist: Annotated[Optional[str], typer.Option("--assist", help="Assist type.")] = None,
    blade_length: Annotated[Optional[str], typer.Option("--blade-length", help="Blade length.")] = None,
    steel: Annotated[Optional[str], typer.Option("--steel", help="Blade steel.")] = None,
    prohibited: Annotated[Optional[bool], typer.Option("--prohibited/--not-prohibited", help="Clear prohibited mechanism flag.")] = None,
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="Notes.")] = None,
) -> None:
    """Add a knife record from the CLI."""
    brand = brand or Prompt.ask("Brand").strip()
    model = model or Prompt.ask("Model").strip()
    classification_norm = normalize_classification(classification) if classification else None
    db = load_database()
    has_retailer = bool(retailer or url)
    retailer_entry = []
    if has_retailer:
        retailer_entry.append(
            {
                "retailer": retailer or "Unknown retailer",
                "url": url or "",
                "listed_price_cad": price,
                "availability": availability or "unknown",
                "source_date": date.today().isoformat(),
            }
        )
    record = {
        "id": make_knife_id(brand, model),
        "brand": brand,
        "model": model,
        "user_classification": classification_norm,
        "user_tags": split_tags(tags),
        "research_status": "canadian_retailer_verified" if has_retailer else "pending_canadian_retailer_search",
        "acquisition_status": "approved_for_further_research" if classification_norm == "approved" or has_retailer else "pending_research",
        "mechanism": {
            "opening_method": opening,
            "lock_type": lock,
            "assist_type": assist or "unknown",
            "blade_length": blade_length,
            "blade_steel": steel,
            "clear_prohibited_mechanism_found": prohibited,
        },
        "canadian_online_retailers": retailer_entry,
        "notes": notes or "",
    }
    backup = backup_database("before-add")
    added = add_knife(db, record)
    save_database(db)
    console.print(f"[green]Added:[/] {added['id']}  [dim]Backup: {backup}[/]")
    console.print(detail_panel(KnifeView(added)))


@app.command()
def classify(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    classification: Annotated[str, typer.Argument(help="approved, rejected, or unclassified.")],
) -> None:
    """Set a knife's user classification."""
    normalized = normalize_classification(classification)
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, _ = found
    backup = backup_database("before-classify")
    knives_list(db)[idx]["user_classification"] = normalized
    save_database(db)
    console.print(f"[green]Updated classification.[/] Backup: {backup}")
    console.print(detail_panel(KnifeView(knives_list(db)[idx])))


@app.command()
def note(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    text: Annotated[Optional[str], typer.Argument(help="Note text. Omit to type interactively.")] = None,
    replace: Annotated[bool, typer.Option("--replace", help="Replace existing notes instead of appending.")] = False,
) -> None:
    """Append or replace a knife note."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, knife = found
    text = text if text is not None else Prompt.ask("Note").strip()
    record = knives_list(db)[idx]
    old = str(record.get("notes") or "")
    record["notes"] = text if replace or not old else old.rstrip() + "\n" + text
    backup = backup_database("before-note")
    save_database(db)
    console.print(f"[green]Updated note.[/] Backup: {backup}")
    console.print(detail_panel(KnifeView(record)))


@app.command()
def delete(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Delete a knife record from the local database."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, knife = found
    if not yes and not Confirm.ask(f"Delete {knife.display_name}?", default=False):
        raise typer.Exit(code=0)
    backup = backup_database("before-delete")
    del knives_list(db)[idx]
    save_database(db)
    console.print(f"[green]Deleted:[/] {knife.id}  [dim]Backup: {backup}[/]")


@tag_app.command(name="list")
def tag_list() -> None:
    """Show all tags and counts."""
    tags()


@tag_app.command(name="add")
def tag_add(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    tag: Annotated[str, typer.Argument(help="Tag to add.")],
) -> None:
    """Add a tag to a knife."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, _ = found
    record = knives_list(db)[idx]
    current = [str(t) for t in record.get("user_tags") or []]
    if tag not in current:
        current.append(tag)
    record["user_tags"] = current
    backup = backup_database("before-tag-add")
    save_database(db)
    console.print(f"[green]Tag added.[/] Backup: {backup}")
    console.print(detail_panel(KnifeView(record)))


@tag_app.command(name="remove")
def tag_remove(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    tag: Annotated[str, typer.Argument(help="Tag to remove.")],
) -> None:
    """Remove a tag from a knife."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, _ = found
    record = knives_list(db)[idx]
    current = [str(t) for t in record.get("user_tags") or []]
    record["user_tags"] = [t for t in current if t != tag]
    backup = backup_database("before-tag-remove")
    save_database(db)
    console.print(f"[green]Tag removed.[/] Backup: {backup}")
    console.print(detail_panel(KnifeView(record)))


@retailer_app.command(name="add")
def retailer_add(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    retailer: Annotated[str, typer.Option("--retailer", "-r", help="Canadian retailer name.")],
    url: Annotated[str, typer.Option("--url", help="Retailer URL.")],
    price: Annotated[Optional[float], typer.Option("--price", help="Listed CAD price.")] = None,
    availability: Annotated[str, typer.Option("--availability", "-a", help="Availability text.")] = "unknown",
) -> None:
    """Add a Canadian retailer source to a knife."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, _ = found
    record = knives_list(db)[idx]
    record.setdefault("canadian_online_retailers", []).append(
        {
            "retailer": retailer,
            "url": url,
            "listed_price_cad": price,
            "availability": availability,
            "source_date": date.today().isoformat(),
        }
    )
    record["research_status"] = "canadian_retailer_verified"
    if record.get("user_classification") != "rejected":
        record["acquisition_status"] = "approved_for_further_research"
    mechanism = record.setdefault("mechanism", {})
    if mechanism.get("clear_prohibited_mechanism_found") is None:
        mechanism["clear_prohibited_mechanism_found"] = False
    backup = backup_database("before-retailer-add")
    save_database(db)
    console.print(f"[green]Retailer added.[/] Backup: {backup}")
    console.print(detail_panel(KnifeView(record)))


def open_first_url(knife: KnifeView) -> None:
    retailer = knife.best_retailer
    if not retailer or not retailer.get("url"):
        console.print("[yellow]No retailer URL saved for this knife.[/]")
        return
    url = str(retailer["url"])
    webbrowser.open(url)
    console.print(f"[green]Opened:[/] {url}")


def interactive() -> None:
    db = load_database()
    page = 0
    state: dict[str, Any] = {
        "query": None,
        "classification": None,
        "tags": [],
        "status": None,
        "canadian": None,
        "brand": None,
        "steel": None,
        "lock": None,
        "assist": None,
        "retailer": None,
        "flag": None,
        "min_price": None,
        "max_price": None,
    }
    current_sort = "brand"
    reverse = False

    while True:
        # Header (2) + table frame (4) + footer/prompt (4) leave the rest for rows.
        page_size = max(8, console.size.height - 10)
        all_knives = knife_views(db)
        filtered_all = sort_knives(filter_knives(all_knives, **state), current_sort, reverse=reverse)
        total_pages = max(1, (len(filtered_all) + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        start = page * page_size
        page_items = filtered_all[start : start + page_size]

        console.clear()
        # Also wipe scrollback so stale frames don't pile up above the live one.
        print("\x1b[3J", end="", flush=True)
        console.print(interactive_header(db, all_knives, {**state, "sort": current_sort, "reverse": reverse}, len(filtered_all)))
        console.print(knives_table(page_items, start_index=start, compact=False))
        console.print(f"[dim]Page {page + 1}/{total_pages} · rows {start + 1}-{min(start + len(page_items), len(filtered_all))} of {len(filtered_all)}[/]")
        console.print("[bold cyan]Commands[/] type text → search · row number → detail · n/p page · s search · f filters · sort · o open · stats · clear · reload · path · ? help · q quit")
        choice = Prompt.ask("knivves", default="?").strip()
        choice_l = choice.lower()

        if choice_l in {"q", "quit", "exit"}:
            break
        if choice_l in {"?", "h", "help"}:
            console.print(help_panel())
            Prompt.ask("Press Enter", default="")
            continue
        if choice_l in {"n", "next"}:
            page = min(page + 1, total_pages - 1)
            continue
        if choice_l in {"p", "prev", "previous"}:
            page = max(page - 1, 0)
            continue
        if choice_l in {"s", "search"}:
            state["query"] = Prompt.ask("Search text", default=state.get("query") or "").strip() or None
            page = 0
            continue
        if choice_l in {"sort", "order"}:
            current_sort = Prompt.ask("Sort by", choices=sorted(SORT_KEYS), default=current_sort)
            reverse = Confirm.ask("Reverse sort?", default=reverse)
            page = 0
            continue
        if choice_l in {"clear", "reset filters"}:
            for key in state:
                state[key] = [] if key == "tags" else None
            current_sort = "brand"
            reverse = False
            page = 0
            continue
        if choice_l == "reload":
            db = load_database()
            continue
        if choice_l == "path":
            console.print(f"[green]{ensure_user_db()}[/]")
            Prompt.ask("Press Enter", default="")
            continue
        if choice_l == "stats":
            console.print(stats_tables(all_knives))
            Prompt.ask("Press Enter", default="")
            continue
        if choice_l in {"f", "filter", "filters"}:
            filter_menu = Table(box=box.SIMPLE)
            filter_menu.add_column("Filter")
            filter_menu.add_column("Current")
            filter_menu.add_row("classification", str(state["classification"] or "any"))
            filter_menu.add_row("tag", ", ".join(state["tags"]) if state["tags"] else "any")
            filter_menu.add_row("status", str(state["status"] or "any"))
            filter_menu.add_row("canadian", str(state["canadian"] if state["canadian"] is not None else "any"))
            filter_menu.add_row("brand", str(state["brand"] or "any"))
            filter_menu.add_row("steel", str(state["steel"] or "any"))
            filter_menu.add_row("retailer", str(state["retailer"] or "any"))
            filter_menu.add_row("flag", str(state["flag"] or "any"))
            console.print(filter_menu)
            field = Prompt.ask(
                "Filter field",
                choices=["classification", "tag", "status", "canadian", "brand", "steel", "lock", "assist", "retailer", "flag", "price"],
                default="classification",
            )
            if field == "classification":
                value = Prompt.ask("Classification", choices=["approved", "rejected", "unclassified", "any"], default="approved")
                state["classification"] = None if value == "any" else value
            elif field == "tag":
                value = Prompt.ask("Tags, comma-separated; blank for any", default=", ".join(state["tags"]))
                state["tags"] = split_tags(value)
            elif field == "status":
                value = Prompt.ask("Status contains; blank for any", default=state.get("status") or "")
                state["status"] = value.strip() or None
            elif field == "canadian":
                value = Prompt.ask("Canadian retailer?", choices=["yes", "no", "any"], default="yes")
                state["canadian"] = True if value == "yes" else False if value == "no" else None
            elif field in {"brand", "steel", "lock", "assist", "retailer"}:
                value = Prompt.ask(f"{field.title()} contains; blank for any", default=state.get(field) or "")
                state[field] = value.strip() or None
            elif field == "flag":
                value = Prompt.ask("Clear prohibited mechanism found?", choices=["yes", "no", "unknown", "any"], default="no")
                state["flag"] = None if value == "any" else value
            elif field == "price":
                min_v = Prompt.ask("Minimum CAD; blank for none", default="")
                max_v = Prompt.ask("Maximum CAD; blank for none", default="")
                state["min_price"] = float(min_v) if min_v.strip() else None
                state["max_price"] = float(max_v) if max_v.strip() else None
            page = 0
            continue
        if choice_l in {"o", "open"}:
            if not page_items:
                continue
            row = IntPrompt.ask("Open row number", default=start + 1)
            idx = row - 1
            if 0 <= idx < len(filtered_all):
                open_first_url(filtered_all[idx])
                Prompt.ask("Press Enter", default="")
            continue
        if choice_l.isdigit():
            idx = int(choice_l) - 1
            if 0 <= idx < len(filtered_all):
                knife = filtered_all[idx]
                console.clear()
                console.print(detail_panel(knife, include_json=Confirm.ask("Include raw JSON?", default=False)))
                Prompt.ask("Press Enter", default="")
            continue
        # Fallback: treat unknown input as quick search.
        state["query"] = choice
        page = 0


@app.command()
def approve(identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")]) -> None:
    """Shortcut: set a knife's user classification to approved."""
    classify(identifier, "approved")


@app.command()
def reject(identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")]) -> None:
    """Shortcut: set a knife's user classification to rejected."""
    classify(identifier, "rejected")


@app.command(name="validate")
def validate_alias() -> None:
    """Alias for doctor."""
    doctor()


@app.command(name="add-retailer")
def add_retailer_alias(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    retailer: Annotated[str, typer.Option("--retailer", "-r", help="Canadian retailer name.")],
    url: Annotated[str, typer.Option("--url", help="Retailer URL.")],
    price: Annotated[Optional[float], typer.Option("--price", help="Listed CAD price.")] = None,
    availability: Annotated[str, typer.Option("--availability", "-a", help="Availability text.")] = "unknown",
) -> None:
    """Shortcut for `knivves retailer add`."""
    retailer_add(identifier, retailer=retailer, url=url, price=price, availability=availability)


@app.command(name="remove-retailer")
def remove_retailer(
    identifier: Annotated[str, typer.Argument(help="Knife ID, brand, model, or search text.")],
    retailer_index: Annotated[int, typer.Argument(help="Retailer number from detail view, starting at 1.")] = 1,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Remove a saved retailer from a knife."""
    db = load_database()
    found = resolve_knife(db, identifier)
    if not found:
        console.print(f"[red]No unique knife found for:[/] {identifier}")
        raise typer.Exit(code=1)
    idx, knife = found
    retailers = knives_list(db)[idx].setdefault("canadian_online_retailers", [])
    remove_idx = retailer_index - 1
    if remove_idx < 0 or remove_idx >= len(retailers):
        console.print(f"[red]Retailer index out of range. Saved retailers: {len(retailers)}[/]")
        raise typer.Exit(code=1)
    target = retailers[remove_idx]
    name = target.get("retailer", "retailer") if isinstance(target, dict) else "retailer"
    if not yes and not Confirm.ask(f"Remove {name} from {knife.display_name}?", default=False):
        raise typer.Exit(code=0)
    backup = backup_database("before-retailer-remove")
    del retailers[remove_idx]
    record = knives_list(db)[idx]
    if not retailers:
        record["research_status"] = "pending_canadian_retailer_search"
        if record.get("user_classification") != "rejected":
            record["acquisition_status"] = "pending_research"
    save_database(db)
    console.print(f"[green]Retailer removed.[/] Backup: {backup}")
    console.print(detail_panel(KnifeView(record)))


@app.command()
def restore(
    backup_path: Annotated[Path, typer.Argument(help="Path to a backup JSON file.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Restore a database backup."""
    if not yes and not Confirm.ask(f"Restore backup {backup_path}?", default=False):
        raise typer.Exit(code=0)
    from .store import restore_backup

    restored = restore_backup(backup_path)
    console.print(f"[green]Restored:[/] {restored}")


if __name__ == "__main__":
    app()
