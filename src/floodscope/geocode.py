"""GCP-based geocoding of raw Sentinel-1 GRD bands into a windowed, gridded array.

Raw Sentinel-1 GRD "measurement" GeoTIFFs (as distributed on AWS Open Data / Earth
Search) carry no affine geotransform -- only a sparse set of Ground Control Points
(GCPs) in range/azimuth (pixel/line) space. ``rasterio``'s ``WarpedVRT`` can warp
through those GCPs into a real CRS on the fly, which is what this module wraps.
"""

from __future__ import annotations

import re

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds

_S3_URI_RE = re.compile(r"^s3://([^/]+)/(.+)$")


def _to_public_https(href: str) -> str:
    """Rewrite an ``s3://bucket/key`` STAC asset href to a plain public HTTPS URL.

    Earth Search lists some assets (e.g. Sentinel-1 GRD) with ``s3://`` hrefs. GDAL's
    ``/vsis3/`` driver treats those as requiring AWS credentials by default, even for
    buckets that allow anonymous reads over plain HTTPS -- so this avoids needing any
    AWS SDK configuration (credentials, ``AWS_NO_SIGN_REQUEST``, etc.) at all.
    """
    match = _S3_URI_RE.match(href)
    if not match:
        return href
    bucket, key = match.groups()
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def read_geocoded_band(
    href: str,
    bbox: tuple[float, float, float, float],
    crs: str | CRS = "EPSG:4326",
    resampling: Resampling = Resampling.bilinear,
) -> tuple[np.ndarray, rasterio.Affine, CRS]:
    """Read one Sentinel-1 GRD band asset, GCP-warped into ``crs``, windowed to ``bbox``.

    Returns ``(data, transform, crs)`` where ``data`` is a 2D array (uint16 digital
    numbers, 0 = no data) and ``transform``/``crs`` describe its real-world grid.
    """
    href = _to_public_https(href)
    with rasterio.open(href) as src:
        with WarpedVRT(src, crs=crs, resampling=resampling) as vrt:
            window = from_bounds(*bbox, transform=vrt.transform).round_lengths().round_offsets()
            data = vrt.read(1, window=window)
            transform = vrt.window_transform(window)
    return data, transform, CRS.from_user_input(crs)
