from unittest.mock import MagicMock, patch

import pytest

from floodscope.search import filter_same_orbit, find_nearest_item, search_items


class FakeItem:
    def __init__(self, item_id, datetime_str, relative_orbit=54, orbit_state="ascending"):
        self.id = item_id
        self.properties = {
            "datetime": datetime_str,
            "sat:relative_orbit": relative_orbit,
            "sat:orbit_state": orbit_state,
        }


def test_search_items_builds_expected_query():
    fake_item = object()
    fake_search = MagicMock()
    fake_search.items.return_value = [fake_item]
    fake_client = MagicMock()
    fake_client.search.return_value = fake_search

    with patch("floodscope.search.Client.open", return_value=fake_client) as mock_open:
        items = search_items(
            bbox=(1, 2, 3, 4),
            datetime="2023-06-01/2023-08-01",
            collection="sentinel-1-grd",
            catalog_url="https://example.com/stac",
        )

    mock_open.assert_called_once_with("https://example.com/stac")
    fake_client.search.assert_called_once_with(
        collections=["sentinel-1-grd"], bbox=[1, 2, 3, 4], datetime="2023-06-01/2023-08-01", limit=100
    )
    assert items == [fake_item]


def test_find_nearest_item_picks_closest_date():
    items = [
        FakeItem("far", "2023-06-01T00:00:00Z"),
        FakeItem("close", "2023-07-17T00:00:00Z"),
        FakeItem("exact", "2023-07-18T00:00:00Z"),
    ]
    result = find_nearest_item(items, "2023-07-18")
    assert result.id == "exact"


def test_find_nearest_item_empty_raises():
    with pytest.raises(ValueError):
        find_nearest_item([], "2023-07-18")


def test_filter_same_orbit_keeps_matching_orbit_and_direction():
    reference = FakeItem("ref", "2023-06-24T00:00:00Z", relative_orbit=54, orbit_state="ascending")
    items = [
        FakeItem("same", "2023-07-18T00:00:00Z", relative_orbit=54, orbit_state="ascending"),
        FakeItem("diff_orbit", "2023-07-18T00:00:00Z", relative_orbit=127, orbit_state="ascending"),
        FakeItem("diff_direction", "2023-07-18T00:00:00Z", relative_orbit=54, orbit_state="descending"),
    ]
    kept = filter_same_orbit(items, reference)
    assert [item.id for item in kept] == ["same"]
