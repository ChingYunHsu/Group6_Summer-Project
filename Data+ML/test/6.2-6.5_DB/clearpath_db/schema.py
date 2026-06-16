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

# helper function to parse schema.sql file into list of statements, return list of strings
def parse_schema_statements(schema_path=SCHEMA_PATH):
    schema_sql = schema_path.read_text(encoding="utf-8")
    return [statement.strip() for statement in schema_sql.split(";") if statement.strip()]

# helper function to get list of table names from schema.sql, return list of strings
def schema_tables(schema_path=SCHEMA_PATH):
    return [
        statement.split()[5].strip("`")
        for statement in parse_schema_statements(schema_path)
        if statement.upper().startswith("CREATE TABLE IF NOT EXISTS")
    ]

# helper function to rebuild schema by dropping all tables and recreating them from schema.sql, return dict of dropped table count and schema path
def rebuild_schema(conn, schema_path=SCHEMA_PATH):
    with conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        try:    
            # drop all tables.
            for table in SCHEMA_TABLES:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                # recreate tables from schema.sql
            for statement in parse_schema_statements(schema_path):
                cursor.execute(statement)
        finally:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    return {"dropped": len(SCHEMA_TABLES), "schema_path": str(schema_path)}
