from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable

from rich import box
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .models import KnifeView

console = Console()


def badge(value: str | None) -> str:
    raw = str(value or "unknown")
    clean = escape(raw.replace("_", " "))
    low = raw.lower()
    if low in {"approved", "approved_for_further_research", "canadian_retailer_verified", "no"}:
        return f"[bold green]✓ {clean}[/]"
    if low in {"rejected", "fail", "failed", "prohibited", "illegal", "yes"}:
        return f"[bold red]✗ {clean}[/]"
    if low in {"pending_research", "pending_canadian_retailer_search", "unknown", "unclassified", "not_yet_validated"} or "pending" in low:
        return f"[bold yellow]… {clean}[/]"
    return f"[cyan]{clean}[/]"


def title(subtitle: str | None = None) -> Panel:
    text = Text()
    text.append("KNIVVES", style="bold white")
    text.append("  ╱╱  ", style="dim")
    text.append("Folding Knife Research Database", style="cyan")
    text.append("\nlocal JSON · Canadian retailer research · terminal-native", style="dim")
    if subtitle:
        text.append(f"\n{subtitle}", style="italic")
    return Panel(text, border_style="cyan", box=box.DOUBLE)


def _money(value: Any) -> str:
    try:
        if value is None:
            return "—"
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _short_status(value: str) -> str:
    text = value.replace("_", " ")
    text = text.replace("canadian retailer verified", "CA verified")
    text = text.replace("pending canadian retailer search", "pending retailer")
    text = text.replace("approved for further research", "research ok")
    return text


def _tag_text(tags: list[str]) -> str:
    if not tags:
        return "[dim]—[/]"
    return " ".join(f"[blue]#{escape(tag)}[/]" for tag in tags)


NEW_CHIP = "[bold #d7a455]★NEW[/]"


def _knife_cell(knife: KnifeView, *, show_id: bool = False) -> str:
    cell = f"[bold]{escape(knife.brand)}[/] — [dim]{escape(knife.model)}[/]"
    if knife.is_new:
        cell = f"{NEW_CHIP} {cell}"
    if knife.buy_priority:
        cell += f" [bold magenta]⬖{knife.buy_priority}[/]"
    if show_id:
        cell += f"\n[cyan]{escape(knife.id)}[/]"
    return cell


def summary_cards(db: dict[str, Any], knives: list[KnifeView]) -> Panel:
    approved = sum(1 for k in knives if k.classification == "approved")
    rejected = sum(1 for k in knives if k.classification == "rejected")
    unclassified = sum(1 for k in knives if k.classification == "unclassified")
    canadian = sum(1 for k in knives if k.has_canadian_retailer)
    pending = sum(1 for k in knives if k.is_pending)
    fresh = sum(1 for k in knives if k.is_new)
    prices = [k.price for k in knives if k.price is not None]
    avg = sum(prices) / len(prices) if prices else None

    table = Table.grid(expand=True, padding=(0, 2))
    for _ in range(7):
        table.add_column(justify="center")
    table.add_row(
        "[bold cyan]TOTAL[/]",
        "[bold #d7a455]NEW[/]",
        "[bold green]APPROVED[/]",
        "[bold red]REJECTED[/]",
        "[bold yellow]OPEN[/]",
        "[bold magenta]CA RETAIL[/]",
        "[bold blue]AVG CAD[/]",
    )
    table.add_row(
        f"[bold white]{len(knives)}[/]",
        f"[bold #d7a455]{fresh}[/]" if fresh else "0",
        str(approved),
        str(rejected),
        f"{unclassified} · {pending} pending",
        str(canadian),
        _money(avg),
    )
    db_name = escape(str(db.get("database_name") or "knivves"))
    version = escape(str(db.get("version") or "unknown"))
    return Panel(table, title=f"{db_name} · v{version}", border_style="green", box=box.ROUNDED)

def _active_filters(filters: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in filters.items():
        if value is None or value == "" or value == [] or value == {}:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        parts.append(f"[bold]{escape(str(key))}[/]=[cyan]{escape(str(value))}[/]")
    return "  ".join(parts) if parts else "[dim]no filters[/]"


def interactive_header(db: dict[str, Any], knives: list[KnifeView], filters: dict[str, Any], result_count: int) -> str:
    approved = sum(1 for k in knives if k.classification == "approved")
    rejected = sum(1 for k in knives if k.classification == "rejected")
    unclassified = sum(1 for k in knives if k.classification == "unclassified")
    canadian = sum(1 for k in knives if k.has_canadian_retailer)
    prices = [k.price for k in knives if k.price is not None]
    avg = sum(prices) / len(prices) if prices else None
    sep = " [dim]·[/] "
    stats = sep.join(
        [
            f"[bold white]KNIVVES[/] [dim]v{escape(str(db.get('version') or '?'))}[/]",
            f"{len(knives)} knives",
            f"[green]{approved} approved[/]",
            f"[red]{rejected} rejected[/]",
            f"[yellow]{unclassified} open[/]",
            f"[magenta]{canadian} CA retail[/]",
            f"[blue]avg {_money(avg)}[/]",
        ]
    )
    return f"{stats}\n[dim]{result_count}/{len(knives)} shown[/]  {_active_filters(filters)}"


def filter_bar(filters: dict[str, Any], result_count: int, total_count: int) -> Panel:
    active = _active_filters(filters)
    return Panel(f"{active}  [dim]· {result_count}/{total_count} shown[/]", title="Active View", border_style="blue", box=box.ROUNDED)


def knives_table(
    knives: Iterable[KnifeView],
    *,
    compact: bool = False,
    show_id: bool = False,
    start_index: int = 0,
    empty_message: str = "No knives match the current filters.",
    view: str = "default",
    limit: int | None = None,
    numbered: bool = False,
) -> Table | Panel:
    items = list(knives)
    if limit is not None:
        items = items[:limit]
    if not items:
        return Panel(f"[yellow]{escape(empty_message)}[/]", border_style="yellow", box=box.ROUNDED)

    narrow = console.width < 100
    table = Table(box=box.ROUNDED, expand=True, show_lines=False, pad_edge=True)
    table.add_column("#", justify="right", style="dim", width=3, no_wrap=True)
    if compact:
        table.add_column("ID", style="bold cyan", ratio=5, overflow="fold")
        table.add_column("Class", justify="center", width=12, no_wrap=True)
        table.add_column("CAD", justify="right", width=11, no_wrap=True)
        table.add_column("CA", justify="center", width=4, no_wrap=True)
        for idx, knife in enumerate(items, start=start_index + 1):
            id_cell = f"{NEW_CHIP} {escape(knife.id)}" if knife.is_new else escape(knife.id)
            table.add_row(str(idx), id_cell, badge(knife.classification), knife.price_label, "[green]✓[/]" if knife.retailer_count else "[dim]—[/]")
        return table

    table.add_column("Knife", style="bold white", ratio=7, no_wrap=True, overflow="ellipsis")
    table.add_column("Class", justify="center", width=12, no_wrap=True)
    table.add_column("Tags", width=14, no_wrap=True, overflow="ellipsis")
    if not narrow:
        table.add_column("Status", ratio=2, overflow="fold")
        table.add_column("Steel", width=12, no_wrap=True, overflow="ellipsis")
    table.add_column("CAD", justify="right", width=11, no_wrap=True)
    table.add_column("CA", justify="center", width=4, no_wrap=True)

    for idx, knife in enumerate(items, start=start_index + 1):
        row = [str(idx), _knife_cell(knife, show_id=show_id), badge(knife.classification), _tag_text(knife.tags)]
        if not narrow:
            row.extend([badge(_short_status(knife.research_status)), escape(knife.blade_steel)])
        row.extend([knife.price_label, "[green]✓[/]" if knife.retailer_count else "[dim]—[/]"])
        table.add_row(*row)
    return table


def detail_panel(knife: KnifeView, *, include_json: bool = False) -> Panel | Group:
    retailer_lines: list[str] = []
    for idx, retailer in enumerate(knife.retailers, start=1):
        price = _money(retailer.get("listed_price_cad"))
        retailer_lines.append(
            f"[bold cyan]{idx}. {escape(str(retailer.get('retailer') or 'Unknown retailer'))}[/]\n"
            f"   {price} CAD · {escape(str(retailer.get('availability') or 'unknown'))}\n"
            f"   [dim]{escape(str(retailer.get('url') or ''))}[/]"
        )
    retailer_block = "\n".join(retailer_lines) if retailer_lines else "[yellow]No Canadian retailer saved yet.[/]"
    source = f"\n[bold]Source Input:[/] [dim]{escape(knife.source_input)}[/]" if knife.source_input else ""
    body = f"""
[bold]ID:[/] [cyan]{escape(knife.id)}[/]
[bold]Brand:[/] {escape(knife.brand)}
[bold]Model:[/] {escape(knife.model)}
[bold]User Classification:[/] {badge(knife.classification)}
[bold]Tags:[/] {' '.join(f'[blue]#{escape(tag)}[/]' for tag in knife.tags) if knife.tags else '—'}
[bold]Research Status:[/] {badge(knife.research_status)}
[bold]Acquisition Status:[/] {badge(knife.acquisition_status)}{source}

[bold cyan]Mechanism[/]
Opening: {escape(knife.opening_method)}
Lock: {escape(knife.lock_type)}
Assist: {escape(knife.assist_type)}
Blade Length: {escape(knife.blade_length)}
Steel: {escape(knife.blade_steel)}
Clear Prohibited Mechanism Found: {badge(knife.prohibited_flag)}

[bold cyan]Canadian Online Retailers[/]
{retailer_block}

[bold cyan]Notes[/]
{escape(knife.notes) if knife.notes else '—'}
""".strip()
    base = Panel(body, title=f"{escape(knife.brand)} — {escape(knife.model)}", border_style="magenta", box=box.ROUNDED)
    if not include_json:
        return base
    return Group(base, Panel(json_syntax(knife.raw), title="Raw JSON", border_style="white", box=box.ROUNDED))


def json_syntax(data: Any) -> Syntax:
    return Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json", theme="ansi_dark", word_wrap=True)


def raw_json_panel(data: Any, title_text: str = "JSON") -> Panel:
    return Panel(json_syntax(data), title=title_text, border_style="white", box=box.ROUNDED)


def stats_tables(knives: list[KnifeView]) -> Group:
    class_counts = Counter(k.classification for k in knives)
    research_counts = Counter(k.research_status for k in knives)
    tag_counts = Counter(tag for k in knives for tag in k.tags)
    steel_counts = Counter(k.blade_steel for k in knives if k.blade_steel != "Unknown")
    lock_counts = Counter(k.lock_type for k in knives if k.lock_type != "Unknown")
    retailer_counts = Counter(name for k in knives for name in k.retailer_names)

    def counter_panel(name: str, counter: Counter[str], color: str) -> Panel:
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Value")
        table.add_column("Count", justify="right")
        for value, count in counter.most_common(10):
            table.add_row(escape(value), str(count))
        if not counter:
            table.add_row("—", "0")
        return Panel(table, title=name, border_style=color, box=box.ROUNDED)

    return Group(
        counter_panel("Classification", class_counts, "green"),
        counter_panel("Research Status", research_counts, "yellow"),
        counter_panel("Tags", tag_counts, "blue"),
        counter_panel("Blade Steels", steel_counts, "cyan"),
        counter_panel("Lock Types", lock_counts, "magenta"),
        counter_panel("Canadian Retailers", retailer_counts, "magenta"),
    )


def aggregate_table(knives: Iterable[KnifeView], field: str) -> Table:
    items = list(knives)
    table = Table(box=box.ROUNDED, expand=True)
    table.add_column(field.title(), ratio=3)
    table.add_column("Count", justify="right")
    table.add_column("Approved", justify="right")
    table.add_column("Canadian Retailer", justify="right")
    if field == "tags":
        values = sorted({tag for k in items for tag in k.tags})
        get = lambda knife, value: value in knife.tags
    elif field == "retailers":
        values = sorted({name for k in items for name in k.retailer_names})
        get = lambda knife, value: value in knife.retailer_names
    elif field == "steels":
        values = sorted({k.blade_steel for k in items if k.blade_steel != "Unknown"})
        get = lambda knife, value: knife.blade_steel == value
    else:
        values = []
        get = lambda knife, value: False
    for value in values:
        members = [knife for knife in items if get(knife, value)]
        table.add_row(
            escape(str(value)),
            str(len(members)),
            str(sum(1 for knife in members if knife.classification == "approved")),
            str(sum(1 for knife in members if knife.retailer_count)),
        )
    if not values:
        table.add_row("—", "0", "0", "0")
    return table


def backups_table(paths: Iterable[Any]) -> Table | Panel:
    paths = list(paths)
    if not paths:
        return Panel("[yellow]No backups found.[/]", border_style="yellow", box=box.ROUNDED)
    table = Table(box=box.ROUNDED, expand=True)
    table.add_column("#", justify="right", width=4)
    table.add_column("Backup", ratio=3)
    table.add_column("Size", justify="right")
    table.add_column("Path", style="dim", ratio=5)
    for idx, path in enumerate(paths, start=1):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        table.add_row(str(idx), escape(path.name), f"{size:,} B", escape(str(path)))
    return table


def help_panel() -> Panel:
    body = """
[bold]/text[/] quick search      [bold]number[/] open row detail
[bold]s[/] search               [bold]f[/] filters
[bold]sort[/] sort records       [bold]n[/]/[bold]p[/] next/previous page
[bold]o[/] open retailer URL     [bold]stats[/] database stats
[bold]clear[/] reset filters     [bold]reload[/] reload JSON
[bold]path[/] show DB path       [bold]q[/] quit
""".strip()
    return Panel(body, title="Interactive Commands", border_style="blue", box=box.ROUNDED)


def buylist_panel(views: list[tuple[int, Any]], totals: list[float], *, limit: int | None = None) -> Panel:
    """The Reserve — the full BuyList priority ladder with running cost."""
    if not views:
        return Panel(
            "[yellow]The buy list is empty.[/]\n[dim]Ingest a markdown ledger with a BuyList section:  knivves add <file.md>[/]",
            title="THE RESERVE · BUY LIST",
            border_style="#d7a455",
            box=box.HEAVY,
        )
    shown = views[:limit] if limit else views
    table = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=True)
    table.add_column("Pri", justify="right", width=4, style="bold #d7a455")
    table.add_column("Knife", ratio=6, overflow="ellipsis")
    table.add_column("Sections", ratio=2, overflow="ellipsis")
    table.add_column("CAD", justify="right", width=11)
    table.add_column("Σ CAD", justify="right", width=12, style="dim")
    for (priority, knife), running in zip(shown, totals):
        name = f"[bold]{escape(knife.brand)}[/] — [dim]{escape(knife.model)}[/]"
        if knife.is_new:
            name = f"{NEW_CHIP} {name}"
        table.add_row(
            str(priority),
            name,
            _tag_text([t for t in knife.tags if t != "buy_list"]),
            knife.price_label,
            _money(running),
        )
    known = sum(1 for _, k in shown if k.price is not None)
    subtitle = f"{len(views)} priorities · running total covers {known} priced"
    if limit and len(views) > limit:
        subtitle += f" · showing top {limit}"
    return Panel(table, title="THE RESERVE · BUY LIST", subtitle=subtitle, border_style="#d7a455", box=box.HEAVY)


def buylist_strip(views: list[tuple[int, Any]], *, limit: int = 5) -> Panel:
    """Compact BuyList window for the top of the list page."""
    lines: list[str] = []
    for priority, knife in views[:limit]:
        chip = f" {NEW_CHIP}" if knife.is_new else ""
        lines.append(
            f"[bold #d7a455]{priority}.[/] [bold]{escape(knife.display_name)}[/]{chip}  [dim]{knife.price_label}[/]"
        )
    more = len(views) - limit
    if more > 0:
        lines.append(f"[dim]… {more} more — knivves buylist[/]")
    return Panel("\n".join(lines), title="BUY LIST · next acquisitions", border_style="#d7a455", box=box.ROUNDED)


def _diagnostics_lines(diagnostics: list[Any], limit: int = 12) -> list[str]:
    lines = [
        f"[{'yellow' if getattr(d, 'severity', '') == 'warning' else 'dim'}]line {getattr(d, 'line', '?'):>4}[/]  {escape(str(getattr(d, 'message', d)))}"
        for d in diagnostics[:limit]
    ]
    if len(diagnostics) > limit:
        lines.append(f"[dim]… {len(diagnostics) - limit} more[/]")
    return lines


def ingest_overview(doc: Any, plan: Any, source: str) -> Group:
    """What the ledger contains and what applying it would do."""
    sections = Table(box=box.ROUNDED, expand=True, title=f"{escape(doc.title or 'Untitled ledger')} · {escape(source)}")
    sections.add_column("SectionID", ratio=3)
    sections.add_column("Kind", width=9)
    sections.add_column("Entries", justify="right", width=8)
    sections.add_column("Tags", ratio=2)
    sections.add_column("Note", ratio=4, style="dim", overflow="ellipsis")
    kind_style = {"buylist": "bold #d7a455", "sources": "cyan", "knives": "white"}
    for section in doc.sections:
        sections.add_row(
            escape(section.name),
            f"[{kind_style.get(section.kind, 'white')}]{section.kind}[/]",
            str(len(section.entries)),
            _tag_text(section.tags),
            escape(section.notes[0]) if section.notes else "—",
        )

    plan_line = (
        f"[green]{len(plan.new_records)} to add[/] · [cyan]{len(plan.merges)} merge into existing[/] · "
        f"[#d7a455]{len(plan.buylist_keys)} buy-list priorities[/] · [magenta]{len(plan.sources)} sources[/] · "
        f"[dim]{len(plan.skipped)} duplicates skipped[/]"
    )
    blocks: list[Any] = [sections, Panel(plan_line, title="Plan", border_style="green", box=box.ROUNDED)]
    if plan.diagnostics:
        blocks.append(Panel("\n".join(_diagnostics_lines(plan.diagnostics)), title="Diagnostics", border_style="yellow", box=box.ROUNDED))
    return Group(*blocks)


def ingest_result(report: Any, backup: Any) -> Panel:
    lines = [
        f"[green]Added {report.added}[/] · merged {report.merged} · buy list {report.buylist} deep · "
        f"{report.sources} sources · {report.duplicates} duplicates skipped",
    ]
    if report.repairs:
        lines.append("")
        lines.append("[bold]Repairs applied[/]")
        for line_no, note in report.repairs[:12]:
            lines.append(f"[dim]line {line_no:>4}[/]  {escape(note)}")
        if len(report.repairs) > 12:
            lines.append(f"[dim]… {len(report.repairs) - 12} more[/]")
    if backup:
        lines.append(f"\n[dim]Backup: {escape(str(backup))}[/]")
    return Panel("\n".join(lines), title="Ingested", border_style="green", box=box.ROUNDED)


def survey_summary_panel(summary: dict[str, Any]) -> Panel:
    movers: list[tuple[str, float]] = summary.get("movers") or []
    lines = [
        f"[bold]{summary['targets']}[/] live listings read · "
        f"[#d7a455]{len(movers)} moved[/] · "
        f"[#d7a455]{len(summary.get('first_priced') or [])} priced for the first time[/] · "
        f"{summary['unchanged']} unchanged",
        f"[dim]{summary['unreachable']} unreachable · {summary['unsupported']} unsupported retailer(s) — kept on record, not surveyed[/]",
    ]
    if movers:
        lines.append("")
        for rid, delta in sorted(movers, key=lambda m: -abs(m[1]))[:10]:
            down = delta < 0
            lines.append(
                f"[{'green' if down else 'red'}]{'▼' if down else '▲'}[/] {escape(rid)}  "
                f"[{'green' if down else 'red'}]{'-' if down else '+'}${abs(delta):,.2f}[/]"
            )
        if len(movers) > 10:
            lines.append(f"[dim]… {len(movers) - 10} more movers in price_history[/]")
    return Panel("\n".join(lines), title="market survey", border_style="#d7a455", box=box.HEAVY)


def update_report_panel(entry: dict[str, Any], keep: int, new_total: int) -> Panel:
    lines = [
        f"[bold]Generation line advanced to {entry['generation']}[/] · cache keeps [bold]{keep}[/] generation(s)",
        f"[green]{entry['added']} filed since last update[/] · "
        f"[#d7a455]{new_total} currently NEW[/] · [dim]{len(entry['aged_out'])} aged out[/]",
    ]
    if entry.get("note"):
        lines.append(f"[italic]{escape(str(entry['note']))}[/]")
    if entry["aged_out"]:
        aged = ", ".join(entry["aged_out"][:8])
        if len(entry["aged_out"]) > 8:
            aged += " …"
        lines.append(f"[dim]aged out: {escape(aged)}[/]")
    return Panel("\n".join(lines), title="knivves update", border_style="#d7a455", box=box.HEAVY)


def new_status_panel(meta_block: dict[str, Any], new_total: int) -> Panel:
    history = meta_block.get("history") or []
    last = history[-1] if history else None
    lines = [
        f"[bold]Open generation:[/] {meta_block.get('generation')}",
        f"[bold]Cache depth:[/] {meta_block.get('keep_generations')} generation(s) [dim](three-generation cache; set with -oneg/-twog/-threeg)[/]",
        f"[bold]Currently NEW:[/] [#d7a455]{new_total}[/]",
    ]
    if last:
        lines.append(f"[dim]last update: gen {last.get('generation')} on {last.get('date')} — {last.get('added')} filed[/]")
    else:
        lines.append("[dim]no updates recorded yet — run knivves update to move the line[/]")
    return Panel("\n".join(lines), title="NEW cache", border_style="#d7a455", box=box.ROUNDED)


def validation_table(issues: list[Any]) -> Table:
    table = Table(box=box.ROUNDED, expand=True)
    table.add_column("Level", no_wrap=True)
    table.add_column("Knife ID", ratio=2)
    table.add_column("Issue", ratio=4)
    table.add_column("Fix", ratio=4)
    if not issues:
        table.add_row("[bold green]✓ ok[/]", "—", "No validation issues found.", "—")
        return table
    for issue in issues:
        severity = getattr(issue, "severity", "warning")
        ident = getattr(issue, "id", "database")
        message = getattr(issue, "message", str(issue))
        fix = getattr(issue, "fix", "")
        style = "red" if severity == "error" else "yellow"
        table.add_row(f"[bold {style}]{escape(str(severity))}[/]", escape(str(ident)), escape(str(message)), escape(str(fix)))
    return table
