import json

import pymysql

from .db import etl_execute, log_etl_error


def parse_lass_languages(language_text):
    if not language_text or language_text.strip() in {
        "None",
        "N/A",
        "",
        "One or more languages (specific language not recorded)",
    }:
        return []
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
    if "designated citywide" in lower_text or "at least" in lower_text:
        return ["es", "zh", "ru", "ko", "fr", "ht"]
    languages = []
    for part in language_text.split(","):
        normalized = part.strip().rstrip(".").lower()
        if normalized in language_map:
            languages.append(language_map[normalized])
        elif normalized.startswith("lang:"):
            languages.append(normalized.replace("lang:", ""))
    return sorted(set(languages))


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


def etl_venue_language(conn, lass_data):
    imported = skipped = errors = 0
    manhattan_rows = [
        row
        for row in lass_data
        if row.get("Borough", "").strip().lower() == "manhattan"
    ]
    signs_column = (
        "Languages in which the facility has translated signs "
        "relating to service being provided"
    )
    documents_column = "Languages in which the facility has translated documents"
    for row in manhattan_rows:
        try:
            lat = float(row.get("Latitude", "").strip())
            lng = float(row.get("Longitude", "").strip())
        except (ValueError, TypeError) as error:
            log_etl_error(
                "venue_language", row.get("Facility Name", "<unknown>"), error
            )
            skipped += 1
            errors += 1
            continue
        if not (40.700 <= lat <= 40.880 and -74.020 <= lng <= -73.900):
            skipped += 1
            continue
        languages = sorted(
            set(
                parse_lass_languages(row.get(signs_column, ""))
                + parse_lass_languages(row.get(documents_column, ""))
            )
        )
        level = "full" if len(languages) >= 3 else ("partial" if languages else "none")
        try:
            with conn.cursor() as cursor:
                venue_id = find_nearest_venue(cursor, lat, lng)
        except pymysql.MySQLError as error:
            log_etl_error(
                "venue_language_match", row.get("Facility Name", "<unknown>"), error
            )
            skipped += 1
            errors += 1
            continue
        if not venue_id:
            skipped += 1
            continue
        statement = (
            "INSERT INTO venue_language "
            "(venue_id, language_tag, language_support_level, chatbot_enabled) "
            "VALUES (%s, %s, %s, FALSE) "
            "ON DUPLICATE KEY UPDATE language_tag = VALUES(language_tag), "
            "language_support_level = VALUES(language_support_level)",
            (venue_id, json.dumps(languages) if languages else None, level),
        )
        if etl_execute(
            conn, statement, source="venue_language", record_id=venue_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1
    return {"imported": imported, "skipped": skipped, "errors": errors}
