from floodscope.geocode import _to_public_https


def test_s3_uri_rewritten_to_public_https():
    href = "s3://sentinel-s1-l1c/GRD/2023/7/18/IW/DV/S1A_.../measurement/iw-vv.tiff"
    assert _to_public_https(href) == (
        "https://sentinel-s1-l1c.s3.amazonaws.com/GRD/2023/7/18/IW/DV/S1A_.../measurement/iw-vv.tiff"
    )


def test_https_href_passed_through_unchanged():
    href = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/some/key.tif"
    assert _to_public_https(href) == href
