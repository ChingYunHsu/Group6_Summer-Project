DEFAULT_TABLES = [
    "venues",
    "venue_source_links",
    "restroom_profiles",
    "healthcare_profiles",
    "emergency_assets",
    "pedestrian_ramps",
    "user_reports",
    "busyness_scores",
]


def table_counts(conn, tables=DEFAULT_TABLES):
    counts = {}
    with conn.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
    return counts


def database_integrity(conn):
    checks = {}
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM venues WHERE name IS NULL OR name = ''")
        checks["venues_missing_name"] = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM venues "
            "WHERE latitude IS NULL OR longitude IS NULL"
        )
        checks["venues_missing_coordinates"] = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM venue_source_links links "
            "LEFT JOIN venues ON venues.venue_id = links.venue_id "
            "WHERE venues.venue_id IS NULL"
        )
        checks["orphan_source_links"] = cursor.fetchone()[0]
    return checks
