from .config import SCHEMA_PATH


SCHEMA_TABLES = [
    "venues",
    "venue_source_links",
    "restroom_profiles",
    "healthcare_profiles",
    "emergency_assets",
    "pedestrian_ramps",
    "user_reports",
    "report_confirmations",
    "busyness_scores",
    "external_context_cache",
    "venue_accessibility",
    "venue_language",
    "venue_warnings",
    "users",
    "user_favorite_venues",
    "notification_preferences",
    "report_categories",
    "busyness_forecasts",
    "venue_embeddings",
]


def parse_schema_statements(schema_path=SCHEMA_PATH):
    schema_sql = schema_path.read_text(encoding="utf-8")
    return [statement.strip() for statement in schema_sql.split(";") if statement.strip()]


def rebuild_schema(conn, schema_path=SCHEMA_PATH):
    with conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        try:
            for table in SCHEMA_TABLES:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            for statement in parse_schema_statements(schema_path):
                cursor.execute(statement)
        finally:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    return {"dropped": len(SCHEMA_TABLES), "schema_path": str(schema_path)}


def schema_tables(schema_path=SCHEMA_PATH):
    return [
        statement.split()[5].strip("`")
        for statement in parse_schema_statements(schema_path)
        if statement.upper().startswith("CREATE TABLE IF NOT EXISTS")
    ]
