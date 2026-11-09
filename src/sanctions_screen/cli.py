"""Command line interface."""

from __future__ import annotations

from pathlib import Path

import typer

from . import __version__, config, match
from . import diff as diff_mod
from .batch import run_batch
from .fetch import FetchError, fetch_all
from .index import build_index, save_index
from .screen import (
    explain_hit,
    format_hits,
    get_index,
    hits_to_csv,
    hits_to_json,
    hits_to_markdown,
    load_lists,
    screen_name,
    stale_sources,
)

app = typer.Typer(
    help="Screen names against public sanctions lists, offline. A screening aid: every hit "
    "needs human review. Not legal advice.",
    no_args_is_help=True,
)


def _pct_to_unit(value: float) -> float:
    """The CLI takes thresholds as 0-100, the library wants 0-1. This is the only place that
    converts."""
    if not 0 <= value <= 100:
        raise typer.BadParameter(f"{value} is outside 0-100")
    return value / 100.0


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"sanctions-screen {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    pass


@app.command()
def fetch(
    dest: Path = typer.Option(config.DEFAULT_LISTS_DIR, "--dest", help="Where to put the lists."),
    only: list[str] = typer.Option(
        None, "--only", help="Limit to a source: ofac, un, eu, uk. Repeatable."
    ),
) -> None:
    """Download the official lists into data/lists/."""
    try:
        got = fetch_all(dest, only or None)
    except FetchError as exc:
        typer.echo(f"fetch failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    for source, path in got.items():
        typer.echo(f"{source}: {path} ({path.stat().st_size // 1024} KiB)")


@app.command()
def index(
    from_dir: Path = typer.Option(
        config.DEFAULT_LISTS_DIR, "--from", help="Directory with the lists."
    ),
    out: Path = typer.Option(config.DEFAULT_INDEX_PATH, "--out", help="Index file to write."),
) -> None:
    """Parse the lists and build the local index."""
    entities = load_lists(from_dir)
    if not entities:
        typer.echo(f"no lists found in {from_dir}", err=True)
        raise typer.Exit(1)
    idx = build_index(entities)
    save_index(idx, out)
    counts: dict[str, int] = {}
    for e in entities:
        counts[e.source] = counts.get(e.source, 0) + 1
    detail = ", ".join(f"{s} {n}" for s, n in sorted(counts.items()))
    typer.echo(f"indexed {len(entities)} entities ({detail}), {len(idx.records)} names -> {out}")


@app.command()
def screen(
    name: str = typer.Argument(..., help="Name of the person or company to check."),
    dob: str = typer.Option(None, "--dob", help="Date of birth: 1971, 1971-03-12 or 12/03/1971."),
    country: str = typer.Option(None, "--country", help="Country, ISO code or name."),
    threshold: float = typer.Option(
        config.DEFAULT_THRESHOLD * 100, "--threshold", help="Minimum score, 0-100."
    ),
    mode: str = typer.Option("balanced", "--mode", help="strict, balanced or broad."),
    index_path: Path = typer.Option(config.DEFAULT_INDEX_PATH, "--index", help="Index file."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
    fmt: str = typer.Option("text", "--format", help="text, json, csv or md."),
    limit: int = typer.Option(config.MAX_HITS, "--limit", help="Maximum number of hits."),
    source: list[str] = typer.Option(None, "--source", help="Only hits from this list."),
    explain: bool = typer.Option(False, "--explain", help="Plain-language paragraph per hit."),
) -> None:
    """Screen one name and print ranked hits with the reasons."""
    if mode not in match.MODES:
        raise typer.BadParameter(f"mode must be one of {', '.join(match.MODES)}")
    if as_json:
        fmt = "json"
    if fmt not in ("text", "json", "csv", "md"):
        raise typer.BadParameter("format must be text, json, csv or md")
    try:
        idx = get_index(index_path)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    for src, age in stale_sources(idx).items():
        typer.echo(f"warning: the {src} list is {age} days old, run `fetch` and `index`", err=True)
    hits = screen_name(
        idx, name, dob=dob, country=country, threshold=_pct_to_unit(threshold), mode=mode,
        decisions_path=config.DEFAULT_DECISIONS_PATH, limit=limit, sources=source or None,
    )
    if fmt == "json":
        typer.echo(hits_to_json(hits))
    elif fmt == "csv":
        typer.echo(hits_to_csv(hits), nl=False)
    elif fmt == "md":
        typer.echo(hits_to_markdown(hits))
    else:
        typer.echo(format_hits(hits))
        if explain:
            for h in hits:
                typer.echo("\n" + explain_hit(h))


@app.command()
def batch(
    csv_path: Path = typer.Argument(..., help="Customers CSV."),
    out: Path = typer.Option(Path("output"), "--out"),
    threshold: float = typer.Option(config.DEFAULT_THRESHOLD * 100, "--threshold"),
    index_path: Path = typer.Option(config.DEFAULT_INDEX_PATH, "--index"),
    decisions: Path = typer.Option(config.DEFAULT_DECISIONS_PATH, "--decisions"),
) -> None:
    """Screen a CSV of customers."""
    try:
        idx = get_index(index_path)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    summary = run_batch(csv_path, out, idx, _pct_to_unit(threshold), decisions)
    typer.echo(
        f"{summary['rows']} rows, {summary['rows_with_hits']} with hits "
        f"({summary['total_hits']} hits) -> {out}/report.json, {out}/report.csv"
    )


@app.command()
def diff(
    old: Path = typer.Argument(..., help="Older snapshot: a directory of lists or one list file."),
    new: Path = typer.Argument(..., help="Newer snapshot."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
) -> None:
    """Show what changed between two snapshots of the lists."""
    try:
        result = diff_mod.diff_paths(old, new)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(diff_mod.diff_to_json(result) if as_json else diff_mod.format_diff(result))


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run the HTTP API (localhost only, no auth)."""
    import uvicorn

    uvicorn.run("sanctions_screen.api:app", host=host, port=port)


if __name__ == "__main__":
    app()
