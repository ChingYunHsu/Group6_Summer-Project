from clearpath_db.etl import restrooms


def test_restroom_etl_returns_structured_stats_and_preserves_source_names():
    calls = []
    original = restrooms.etl_execute

    def capture(_conn, statements, *, source, record_id):
        calls.append((statements, source, record_id))
        return True

    restrooms.etl_execute = capture
    try:
        result = restrooms.etl_restrooms(
            object(),
            [
                {
                    "Facility Name": "Test Restroom",
                    "Latitude": "40.75",
                    "Longitude": "-73.98",
                    "Status": "Operational",
                }
            ],
            [{"Name": "Test Park", "Borough": "Manhattan"}],
        )
    finally:
        restrooms.etl_execute = original

    assert result == {"imported": 2, "skipped": 0, "errors": 0}
    assert [call[1] for call in calls] == ["nyc_restrooms", "parks_toilets"]
    assert '"nyc_restrooms"' in calls[0][0][2][0]
    assert '"parks_toilets"' in calls[1][0][2][0]
