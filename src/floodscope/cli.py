"""Command-line interface for floodscope."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from floodscope.change import detect_flood
from floodscope.geocode import read_geocoded_band
from floodscope.io import export_cog
from floodscope.processing import despeckle, to_db
from floodscope.search import (
    filter_same_orbit,
    find_nearest_item,
    search_items,
)

app = typer.Typer(help="Flood-extent change detection from public Sentinel-1 SAR imagery.")
console = Console()


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = [float(p) for p in value.split(",")]
    if len(parts) != 4:
        raise typer.BadParameter("bbox must be 'west,south,east,north'")
    return (parts[0], parts[1], parts[2], parts[3])


@app.command()
def search(
    bbox: str = typer.Option(..., help="west,south,east,north (WGS84 degrees)"),
    start: str = typer.Option(..., help="Start date, e.g. 2023-06-01"),
    end: str = typer.Option(..., help="End date, e.g. 2023-08-01"),
) -> None:
    """List Sentinel-1 GRD scenes matching an AOI and date range."""
    items = search_items(bbox=_parse_bbox(bbox), datetime=f"{start}T00:00:00Z/{end}T23:59:59Z")
    table = Table(title=f"{len(items)} scene(s) found")
    table.add_column("Item ID")
    table.add_column("Date")
    table.add_column("Orbit")
    table.add_column("Direction")
    for item in items:
        table.add_row(
            item.id,
            str(item.properties.get("datetime", "?"))[:10],
            str(item.properties.get("sat:relative_orbit")),
            str(item.properties.get("sat:orbit_state")),
        )
    console.print(table)


@app.command()
def detect(
    bbox: str = typer.Option(..., help="west,south,east,north (WGS84 degrees)"),
    pre_date: str = typer.Option(..., help="Pre-event reference date, e.g. 2023-06-24"),
    post_date: str = typer.Option(..., help="Post-event date, e.g. 2023-07-18"),
    output: Path = typer.Option(..., help="Output COG path"),
    threshold: float = typer.Option(-3.0, help="Darkening threshold in dB to flag as new water"),
    min_pixels: int = typer.Option(8, help="Minimum connected-component size (drops speckle)"),
    search_window_days: int = typer.Option(6, help="+/- days around each date to search"),
) -> None:
    """Search, geocode, and difference a same-orbit Sentinel-1 pair to map new flood extent."""
    parsed_bbox = _parse_bbox(bbox)

    def _window(date: str) -> str:
        import datetime as dt

        center = dt.datetime.fromisoformat(date)
        delta = dt.timedelta(days=search_window_days)
        return f"{(center - delta).date()}T00:00:00Z/{(center + delta).date()}T23:59:59Z"

    with console.status("Searching for pre-event scene..."):
        pre_candidates = search_items(bbox=parsed_bbox, datetime=_window(pre_date))
    if not pre_candidates:
        console.print("[red]No pre-event scenes found in that window.[/red]")
        raise typer.Exit(code=1)
    pre_item = find_nearest_item(pre_candidates, pre_date)

    with console.status("Searching for post-event scene..."):
        post_candidates = search_items(bbox=parsed_bbox, datetime=_window(post_date))
    post_candidates = filter_same_orbit(post_candidates, pre_item)
    if not post_candidates:
        console.print(
            "[red]No post-event scene found on the same relative orbit as the pre-event scene. "
            "Try a wider --search-window-days.[/red]"
        )
        raise typer.Exit(code=1)
    post_item = find_nearest_item(post_candidates, post_date)

    console.print(f"Pre:  {pre_item.id} ({pre_item.properties['datetime'][:10]})")
    console.print(f"Post: {post_item.id} ({post_item.properties['datetime'][:10]})")

    with console.status("Geocoding and processing..."):
        pre_dn, transform, crs = read_geocoded_band(pre_item.assets["vv"].href, parsed_bbox)
        post_dn, _, _ = read_geocoded_band(post_item.assets["vv"].href, parsed_bbox)
        pre_db = despeckle(to_db(pre_dn))
        post_db = despeckle(to_db(post_dn))
        result = detect_flood(pre_db, post_db, transform, crs, threshold=threshold, min_pixels=min_pixels)

    export_cog(result, str(output))
    console.print(f"[green]Wrote {output}[/green] -- estimated new-water area: {result.area_km2:.2f} km^2")


if __name__ == "__main__":
    app()
