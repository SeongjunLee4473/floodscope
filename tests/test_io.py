import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from floodscope.change import FloodResult
from floodscope.io import export_cog


def test_export_cog_round_trip(tmp_path):
    mask = np.array([[0, 1], [1, 0]], dtype=bool)
    diff_db = np.array([[0.5, -4.0], [-5.0, 0.2]], dtype="float32")
    result = FloodResult(
        mask=mask,
        diff_db=diff_db,
        area_km2=1.23,
        transform=from_origin(127.0, 36.8, 0.001, 0.001),
        crs=CRS.from_epsg(4326),
    )

    out_path = tmp_path / "flood.tif"
    export_cog(result, str(out_path))

    with rasterio.open(out_path) as src:
        assert src.count == 2
        assert src.descriptions == ("flood_mask", "diff_db")
        np.testing.assert_allclose(src.read(1), mask.astype("float32"))
        np.testing.assert_allclose(src.read(2), diff_db)
