import datetime

from ..db import etl_execute, log_etl_error
from ..validation import gen_vid, gps_to_district, safe_int, source_hash


def etl_aed(conn, data):
    imported = skipped = errors = 0
    for row in data:
        name = (row.get("Entity_Name") or "").strip()
        if not name:
            skipped += 1
            continue
        try:
            lat, lng = float(row["Latitude"]), float(row["Longitude"])
        except (ValueError, TypeError, KeyError) as error:
            log_etl_error("aed_inventory", name, error)
            skipped += 1
            errors += 1
            continue
        if (row.get("Borough") or "").strip().lower() != "manhattan":
            skipped += 1
            continue
        address = (row.get("Address") or "").strip()
        floor = (row.get("Floor") or "").strip()
        source_id = source_hash(name, address, floor)
        venue_id = gen_vid("aed_inventory", source_id)
        last_updated = None
        last_updated_raw = (row.get("Last Updated") or "").strip()
        if last_updated_raw:
            try:
                last_updated = datetime.datetime.strptime(
                    last_updated_raw, "%m/%d/%Y"
                ).strftime("%Y-%m-%d")
            except ValueError as error:
                log_etl_error("aed_inventory", source_id, error)
                errors += 1
        statements = [
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, source_confidence) VALUES (%s, "emergencyasset", %s, %s, %s, %s, %s, %s, 0.800) ON DUPLICATE KEY UPDATE name = VALUES(name)',
                (
                    venue_id,
                    f"{name} AED",
                    lat,
                    lng,
                    (row.get("Borough") or "").strip() or None,
                    gps_to_district(lat, lng),
                    address or None,
                ),
            ),
            (
                'INSERT INTO emergency_assets (venue_id, asset_type, floor, location_type, aed_count, trained_people_count, community_district, council_district, last_updated) VALUES (%s, "aed", %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE aed_count = VALUES(aed_count)',
                (
                    venue_id,
                    floor or None,
                    (row.get("Location Type") or "").strip() or None,
                    safe_int(row.get("AED_NumAeds")),
                    safe_int(row.get("AED_NumPersonTrained")),
                    (row.get("Community_District") or "").strip() or None,
                    (row.get("Council_District") or "").strip() or None,
                    last_updated,
                ),
            ),
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, raw_location_text, matched_method, match_confidence) VALUES (%s, "aed_inventory", %s, %s, %s, "single_source", 0.800) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name, address),
            ),
        ]
        if etl_execute(
            conn, statements, source="aed_inventory", record_id=source_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1
    return {"imported": imported, "skipped": skipped, "errors": errors}
