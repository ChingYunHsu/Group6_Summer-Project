from clearpath_db.validation import gen_vid, source_hash


def test_source_hash_and_venue_id_are_stable():
    first_hash = source_hash("Central Park", "40.7", "-74.0")
    second_hash = source_hash("Central Park", "40.7", "-74.0")

    assert first_hash == second_hash
    assert len(first_hash) == 36
    assert gen_vid("nyc_restrooms", first_hash) == gen_vid("nyc_restrooms", first_hash)
    assert gen_vid("nyc_restrooms", first_hash) != gen_vid("parks_toilets", first_hash)
