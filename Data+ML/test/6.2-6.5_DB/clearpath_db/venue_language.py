import json

import pymysql

from .db import etl_execute, log_etl_error


# parse_lass_languages: 解析 LASS 语言文本
# 功能：将逗号分隔的语言名称转换为 ISO 语言代码列表
# 输入：language_text（如 "Spanish, Chinese, Russian"）
# 输出：["es", "zh", "ru"]（ISO 代码列表，已排序去重）
# 特殊处理：
#   - "designated citywide" / "at least" → 返回 6 种主要语言
#   - "lang:xxx" 格式 → 直接提取代码
#   - 空值/无效值 → 返回空列表
def parse_lass_languages(language_text):
    if not language_text or language_text.strip() in {
        "None",
        "N/A",
        "",
        "One or more languages (specific language not recorded)",
    }:
        return []

    # 语言名称 → ISO 代码映射表
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

    # 特殊情况：全市指定语言服务点 → 返回 6 种主要语言
    if "designated citywide" in lower_text or "at least" in lower_text:
        return ["es", "zh", "ru", "ko", "fr", "ht"]

    # 逐个解析逗号分隔的语言名称
    languages = []
    for part in language_text.split(","):
        normalized = part.strip().rstrip(".").lower()
        if normalized in language_map:
            languages.append(language_map[normalized])
        elif normalized.startswith("lang:"):
            # 支持 "lang:en" 格式
            languages.append(normalized.replace("lang:", ""))

    return sorted(set(languages))  # 排序 + 去重


# find_nearest_venue: 查找最近的场所
# 功能：根据 GPS 坐标查找最近的 venues 记录
# 输入：cursor（数据库游标）, lat（纬度）, lng（经度）, threshold（距离阈值，默认100米）
# 输出：venue_id（最近场所ID）或 None（无匹配）
# 算法：Haversine 公式计算球面距离
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


# etl_venue_language: 语言支持 ETL 导入函数
# 功能：将 LASS 语言访问数据导入 venue_language 表
# 输入：conn（数据库连接）, lass_data（LASS CSV 数据列表）
# 流程：
#   1. 筛选曼哈顿记录
#   2. 解析 GPS 坐标
#   3. 提取语言标签（signs + documents）
#   4. 匹配最近场所（GPS < 100m）
#   5. 插入 venue_language 表
# 返回：{"imported": 成功数, "skipped": 跳过数, "errors": 错误数}
def etl_venue_language(conn, lass_data):
    imported = skipped = errors = 0   # 统计计数器

    # 步骤 1：筛选曼哈顿记录
    manhattan_rows = [ row for row in lass_data if row.get("Borough", "").strip().lower() == "manhattan"]

    # LASS CSV 中的列名（用于提取翻译语言）
    signs_column = (
        "Languages in which the facility has translated signs "
        "relating to service being provided"
    )
    documents_column = "Languages in which the facility has translated documents"

    # 步骤 2-5：逐条处理
    for row in manhattan_rows:
        # 步骤 2：解析 GPS 坐标
        try:
            lat = float(row.get("Latitude", "").strip())
            lng = float(row.get("Longitude", "").strip())
        except (ValueError, TypeError) as error:
            # 记录错误日志并统计
            log_etl_error(
                "venue_language", row.get("Facility Name", "<unknown>"), error
            )
            skipped += 1
            errors += 1
            continue

        # 验证曼哈顿 GPS 边界框
        if not (40.700 <= lat <= 40.880 and -74.020 <= lng <= -73.900):
            skipped += 1
            continue

        # 步骤 3：提取语言标签（合并 signs + documents）
        languages = sorted(set(parse_lass_languages(row.get(signs_column, ""))+ parse_lass_languages(row.get(documents_column, "")) ))

        # 步骤 4：确定语言支持等级
        # full: ≥3 种语言 | partial: 有语言但 <3 种 | none: 无语言
        level = "full" if len(languages) >= 3 else ("partial" if languages else "none")

        # 步骤 5：匹配最近场所（GPS < 100m）
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

        # 步骤 6：插入 venue_language 表
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
