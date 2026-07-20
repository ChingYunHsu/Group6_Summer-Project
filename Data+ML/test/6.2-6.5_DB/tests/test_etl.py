from clearpath_db.etl import healthcare, restrooms


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


def test_healthcare_etl_writes_recognised_nys_and_osm_subtypes():
    calls = []
    original = healthcare.etl_execute

    def capture(_conn, statements, *, source, record_id):
        calls.append((statements, source, record_id))
        return True

    healthcare.etl_execute = capture
    try:
        result = healthcare.etl_healthcare(
            object(),
            [{
                "Facility Name": "Downtown Pharmacy",
                "Facility County": "New York",
                "Facility Latitude": "40.75",
                "Facility Longitude": "-73.98",
                "Facility ID": "nys-pharmacy-1",
                "Short Description": "Retail pharmacy",
            }],
            [{
                "geometry": {"coordinates": [-73.98, 40.75]},
                "properties": {
                    "@id": "node/1", "name": "Dental Care", "amenity": "dentist"
                },
            }],
        )
    finally:
        healthcare.etl_execute = original

    assert result == {"imported": 2, "skipped": 0, "errors": 0}
    assert calls[0][0][0][1][1] == "pharmacy"
    assert calls[1][0][0][1][1] == "dentist"


def test_hospital_sponsored_school_health_is_not_classified_as_hospital():
    row = {
        "Facility Type": "HOSP-SB",
        "Short Description": "Hospital-sponsored school health programme",
        "Facility Name": "School Health Centre",
    }
    assert healthcare.classify_nys_venue_type(row) == "healthcare"
    assert healthcare.classify_nys_venue_type({"Short Description": "Acute care hospital"}) == "hospital"
