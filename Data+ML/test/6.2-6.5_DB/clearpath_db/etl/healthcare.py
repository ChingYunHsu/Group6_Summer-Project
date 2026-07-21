from ..config import OSM_CATEGORY_MAP
from ..db import etl_execute, log_etl_error
from ..validation import gen_vid, gps_to_district, is_manhattan, source_hash


VENUE_SUBTYPES = {"hospital", "clinic", "pharmacy", "dentist", "laboratory"}
WHEELCHAIR_STATUS = {
    "yes": "full_access",
    "limited": "partial",
    "designated": "partial",
    "assisted": "partial",
    "separate": "partial",
    "no": "none",
}


def classify_nys_venue_type(row):
    """Map official NYS facility metadata to the venue enum.

    The original facility type remains in ``healthcare_profiles``; this
    classification only controls the user-facing ``venues.venue_type``.
    """
    text = " ".join(
        (row.get(field) or "").strip().lower()
        for field in (
            "Facility Type",
            "Short Description",
            "Description",
            "Facility Name",
        )
    )
    # Hospital-sponsored school health programmes are clinical access points,
    # not acute-care hospitals.  Keep their source type in healthcare_profiles
    # but exclude them from the emergency-facing Hospital filter.
    if any(marker in text for marker in (
        "hosp-sb", "hospital-sponsored school health",
        "hospital sponsored school health", "school-based health",
        "school based health",
    )):
        return "healthcare"
    for keyword, venue_type in (
        ("pharmacy", "pharmacy"),
        ("pharm", "pharmacy"),
        ("dent", "dentist"),
        ("laborator", "laboratory"),
        ("diagnostic lab", "laboratory"),
        ("hospital", "hospital"),
        ("clinic", "clinic"),
        ("ambulatory", "clinic"),
        ("primary care", "clinic"),
    ):
        if keyword in text:
            return venue_type
    return "healthcare"


def _accessibility_values(feature):
    """Return trusted OSM accessibility values, or ``None`` when unlabelled."""
    props = feature.get("properties", {})
    wheelchair = (props.get("wheelchair") or "").strip().lower()
    toilet = (props.get("toilets:wheelchair") or "").strip().lower()
    status = WHEELCHAIR_STATUS.get(wheelchair)
    accessible_toilet = toilet in {"yes", "designated"}
    if status is None and not accessible_toilet:
        return None
    return status, status == "full_access", accessible_toilet


def _is_osm_healthcare(props):
    venue_type = OSM_CATEGORY_MAP.get((props.get("healthcare") or "").strip().lower())
    venue_type = venue_type or OSM_CATEGORY_MAP.get(
        (props.get("amenity") or "").strip().lower()
    )
    return venue_type in VENUE_SUBTYPES


def _etl_osm_accessibility(conn, accessibility_data):
    """Attach OSM wheelchair tags only to existing OSM healthcare venues.

    The OSM object id is the join key.  We deliberately do not spatially infer
    accessibility for NYS facilities, and retain OSM provenance in both the
    source-link table and the venue JSON metadata.
    """
    processed = errors = 0
    for feature in accessibility_data or []:
        props = feature.get("properties", {})
        if not _is_osm_healthcare(props):
            continue
        source_id = (props.get("@id") or "").strip()
        values = _accessibility_values(feature)
        if not source_id or values is None:
            continue
        status, wheelchair_friendly, accessible_toilet = values
        statements = [
            (
                "INSERT INTO venue_accessibility "
                "(venue_id, wheelchair_friendly, accessible_toilet) "
                "SELECT links.venue_id, %s, %s "
                "FROM venue_source_links AS links "
                "JOIN healthcare_profiles AS profiles ON profiles.venue_id = links.venue_id "
                "WHERE links.source_name = 'osm' AND links.source_record_id = %s "
                "ON DUPLICATE KEY UPDATE wheelchair_friendly = VALUES(wheelchair_friendly), "
                "accessible_toilet = VALUES(accessible_toilet)",
                (wheelchair_friendly, accessible_toilet, source_id),
            ),
            (
                "INSERT INTO venue_source_links "
                "(venue_id, source_name, source_record_id, raw_name, matched_method, match_confidence) "
                "SELECT links.venue_id, 'osm_accessibility', %s, %s, 'exact_source_id', 0.500 "
                "FROM venue_source_links AS links "
                "JOIN healthcare_profiles AS profiles ON profiles.venue_id = links.venue_id "
                "WHERE links.source_name = 'osm' AND links.source_record_id = %s "
                "ON DUPLICATE KEY UPDATE raw_name = VALUES(raw_name), "
                "match_confidence = VALUES(match_confidence)",
                (source_id, (props.get("name") or "").strip() or None, source_id),
            ),
        ]
        if status is not None:
            statements.append(
                (
                    "UPDATE venues AS venue "
                    "JOIN venue_source_links AS links ON links.venue_id = venue.venue_id "
                    "JOIN healthcare_profiles AS profiles ON profiles.venue_id = venue.venue_id "
                    "SET venue.accessible_status = %s, "
                    "venue.accessibility_features = JSON_SET("
                    "COALESCE(venue.accessibility_features, JSON_OBJECT()), "
                    "'$.wheelchair', %s, '$.toilets_wheelchair', %s, '$.source', 'OSM') "
                    "WHERE links.source_name = 'osm' AND links.source_record_id = %s",
                    (status, status, accessible_toilet, source_id),
                )
            )
        if etl_execute(conn, statements, source="osm_accessibility", record_id=source_id):
            processed += 1
        else:
            errors += 1
    return processed, errors


def etl_healthcare(conn, nys_data, osm_data, accessibility_data=None):
    imported = skipped = errors = 0
    for row in nys_data:
        name = (row.get("Facility Name") or "").strip()
        if (row.get("Facility County") or "").strip() != "New York" or not name:
            continue
        try:
            lat = float(row.get("Facility Latitude", ""))
            lng = float(row.get("Facility Longitude", ""))
        except (ValueError, TypeError) as error:
            log_etl_error("nys_health", name, error)
            skipped += 1
            errors += 1
            continue
        if not is_manhattan(lat, lng):
            continue
        facility_id = (row.get("Facility ID") or "").strip()
        source_id = facility_id or source_hash(name, str(lat), str(lng))
        venue_id = gen_vid("nys_health", source_id)
        address = ", ".join(
            filter(
                None,
                (
                    (row.get(field) or "").strip()
                    for field in ("Facility Address 1", "Facility Address 2")
                ),
            )
        ) or None
        healthcare_type = classify_nys_venue_type(row)
        statements = [
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, phone, website, source_confidence, accessible_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0.900, "unknown") ON DUPLICATE KEY UPDATE venue_type = VALUES(venue_type), name = VALUES(name)',
                (
                    venue_id,
                    healthcare_type,
                    name,
                    lat,
                    lng,
                    "Manhattan",
                    gps_to_district(lat, lng),
                    address,
                    (row.get("Facility Phone Number") or "").strip() or None,
                    (row.get("Facility Website") or "").strip() or None,
                ),
            ),
            (
                "INSERT INTO healthcare_profiles (venue_id, facility_external_id, facility_type, healthcare_category, operator_name, ownership_type, official_source_priority) VALUES (%s, %s, %s, %s, %s, %s, 1) ON DUPLICATE KEY UPDATE facility_type = VALUES(facility_type), healthcare_category = VALUES(healthcare_category), operator_name = VALUES(operator_name), ownership_type = VALUES(ownership_type)",
                (
                    venue_id,
                    facility_id,
                    (row.get("Short Description") or "").strip() or None,
                    healthcare_type,
                    (row.get("Operator Name") or "").strip() or None,
                    (row.get("Ownership Type") or "").strip() or None,
                ),
            ),
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, raw_location_text, matched_method, match_confidence) VALUES (%s, "nys_health", %s, %s, %s, "single_source", 0.900) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name, address),
            ),
        ]
        if etl_execute(conn, statements, source="nys_health", record_id=source_id):
            imported += 1
        else:
            skipped += 1
            errors += 1

    for feature in osm_data:
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            skipped += 1
            continue
        lng, lat = coords[0], coords[1]
        if not is_manhattan(lat, lng):
            skipped += 1
            continue
        props = feature.get("properties", {})
        name = (props.get("name") or "").strip()
        osm_id = (props.get("@id") or "").strip()
        source_id = osm_id or source_hash(name or "unknown", str(lat), str(lng))
        venue_id = gen_vid("osm", source_id)
        healthcare_type = OSM_CATEGORY_MAP.get(
            (props.get("healthcare") or "").strip().lower()
        ) or OSM_CATEGORY_MAP.get((props.get("amenity") or "").strip().lower())
        if healthcare_type not in VENUE_SUBTYPES:
            skipped += 1
            continue
        house_number = props.get("addr:housenumber", "")
        street = props.get("addr:street", "")
        address = (
            f"{house_number} {street}"
            if house_number and street
            else (street or None)
        )
        statements = [
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, phone, website, opening_hours, source_confidence) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0.500) ON DUPLICATE KEY UPDATE venue_type = VALUES(venue_type), name = VALUES(name)',
                (
                    venue_id,
                    healthcare_type,
                    name or None,
                    lat,
                    lng,
                    (props.get("addr:city") or "").strip() or None,
                    gps_to_district(lat, lng),
                    address,
                    (props.get("phone") or props.get("contact:phone") or "").strip()
                    or None,
                    (props.get("website") or "").strip() or None,
                    (props.get("opening_hours") or "").strip() or None,
                ),
            ),
            (
                "INSERT INTO healthcare_profiles (venue_id, healthcare_category, facility_type, healthcare_speciality) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE healthcare_category = VALUES(healthcare_category)",
                (
                    venue_id,
                    healthcare_type,
                    healthcare_type,
                    (props.get("healthcare:speciality") or "").strip() or None,
                ),
            ),
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, matched_method, match_confidence) VALUES (%s, "osm", %s, %s, "single_source", 0.500) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name or "unknown"),
            ),
        ]
        if etl_execute(
            conn, statements, source="osm_healthcare", record_id=source_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1
    accessibility_processed, accessibility_errors = _etl_osm_accessibility(
        conn, accessibility_data
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors + accessibility_errors,
        "accessibility_processed": accessibility_processed,
    }
