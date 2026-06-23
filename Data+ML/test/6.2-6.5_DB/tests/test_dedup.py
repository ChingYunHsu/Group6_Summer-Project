from clearpath_db.dedup import dedup_parks, dedup_restrooms


def test_restroom_dedup_filters_region_and_duplicate_names():
    rows = [
        {"Facility Name": "A", "Latitude": "40.75", "Longitude": "-73.98"},
        {"Facility Name": "A", "Latitude": "40.76", "Longitude": "-73.97"},
        {"Facility Name": "Outside", "Latitude": "40.60", "Longitude": "-73.98"},
    ]

    result, stats = dedup_restrooms(rows)

    assert [row["Facility Name"] for row in result] == ["A"]
    assert stats == {"input": 3, "unique": 1, "duplicates": 1, "filtered": 1}


def test_parks_dedup_keeps_only_unique_manhattan_names():
    rows = [
        {"Name": "Park A", "Borough": "Manhattan"},
        {"Name": "Park A", "Borough": "Manhattan"},
        {"Name": "Park B", "Borough": "Brooklyn"},
    ]

    result, stats = dedup_parks(rows)

    assert [row["Name"] for row in result] == ["Park A"]
    assert stats == {"input": 3, "unique": 1, "duplicates": 1, "filtered": 1}
