from unittest.mock import MagicMock

from clearpath_db import venue_language
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

    assert result == {"imported": 2, "skipped": 0, "errors": 0, "accessibility_processed": 0}
    assert calls[0][0][0][1][1] == "pharmacy"
    assert calls[1][0][0][1][1] == "dentist"


def test_healthcare_etl_links_osm_wheelchair_tags_by_stable_osm_id():
    calls = []
    original = healthcare.etl_execute
    healthcare.etl_execute = lambda _conn, statements, **kwargs: calls.append(
        (statements, kwargs)
    ) or True
    try:
        result = healthcare.etl_healthcare(
            object(), [], [],
            [{"properties": {"@id": "node/1", "name": "Dental Care", "amenity": "dentist", "wheelchair": "limited", "toilets:wheelchair": "yes"}}],
        )
    finally:
        healthcare.etl_execute = original

    assert result == {"imported": 0, "skipped": 0, "errors": 0, "accessibility_processed": 1}
    statements, metadata = calls[0]
    assert metadata["source"] == "osm_accessibility"
    assert len(statements) == 3
    assert statements[0][1] == (False, True, "node/1")
    assert statements[2][1] == ("partial", "partial", True, "node/1")


def test_hospital_sponsored_school_health_is_not_classified_as_hospital():
    row = {
        "Facility Type": "HOSP-SB",
        "Short Description": "Hospital-sponsored school health programme",
        "Facility Name": "School Health Centre",
    }
    assert healthcare.classify_nys_venue_type(row) == "healthcare"
    assert healthcare.classify_nys_venue_type({"Short Description": "Acute care hospital"}) == "hospital"


def test_lass_language_ingestion_also_updates_venue_filter_fields():
    calls = []
    original_execute = venue_language.etl_execute
    original_find = venue_language.find_nearest_venue
    venue_language.etl_execute = lambda _conn, statements, **_kwargs: calls.append(statements) or True
    venue_language.find_nearest_venue = lambda *_args: "venue_language_1"
    try:
        result = venue_language.etl_venue_language(
            MagicMock(),
            [{
                "Borough": "Manhattan", "Latitude": "40.75", "Longitude": "-73.98",
                "Facility Name": "Language Centre",
                "Languages in which the facility has translated signs relating to service being provided": "Spanish, Chinese",
                "Languages in which the facility has translated documents": "",
            }],
        )
    finally:
        venue_language.etl_execute = original_execute
        venue_language.find_nearest_venue = original_find

    assert result == {"imported": 1, "skipped": 0, "errors": 0}
    assert len(calls[0]) == 2
    assert calls[0][1][1] == ('["ES", "ZH"]', "ES", "ZH", "venue_language_1")
