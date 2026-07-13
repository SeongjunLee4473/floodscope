"""Export a FloodResult to a Cloud-Optimized GeoTIFF."""

from __future__ import annotations

import numpy as np
import rasterio

from floodscope.change import FloodResult


def export_cog(result: FloodResult, path: str) -> None:
    """Write ``result`` to ``path`` as a 2-band Cloud-Optimized GeoTIFF.

    Band 1: ``flood_mask`` (uint8, 1 = detected new water, 0 = not).
    Band 2: ``diff_db`` (float32, post-minus-pre backscatter difference).
    """
    height, width = result.mask.shape
    profile = {
        "driver": "COG",
        "height": height,
        "width": width,
        "count": 2,
        "dtype": "float32",
        "crs": result.crs,
        "transform": result.transform,
        "nodata": np.nan,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(result.mask.astype("float32"), 1)
        dst.set_band_description(1, "flood_mask")
        dst.write(result.diff_db.astype("float32"), 2)
        dst.set_band_description(2, "diff_db")
