"""Thin wrapper around pystac-client for searching public STAC catalogs for SAR scenes."""

from __future__ import annotations

from typing import Sequence

import pystac
from pystac_client import Client

DEFAULT_CATALOG_URL = "https://earth-search.aws.element84.com/v1"
DEFAULT_COLLECTION = "sentinel-1-grd"


def search_items(
    bbox: Sequence[float],
    datetime: str,
    collection: str = DEFAULT_COLLECTION,
    catalog_url: str = DEFAULT_CATALOG_URL,
    limit: int = 100,
) -> list[pystac.Item]:
    """Search a public STAC catalog and return matching items.

    Parameters
    ----------
    bbox:
        ``(west, south, east, north)`` in WGS84 degrees.
    datetime:
        RFC3339 instant or ``start/end`` range, e.g. ``"2023-06-01/2023-08-01"``.
    collection:
        STAC collection id (default: Sentinel-1 GRD on Earth Search).
    catalog_url:
        STAC API root. Defaults to AWS Earth Search, which requires no authentication.
    """
    client = Client.open(catalog_url)
    search = client.search(collections=[collection], bbox=list(bbox), datetime=datetime, limit=limit)
    return list(search.items())


def find_nearest_item(items: list[pystac.Item], target_date: str) -> pystac.Item:
    """Return the item whose acquisition datetime is closest to ``target_date`` (YYYY-MM-DD)."""
    import datetime as dt

    target = dt.datetime.fromisoformat(target_date).replace(tzinfo=dt.timezone.utc)

    def _distance(item: pystac.Item) -> float:
        acquired = dt.datetime.fromisoformat(item.properties["datetime"].replace("Z", "+00:00"))
        return abs((acquired - target).total_seconds())

    if not items:
        raise ValueError("No items to search")
    return min(items, key=_distance)


def filter_same_orbit(items: list[pystac.Item], reference: pystac.Item) -> list[pystac.Item]:
    """Keep only items sharing ``reference``'s relative orbit (and orbit direction).

    Sentinel-1's viewing geometry (incidence angle) depends on the relative orbit, so
    comparing two acquisitions from *different* relative orbits mixes genuine change with
    geometry-driven brightness differences. Two acquisitions from the *same* relative
    orbit (which repeats every 12 days for Sentinel-1) share the same geometry, making a
    direct pixel-to-pixel comparison meaningful.
    """
    ref_orbit = reference.properties.get("sat:relative_orbit")
    ref_direction = reference.properties.get("sat:orbit_state")
    return [
        item
        for item in items
        if item.properties.get("sat:relative_orbit") == ref_orbit
        and item.properties.get("sat:orbit_state") == ref_direction
    ]
