"""floodscope: flood-extent change detection from public Sentinel-1 SAR imagery."""

from floodscope.change import FloodResult, detect_flood
from floodscope.geocode import read_geocoded_band
from floodscope.io import export_cog
from floodscope.processing import despeckle, to_db
from floodscope.search import filter_same_orbit, find_nearest_item, search_items

__version__ = "0.1.0"

__all__ = [
    "search_items",
    "find_nearest_item",
    "filter_same_orbit",
    "read_geocoded_band",
    "to_db",
    "despeckle",
    "detect_flood",
    "FloodResult",
    "export_cog",
]
