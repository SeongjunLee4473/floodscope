"""Real end-to-end test against the public Earth Search STAC API and Sentinel-1 GRD.

Not run by default CI (see .github/workflows/ci.yml, which passes -m "not integration") --
it depends on network access and third-party service availability, and downloads a
sizable window from two ~1 GB scenes. Run it explicitly with:

    pytest -m integration
"""

import pytest

from floodscope import (
    despeckle,
    detect_flood,
    filter_same_orbit,
    find_nearest_item,
    read_geocoded_band,
    search_items,
    to_db,
)

# Miho River / Cheongju, South Korea -- the July 2023 Osong underpass flood.
AOI_BBOX = (127.35, 36.55, 127.60, 36.80)
PRE_DATE = "2023-06-24"
POST_DATE = "2023-07-18"


@pytest.mark.integration
def test_real_flood_detection_over_cheongju_2023():
    pre_candidates = search_items(bbox=AOI_BBOX, datetime="2023-06-15T00:00:00Z/2023-07-01T23:59:59Z")
    pre_item = find_nearest_item(pre_candidates, PRE_DATE)

    post_candidates = search_items(bbox=AOI_BBOX, datetime="2023-07-10T00:00:00Z/2023-07-25T23:59:59Z")
    post_candidates = filter_same_orbit(post_candidates, pre_item)
    assert post_candidates, "expected a same-relative-orbit post-event scene"
    post_item = find_nearest_item(post_candidates, POST_DATE)

    pre_dn, transform, crs = read_geocoded_band(pre_item.assets["vv"].href, AOI_BBOX)
    post_dn, _, _ = read_geocoded_band(post_item.assets["vv"].href, AOI_BBOX)

    pre_db = despeckle(to_db(pre_dn))
    post_db = despeckle(to_db(post_dn))
    result = detect_flood(pre_db, post_db, transform, crs)

    assert result.mask.any(), "expected some flood extent to be detected for a known flood event"
    assert 0.1 < result.area_km2 < 50, f"implausible flood area: {result.area_km2} km^2"
