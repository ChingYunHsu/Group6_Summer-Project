from clearpath_db.validation import gps_to_district, is_manhattan, safe_dec, safe_int


def test_manhattan_boundary_and_district_classification():
    assert is_manhattan(40.700, -74.020)
    assert is_manhattan(40.880, -73.900)
    assert not is_manhattan(40.699, -74.000)
    assert gps_to_district(40.810, -73.950) == "uptown"
    assert gps_to_district(40.760, -73.970) == "midtown_east"
    assert gps_to_district(40.760, -73.980) == "midtown_west"
    assert gps_to_district(40.730, -74.000) == "downtown"


def test_safe_numeric_conversion_uses_defaults():
    assert safe_int("12") == 12
    assert safe_int("bad") is None
    assert str(safe_dec("3.25")) == "3.25"
    assert safe_dec(None) is None
