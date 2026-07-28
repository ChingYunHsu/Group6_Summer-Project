import json

import pymysql

from .db import etl_execute, log_etl_error


# parse_lass_languages: Parse LASS language text
# Converts comma-separated language names into ISO language code list
# Input: language_text (e.g. "Spanish, Chinese, Russian")
# Output: ["es", "zh", "ru"] (ISO code list, sorted and deduplicated)
# Special handling:
#   - "designated citywide" / "at least" → returns 6 major languages
#   - "lang:xxx" format → directly extract code
#   - Empty/invalid values → returns empty list
def parse_lass_languages(language_text):
    if not language_text or language_text.strip() in {
        "None",
        "N/A",
        "",
        "One or more languages (specific language not recorded)",
    }:
        return []

    # Language name → ISO code mapping table
    language_map = {
        "spanish": "es",
        "chinese": "zh",
        "russian": "ru",
        "korean": "ko",
        "french": "fr",
        "haitian creole": "ht",
        "arabic": "ar",
        "bengali": "bn",
        "polish": "pl",
        "italian": "it",
        "japanese": "ja",
        "vietnamese": "vi",
        "yiddish": "yi",
        "hebrew": "he",
        "urdu": "ur",
        "gujarati": "gu",
        "tagalog": "tl",
        "french-creole": "ht",
        "french creole": "ht",
    }

    lower_text = language_text.lower()

    # Special case: citywide designated language services → return 6 major languages
    if "designated citywide" in lower_text or "at least" in lower_text:
        return ["es", "zh", "ru", "ko", "fr", "ht"]

    # Parse comma-separated language names one by one
    languages = []
    for part in language_text.split(","):
        normalized = part.strip().rstrip(".").lower()
        if normalized in language_map:
            languages.append(language_map[normalized])
        elif normalized.startswith("lang:"):
            # Support "lang:en" format
            languages.append(normalized.replace("lang:", ""))

    return sorted(set(languages))  # Sort + deduplicate


# find_nearest_venue: Find nearest venue
# Finds the nearest venue record by GPS coordinates
# Input: cursor (DB cursor), lat (latitude), lng (longitude), threshold (distance threshold, default 100m)
# Output: venue_id (nearest venue ID) or None (no match)
# Algorithm: Haversine formula for great-circle distance
def find_nearest_venue(cursor, lat, lng, threshold=100):
    cursor.execute(
        "SELECT venue_id, (6371000 * ACOS("
        "COS(RADIANS(%s)) * COS(RADIANS(latitude)) * "
        "COS(RADIANS(longitude) - RADIANS(%s)) + "
        "SIN(RADIANS(%s)) * SIN(RADIANS(latitude)))) AS dist "
        "FROM venues WHERE latitude != 0 AND longitude != 0 "
        "HAVING dist < %s ORDER BY dist LIMIT 1",
        (lat, lng, lat, threshold),
    )
    row = cursor.fetchone()
    return row[0] if row else None


# etl_venue_language: Language support ETL import function
# Imports LASS language access data into venue_language table
# Input: conn (DB connection), lass_data (LASS CSV data list)
# Flow:
#   1. Filter Manhattan records
#   2. Parse GPS coordinates
#   3. Extract language tags (signs + documents)
#   4. Match nearest venue (GPS < 100m)
#   5. Insert into venue_language table
# Returns: {"imported": success count, "skipped": skip count, "errors": error count}
def etl_venue_language(conn, lass_data):
    imported = skipped = errors = 0   # Statistics counters

    # Step 1: Filter Manhattan records
    manhattan_rows = [ row for row in lass_data if row.get("Borough", "").strip().lower() == "manhattan"]

    # LASS CSV column names (for extracting translated languages)
    signs_column = (
        "Languages in which the facility has translated signs "
        "relating to service being provided"
    )
    documents_column = "Languages in which the facility has translated documents"

    # Step 2-5: Process row by row
    for row in manhattan_rows:
        # Step 2: Parse GPS coordinates
        try:
            lat = float(row.get("Latitude", "").strip())
            lng = float(row.get("Longitude", "").strip())
        except (ValueError, TypeError) as error:
            # Log error and count
            log_etl_error(
                "venue_language", row.get("Facility Name", "<unknown>"), error
            )
            skipped += 1
            errors += 1
            continue

        # Validate Manhattan GPS bounding box
        if not (40.700 <= lat <= 40.880 and -74.020 <= lng <= -73.900):
            skipped += 1
            continue

        # Step 3: Extract language tags (merge signs + documents)
        languages = sorted(set(parse_lass_languages(row.get(signs_column, ""))+ parse_lass_languages(row.get(documents_column, "")) ))

        # Step 4: Determine language support level
        # full: ≥3 languages | partial: has languages but <3 | none: no languages
        level = "full" if len(languages) >= 3 else ("partial" if languages else "none")

        # Step 5: Match nearest venue (GPS < 100m)
        try:
            with conn.cursor() as cursor:
                venue_id = find_nearest_venue(cursor, lat, lng)
        except pymysql.MySQLError as error:
            log_etl_error("venue_language_match", row.get("Facility Name", "<unknown>"), error)
            skipped += 1
            errors += 1
            continue

        if not venue_id:
            skipped += 1
            continue

        # Step 6: Insert into venue_language table
        language_json = json.dumps(languages) if languages else None
        statement = [
            (
                "INSERT INTO venue_language "
                "(venue_id, language_tag, language_support_level, chatbot_enabled) "
                "VALUES (%s, %s, %s, FALSE) "
                "ON DUPLICATE KEY UPDATE language_tag = VALUES(language_tag), "
                "language_support_level = VALUES(language_support_level)",
                (venue_id, language_json, level),
            ),
            (
                "UPDATE venues SET language_tags=%s, primary_language=%s, secondary_language=%s "
                "WHERE venue_id=%s",
                (
                    json.dumps([language.upper() for language in languages]) if languages else None,
                    languages[0].upper() if languages else None,
                    languages[1].upper() if len(languages) > 1 else None,
                    venue_id,
                ),
            ),
        ]
        if etl_execute(
            conn, statement, source="venue_language", record_id=venue_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1

    return {"imported": imported, "skipped": skipped, "errors": errors}
