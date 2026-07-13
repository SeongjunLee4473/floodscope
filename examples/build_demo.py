"""Build the demo images used in README.md.

Entirely self-contained: searches a public STAC catalog, reads real Sentinel-1 GRD
scenes directly over HTTPS, GCP-geocodes them, and runs full flood-extent change
detection against a real, documented event. No credentials and no manual downloads
required.

Usage (with the [demo] extra installed):
    pip install -e ".[demo]"
    python examples/build_demo.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from floodscope import (
    despeckle,
    detect_flood,
    filter_same_orbit,
    find_nearest_item,
    read_geocoded_band,
    search_items,
    to_db,
)

# Miho River / Cheongju, South Korea -- the July 2023 Osong underpass flood
# (a temporary embankment near the Miho River breached on 2023-07-15, flooding the
# Gungpyeong 2 underpass).
AOI_BBOX = (127.35, 36.55, 127.60, 36.80)
PRE_DATE = "2023-06-24"
POST_DATE = "2023-07-18"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Searching Earth Search for a pre-event Sentinel-1 scene...")
    pre_candidates = search_items(bbox=AOI_BBOX, datetime="2023-06-15T00:00:00Z/2023-07-01T23:59:59Z")
    pre_item = find_nearest_item(pre_candidates, PRE_DATE)
    print(f"  pre:  {pre_item.id}  ({pre_item.properties['datetime'][:10]})")

    print("Searching for a same-relative-orbit post-event scene...")
    post_candidates = search_items(bbox=AOI_BBOX, datetime="2023-07-10T00:00:00Z/2023-07-25T23:59:59Z")
    post_candidates = filter_same_orbit(post_candidates, pre_item)
    post_item = find_nearest_item(post_candidates, POST_DATE)
    print(f"  post: {post_item.id}  ({post_item.properties['datetime'][:10]})")

    print("GCP-geocoding both scenes over the AOI (reads real COGs over HTTPS)...")
    pre_dn, transform, crs = read_geocoded_band(pre_item.assets["vv"].href, AOI_BBOX)
    post_dn, _, _ = read_geocoded_band(post_item.assets["vv"].href, AOI_BBOX)

    print("Converting to dB and despeckling...")
    pre_db = despeckle(to_db(pre_dn))
    post_db = despeckle(to_db(post_dn))

    print("Detecting flood extent...")
    result = detect_flood(pre_db, post_db, transform, crs)
    print(f"  estimated new-water area: {result.area_km2:.2f} km^2")

    display_vmin, display_vmax = np.nanpercentile(post_db, [1, 99])

    # --- Figure 1: pre vs post grayscale VV backscatter ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    axes[0].imshow(pre_db, cmap="gray", vmin=display_vmin, vmax=display_vmax)
    axes[0].set_title(f"Pre-flood ({pre_item.properties['datetime'][:10]})", fontsize=12)
    axes[0].axis("off")
    axes[1].imshow(post_db, cmap="gray", vmin=display_vmin, vmax=display_vmax)
    axes[1].set_title(f"Post-flood ({post_item.properties['datetime'][:10]})", fontsize=12)
    axes[1].axis("off")
    fig.suptitle("Sentinel-1 VV backscatter, before and after the flood", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "pre_post_backscatter.png", dpi=120)
    plt.close(fig)
    print("Wrote docs/images/pre_post_backscatter.png")

    # --- Figure 2: detected flood extent overlaid on the post-flood image ---
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(post_db, cmap="gray", vmin=display_vmin, vmax=display_vmax)
    overlay = np.zeros((*result.mask.shape, 4))
    overlay[result.mask] = [1, 0, 0, 0.65]
    ax.imshow(overlay)
    ax.set_title(f"Detected new-water extent: {result.area_km2:.2f} km^2", fontsize=13, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "flood_extent.png", dpi=120)
    plt.close(fig)
    print("Wrote docs/images/flood_extent.png")

    print(f"\nDone. {len(post_candidates)} same-orbit post-event candidate(s) considered.")


if __name__ == "__main__":
    main()
