from ..db import etl_execute, log_etl_error
from ..validation import gen_vid, gps_to_district, is_manhattan, source_hash


def etl_restrooms(conn, restrooms_data, parks_data):
    imported = skipped = errors = 0
    for row in restrooms_data:
        name = (row.get("Facility Name") or "").strip()
        try:
            lat, lng = float(row["Latitude"]), float(row["Longitude"])
        except (ValueError, TypeError, KeyError) as error:
            log_etl_error("nyc_restrooms", name or "<missing-name>", error)
            skipped += 1
            errors += 1
            continue
        if not name or not is_manhattan(lat, lng):
            skipped += 1
            continue
        source_id = source_hash(name, str(lat), str(lng))
        venue_id = gen_vid("nyc_restrooms", source_id)
        status_raw = (row.get("Status") or "").strip().lower()
        status = (
            "operational"
            if "operational" in status_raw and "not" not in status_raw
            else "not_operational"
        )
        statements = [
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, website, source_confidence) VALUES (%s, "restroom", %s, %s, %s, %s, %s, %s, %s, 0.600) ON DUPLICATE KEY UPDATE name = VALUES(name)',
                (
                    venue_id,
                    name,
                    lat,
                    lng,
                    row.get("Location Type", ""),
                    gps_to_district(lat, lng),
                    (row.get("Location") or "").strip() or None,
                    (row.get("Website") or "").strip() or None,
                ),
            ),
            (
                "INSERT INTO restroom_profiles (venue_id, restroom_type, operator, status, handicap_accessible, changing_station, additional_notes) VALUES (%s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE status = VALUES(status)",
                (
                    venue_id,
                    (row.get("Restroom Type") or "").strip() or None,
                    (row.get("Operator") or "").strip() or None,
                    status,
                    True
                    if "accessible" in (row.get("Accessibility") or "").lower()
                    and "not" not in (row.get("Accessibility") or "").lower()
                    else None,
                    True
                    if (row.get("Changing Stations") or "").strip().lower() == "yes"
                    else None,
                    (row.get("Additional Notes") or "").strip() or None,
                ),
            ),
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, matched_method, match_confidence) VALUES (%s, "nyc_restrooms", %s, %s, "single_source", 0.600) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name),
            ),
        ]
        if etl_execute(
            conn, statements, source="nyc_restrooms", record_id=source_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1

    for row in parks_data:
        name = (row.get("Name") or "").strip()
        borough = (row.get("Borough") or "").strip()
        if not name or borough.lower() != "manhattan":
            skipped += 1
            continue
        source_id = source_hash(name, borough)
        venue_id = gen_vid("parks_toilets", source_id)
        location = (row.get("Location") or "").strip() or None
        statements = [
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, source_confidence) VALUES (%s, "restroom", %s, 0, 0, %s, NULL, %s, 0.300) ON DUPLICATE KEY UPDATE name = VALUES(name)',
                (venue_id, name, borough, location),
            ),
            (
                "INSERT INTO restroom_profiles (venue_id, restroom_type, operator, open_year_round, handicap_accessible, additional_notes) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE additional_notes = VALUES(additional_notes)",
                (
                    venue_id,
                    "park",
                    "NYC Parks",
                    True
                    if (row.get("Open Year-Round") or "").strip().lower() == "yes"
                    else None,
                    True
                    if (row.get("Handicap Accessible") or "").strip().lower()
                    == "yes"
                    else None,
                    f"Location: {location}" if location else None,
                ),
            ),
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, matched_method, match_confidence) VALUES (%s, "parks_toilets", %s, %s, "single_source", 0.300) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name),
            ),
        ]
        if etl_execute(
            conn, statements, source="parks_toilets", record_id=source_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1
    return {"imported": imported, "skipped": skipped, "errors": errors}
