import numpy as np

from floodscope.processing import despeckle, to_db


def test_to_db_basic_conversion():
    dn = np.array([1, 10, 100])
    db = to_db(dn)
    np.testing.assert_allclose(db, [0.0, 20.0, 40.0])


def test_to_db_zero_is_nan():
    dn = np.array([0, 100])
    db = to_db(dn)
    assert np.isnan(db[0])
    assert db[1] == 40.0


def test_to_db_preserves_shape():
    dn = np.random.randint(1, 5000, size=(10, 12))
    db = to_db(dn)
    assert db.shape == dn.shape


def test_despeckle_smooths_salt_and_pepper_noise():
    base = np.full((20, 20), 10.0)
    noisy = base.copy()
    noisy[5, 5] = 200.0  # single-pixel speckle spike
    filtered = despeckle(noisy, size=5)
    assert filtered[5, 5] < 50.0  # spike should be smoothed away
    np.testing.assert_allclose(filtered[0, 0], 10.0)


def test_despeckle_preserves_nan_footprint():
    data = np.full((10, 10), 5.0)
    data[0:3, 0:3] = np.nan
    filtered = despeckle(data)
    assert np.isnan(filtered[0:3, 0:3]).all()
    assert not np.isnan(filtered[5, 5])
