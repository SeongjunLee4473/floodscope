"""Digital-number-to-dB conversion and speckle filtering for Sentinel-1 GRD."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter


def to_db(digital_numbers: np.ndarray) -> np.ndarray:
    """Convert Sentinel-1 GRD digital numbers to an uncalibrated backscatter-in-dB proxy.

    This is ``20 * log10(DN)``, NOT radiometrically calibrated sigma0 -- proper
    calibration needs a per-pixel gain correction from the product's calibration
    annotation LUT (angle- and range-dependent), which is out of scope here. For
    comparing two same-relative-orbit acquisitions (see
    ``floodscope.search.filter_same_orbit``), the viewing geometry -- and so the gain
    curve -- is identical between them, so the *relative* difference this function
    feeds into change detection is still meaningful without absolute calibration.

    DN == 0 (no data, e.g. outside the imaged swath) maps to NaN rather than a
    log(0) singularity.
    """
    valid = digital_numbers > 0
    safe = np.where(valid, digital_numbers, 1)
    return np.where(valid, 20 * np.log10(safe), np.nan)


def despeckle(db: np.ndarray, size: int = 5) -> np.ndarray:
    """Reduce speckle noise with a median filter, preserving NaN (no-data) pixels.

    A median filter is a simple, standard first-pass SAR despeckling method -- cheap
    and effective at removing salt-and-pepper speckle without the complexity of a full
    Lee/Frost adaptive filter, at the cost of some edge blurring.
    """
    filled = np.nan_to_num(db, nan=np.nanmedian(db))
    filtered = median_filter(filled, size=size)
    return np.where(np.isnan(db), np.nan, filtered)
