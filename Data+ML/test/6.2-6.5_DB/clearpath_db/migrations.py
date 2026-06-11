import pymysql

from .config import MYSQL_CONFIG
from .db import column_exists, table_exists


DUPLICATE_OBJECT_CODES = {1050, 1060}

MIGRATIONS = [
    {
        "name": "modify venues.venue_type",
        "kind": "always",
        "sql": "ALTER TABLE venues MODIFY COLUMN venue_type ENUM("
        "'restroom','healthcare','emergencyasset','clinic','pharmacy',"
        "'hospital','dentist','laboratory') NOT NULL",
    },
    *[
        {
            "name": f"add {table}.{column}",
            "kind": "column",
            "table": table,
            "column": column,
            "sql": sql,
        }
        for table, column, sql in [
            ("venues", "language_tags", "ALTER TABLE venues ADD COLUMN language_tags JSON AFTER borough"),
            ("venues", "primary_language", "ALTER TABLE venues ADD COLUMN primary_language VARCHAR(10) AFTER language_tags"),
            ("venues", "secondary_language", "ALTER TABLE venues ADD COLUMN secondary_language VARCHAR(10) AFTER primary_language"),
            ("venues", "accessible_status", "ALTER TABLE venues ADD COLUMN accessible_status ENUM('full_access','partial','step_free_route_only','none') DEFAULT 'none' AFTER secondary_language"),
            ("venues", "accessibility_features", "ALTER TABLE venues ADD COLUMN accessibility_features JSON AFTER accessible_status"),
            ("venues", "active_warning", "ALTER TABLE venues ADD COLUMN active_warning BOOLEAN DEFAULT FALSE AFTER accessibility_features"),
            ("venues", "open_now", "ALTER TABLE venues ADD COLUMN open_now BOOLEAN DEFAULT TRUE AFTER active_warning"),
            ("venues", "photos", "ALTER TABLE venues ADD COLUMN photos JSON AFTER opening_hours"),
            ("venues", "rating", "ALTER TABLE venues ADD COLUMN rating DECIMAL(3,2) AFTER photos"),
            ("venues", "weather_risk", "ALTER TABLE venues ADD COLUMN weather_risk ENUM('low','medium','high') DEFAULT 'low' AFTER rating"),
            ("venues", "district", "ALTER TABLE venues ADD COLUMN district VARCHAR(32) DEFAULT NULL AFTER borough"),
            ("user_reports", "anonymous", "ALTER TABLE user_reports ADD COLUMN anonymous BOOLEAN DEFAULT FALSE AFTER accuracy_meters"),
            ("user_reports", "description", "ALTER TABLE user_reports ADD COLUMN description TEXT AFTER anonymous"),
            ("user_reports", "photos", "ALTER TABLE user_reports ADD COLUMN photos JSON AFTER description"),
            ("user_reports", "reported_by", "ALTER TABLE user_reports ADD COLUMN reported_by VARCHAR(50) DEFAULT 'anonymous' AFTER photos"),
            ("user_reports", "expires_in_minutes", "ALTER TABLE user_reports ADD COLUMN expires_in_minutes INT DEFAULT 120 AFTER status"),
            ("user_reports", "default_language", "ALTER TABLE user_reports ADD COLUMN default_language VARCHAR(10) AFTER expires_in_minutes"),
            ("user_reports", "fallback_language", "ALTER TABLE user_reports ADD COLUMN fallback_language VARCHAR(10) AFTER default_language"),
            ("report_confirmations", "language", "ALTER TABLE report_confirmations ADD COLUMN language VARCHAR(10) AFTER action"),
            ("busyness_scores", "forecast_1h", "ALTER TABLE busyness_scores ADD COLUMN forecast_1h JSON AFTER estimated_wait_minutes"),
            ("pedestrian_ramps", "district", "ALTER TABLE pedestrian_ramps ADD COLUMN district VARCHAR(32) DEFAULT NULL AFTER borough"),
        ]
    ],
    {
        "name": "modify busyness_scores.level to 4-level enum",
        "kind": "always",
        "sql": "ALTER TABLE busyness_scores MODIFY COLUMN level "
        "ENUM('quiet','moderate','busy','no_data') DEFAULT NULL",
    },
    {
        "name": "add emergency_assets unique constraint",
        "kind": "index",
        "table": "emergency_assets",
        "column": "uq_emergency_asset_natural",
        "sql": "ALTER TABLE emergency_assets ADD UNIQUE KEY "
        "uq_emergency_asset_natural (venue_id, floor, location_type)",
    },
    {
        "name": "create venue_accessibility",
        "kind": "table",
        "table": "venue_accessibility",
        "sql": "CREATE TABLE IF NOT EXISTS venue_accessibility ("
        "venue_id VARCHAR(36) PRIMARY KEY,"
        "wheelchair_friendly BOOLEAN DEFAULT FALSE,"
        "step_free_route BOOLEAN DEFAULT FALSE,"
        "accessible_toilet BOOLEAN DEFAULT FALSE,"
        "entrance_width_cm INT,"
        "FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE)",
    },
    {
        "name": "create venue_language",
        "kind": "table",
        "table": "venue_language",
        "sql": "CREATE TABLE IF NOT EXISTS venue_language ("
        "venue_id VARCHAR(36) PRIMARY KEY,"
        "language_tag JSON,"
        "language_support_level ENUM('full','partial','none') DEFAULT 'none',"
        "chatbot_enabled BOOLEAN DEFAULT FALSE,"
        "chatbot_welcoming_message TEXT,"
        "FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE)",
    },
    {
        "name": "create venue_warnings",
        "kind": "table",
        "table": "venue_warnings",
        "sql": "CREATE TABLE IF NOT EXISTS venue_warnings ("
        "venue_id VARCHAR(36) PRIMARY KEY,"
        "active_warning BOOLEAN DEFAULT FALSE,"
        "warning_detail TEXT,"
        "wait_alert BOOLEAN DEFAULT FALSE,"
        "replacement_suggestion JSON,"
        "FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE)",
    },
]


def migration_is_applied(conn, migration):
    if migration["kind"] == "column":
        return column_exists(conn, migration["table"], migration["column"])
    if migration["kind"] == "table":
        return table_exists(conn, migration["table"])
    if migration["kind"] == "index":
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s",
                (
                    MYSQL_CONFIG["database"],
                    migration["table"],
                    migration["column"],
                ),
            )
            return cursor.fetchone()[0] > 0
    return False


def apply_migrations(conn, migrations=MIGRATIONS):
    applied = skipped = 0
    for migration in migrations:
        name = migration["name"]
        if migration_is_applied(conn, migration):
            skipped += 1
            continue
        try:
            with conn.cursor() as cursor:
                cursor.execute(migration["sql"])
            conn.commit()
            applied += 1
        except pymysql.MySQLError as error:
            conn.rollback()
            if error.args and error.args[0] in DUPLICATE_OBJECT_CODES:
                skipped += 1
                continue
            raise RuntimeError(f"Migration failed: {name}: {error}") from error
    return {"applied": applied, "skipped": skipped}
