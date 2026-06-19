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

# reporting.py: 数据库报告函数
# 功能：提供数据库状态和数据质量的报告函数
# 包含以下函数：
#   - table_counts(conn, tables=DEFAULT_TABLES): 返回指定表的记录数

def table_counts(conn, tables=DEFAULT_TABLES):
    counts = {}
    with conn.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
    return counts

#   - database_integrity(conn): 返回数据库完整性检查结果，包括缺失名称、缺失坐标和孤立来源链接的计数
def database_integrity(conn):
    checks = {}
    with conn.cursor() as cursor:
        # 检查 venues 表中缺失名称的记录数
        cursor.execute("SELECT COUNT(*) FROM venues WHERE name IS NULL OR name = ''")
        checks["venues_missing_name"] = cursor.fetchone()[0]
        # 检查 venues 表中缺失坐标的记录数
        cursor.execute(
            "SELECT COUNT(*) FROM venues "
            "WHERE latitude IS NULL OR longitude IS NULL"
        )
        checks["venues_missing_coordinates"] = cursor.fetchone()[0]
        # 检查孤立的来源链接
        cursor.execute(
            "SELECT COUNT(*) FROM venue_source_links links "
            "LEFT JOIN venues ON venues.venue_id = links.venue_id "
            "WHERE venues.venue_id IS NULL"
        )
        checks["orphan_source_links"] = cursor.fetchone()[0]
    return checks
