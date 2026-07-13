import numpy as np
from rasterio.crs import CRS
from rasterio.transform import from_origin

from floodscope.change import _pixel_area_km2, detect_flood


def _flat_transform(pixel_deg=0.001):
    # Origin near the equator so 1 degree lon ~= 1 degree lat in km (simplifies expected math).
    return from_origin(127.0, 0.001 * 10, pixel_deg, pixel_deg)


def test_detect_flood_flags_darkened_cluster():
    pre = np.full((20, 20), -10.0)
    post = pre.copy()
    post[5:9, 5:9] -= 6.0  # a 4x4 = 16-pixel cluster darkens by 6 dB

    transform = _flat_transform()
    result = detect_flood(pre, post, transform, CRS.from_epsg(4326), threshold=-3.0, min_pixels=8)

    assert result.mask[5:9, 5:9].all()
    assert result.mask.sum() == 16
    assert result.area_km2 > 0


def test_detect_flood_drops_small_clusters_as_speckle():
    pre = np.full((20, 20), -10.0)
    post = pre.copy()
    post[5, 5] -= 6.0  # a single isolated pixel

    transform = _flat_transform()
    result = detect_flood(pre, post, transform, CRS.from_epsg(4326), threshold=-3.0, min_pixels=8)

    assert not result.mask.any()
    assert result.area_km2 == 0.0


def test_detect_flood_ignores_brightening():
    pre = np.full((10, 10), -10.0)
    post = pre + 6.0  # got brighter everywhere, not darker
    transform = _flat_transform()
    result = detect_flood(pre, post, transform, CRS.from_epsg(4326))
    assert not result.mask.any()


def test_detect_flood_respects_nan_as_invalid():
    pre = np.full((10, 10), -10.0)
    post = np.full((10, 10), -10.0)
    pre[0, 0] = np.nan
    post[0, 0] = -20.0  # would be a big darkening, but pre is nodata here
    transform = _flat_transform()
    result = detect_flood(pre, post, transform, CRS.from_epsg(4326), min_pixels=1)
    assert not result.mask[0, 0]


def test_pixel_area_km2_matches_known_scale_near_equator():
    transform = from_origin(0.0, 0.0, 0.01, 0.01)  # ~1.1132 km per pixel side near equator
    area = _pixel_area_km2(transform, (100, 100))
    assert 1.2 < area < 1.25
