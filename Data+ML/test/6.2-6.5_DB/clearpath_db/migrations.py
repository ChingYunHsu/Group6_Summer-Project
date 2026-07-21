import pymysql

from .config import MYSQL_CONFIG
from .db import column_exists, table_exists


DUPLICATE_OBJECT_CODES = {1050, 1060}  # MySQL: 表/列已存在

# MIGRATIONS: 数据库迁移定义列表
# 每个迁移包含 name（名称）、kind（类型）、sql（SQL语句）
# kind 类型："column"=检查列、"table"=检查表、"index"=检查索引、"always"=每次都执行#
MIGRATIONS = [
    # ──── 类型 1: 修改列定义（ MODIFY COLUMN：重复执行安全）────
    {
        "name": "modify venues.venue_type",
        "kind": "always",
        "sql": "ALTER TABLE venues MODIFY COLUMN venue_type ENUM("
        "'restroom','healthcare','emergencyasset','clinic','pharmacy',"
        "'hospital','dentist','laboratory') NOT NULL",
    },
    # ──── 类型 2: 添加新列────
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
            ("venues", "accessible_status", "ALTER TABLE venues ADD COLUMN accessible_status ENUM('full_access','partial','step_free_route_only','none','unknown') DEFAULT 'unknown' AFTER secondary_language"),
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
    # ──── 类型 3: 修改枚举值（把 busyness_scores.level 从 3 级枚举扩展为 4 级）────
    {
        "name": "modify busyness_scores.level to 4-level enum",
        "kind": "always",
        "sql": "ALTER TABLE busyness_scores MODIFY COLUMN level "
        "ENUM('quiet','moderate','busy','no_data') DEFAULT NULL",
    },
    # ──── 类型 4: 添加唯一约束（防止重复数据,动态添加过程应用）────
    {
        "name": "add emergency_assets unique constraint",
        "kind": "index",
        "table": "emergency_assets",
        "column": "uq_emergency_asset_natural",
        "sql": "ALTER TABLE emergency_assets ADD UNIQUE KEY "
        "uq_emergency_asset_natural (venue_id, floor, location_type)",
    },
    # ──── 类型 5: 创建新表（table = 检查表是否存在）────
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

# migration_is_applied: 检查迁移是否已应用
# 根据迁移类型检查数据库中是否已存在该列/表/索引
# 返回：True（已应用）, False（未应用）
def migration_is_applied(conn, migration):
    if migration["kind"] == "column":
        # 检查列是否存在
        return column_exists(conn, migration["table"], migration["column"])
    if migration["kind"] == "table":
        # 检查表是否存在
        return table_exists(conn, migration["table"])
    if migration["kind"] == "index":
        # 检查索引是否存在（通过 information_schema.STATISTICS）
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


# apply_migrations: 应用所有迁移
# 遍历迁移列表，跳过已应用的，执行未应用的
# 返回：{"applied": 已应用数, "skipped": 跳过数}
def apply_migrations(conn, migrations=MIGRATIONS):
    applied = skipped = 0   # 统计计数器

    for migration in migrations:
        name = migration["name"]

        # 步骤 1：检查是否已应用
        if migration_is_applied(conn, migration):
            skipped += 1
            continue

        # 步骤 2：执行 SQL
        try:
            with conn.cursor() as cursor:
                cursor.execute(migration["sql"])
            conn.commit()
            applied += 1
        except pymysql.MySQLError as error:
            conn.rollback()
            # 步骤 3：处理重复对象错误（1050/1060 = 列/表/索引已存在）
            if error.args and error.args[0] in DUPLICATE_OBJECT_CODES:
                skipped += 1
                continue
            # 其他错误：抛出异常
            raise RuntimeError(f"Migration failed: {name}: {error}") from error

    return {"applied": applied, "skipped": skipped}
