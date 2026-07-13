"""Pre/post change detection: isolate newly-flooded pixels and estimate their area."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.crs import CRS
from scipy.ndimage import label

KM_PER_DEGREE_LAT = 111.32


@dataclass
class FloodResult:
    """A detected flood extent: the boolean mask, the underlying diff, and its area."""

    mask: np.ndarray
    diff_db: np.ndarray
    area_km2: float
    transform: rasterio.Affine
    crs: CRS


def _pixel_area_km2(transform: rasterio.Affine, shape: tuple[int, int]) -> float:
    """Approximate area of one pixel in km^2, for a geographic (degrees) transform.

    Uses the raster's center latitude for the longitude-degrees-to-km conversion; for
    an AOI a few tens of km across this introduces well under 1% error, which is fine
    for a summary area statistic (not a cadastral-grade measurement).
    """
    height, width = shape
    _, center_lat = transform * (width / 2, height / 2)
    km_per_degree_lon = KM_PER_DEGREE_LAT * np.cos(np.radians(center_lat))
    pixel_height_km = abs(transform.e) * KM_PER_DEGREE_LAT
    pixel_width_km = abs(transform.a) * km_per_degree_lon
    return pixel_height_km * pixel_width_km


def detect_flood(
    pre_db: np.ndarray,
    post_db: np.ndarray,
    transform: rasterio.Affine,
    crs: CRS,
    threshold: float = -3.0,
    min_pixels: int = 8,
) -> FloodResult:
    """Flag pixels that got darker than ``threshold`` (dB) between ``pre_db`` and ``post_db``.

    A pixel darkening sharply between two same-relative-orbit SAR acquisitions is the
    standard signature of new open-water inundation (calm water is a near-specular
    reflector, so it returns very little energy to the sensor). ``min_pixels`` drops
    connected clusters smaller than that -- isolated single-pixel flags are far more
    often residual speckle than real flooding.

    Only detects *open-water* flooding (the classic dark-water signature); flooded
    vegetation or urban areas can instead brighten via double-bounce scattering, which
    this simple threshold does not attempt to capture.
    """
    diff = post_db - pre_db
    valid = ~np.isnan(diff)
    candidate = np.where(valid, diff < threshold, False)

    labeled, _ = label(candidate)
    sizes = np.bincount(labeled.ravel())
    keep = sizes >= min_pixels
    keep[0] = False  # label 0 is the background, never "kept"
    mask = keep[labeled]

    area_km2 = float(mask.sum()) * _pixel_area_km2(transform, mask.shape)
    return FloodResult(mask=mask, diff_db=diff, area_km2=area_km2, transform=transform, crs=crs)
