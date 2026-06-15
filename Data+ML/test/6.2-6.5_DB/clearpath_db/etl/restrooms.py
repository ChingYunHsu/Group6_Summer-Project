from ..db import etl_execute, log_etl_error
from ..validation import gen_vid, gps_to_district, is_manhattan, source_hash


# etl_restrooms: 卫生间 ETL 导入函数
# 功能：将 NYC 公共卫生间 + 公园厕所数据导入数据库
# 输入：conn（数据库连接）, restrooms_data（NYC 卫生间去重数据）, parks_data（公园厕所去重数据）
# 目标表：venues（主表）, restroom_profiles（详情表）, venue_source_links（来源表）
# 返回：{"imported": 成功数, "skipped": 跳过数, "errors": 错误数}
def etl_restrooms(conn, restrooms_data, parks_data):
    imported = skipped = errors = 0   # 统计计数器

    # ──── 循环 1：导入 NYC 公共卫生间 ────
    for row in restrooms_data:
        # 步骤 1：提取并验证基础字段
        name = (row.get("Facility Name") or "").strip()
        try:
            lat, lng = float(row["Latitude"]), float(row["Longitude"])
        except (ValueError, TypeError, KeyError) as error:
            log_etl_error("nyc_restrooms", name or "<missing-name>", error)
            skipped += 1
            errors += 1
            continue
        if not name or not is_manhattan(lat, lng):
            skipped += 1
            continue

        # 步骤 2：生成唯一标识（source_hash → deterministic venue_id）
        source_id = source_hash(name, str(lat), str(lng))
        venue_id = gen_vid("nyc_restrooms", source_id)

        # 步骤 3：解析运营状态
        status_raw = (row.get("Status") or "").strip().lower()
        status = (
            "operational"
            if "operational" in status_raw and "not" not in status_raw
            else "not_operational"
        )

        # 步骤 4：构建三条 INSERT 语句（事务性，一起成功或一起失败）
        statements = [
            # 4a: 插入 venues 主表
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, website, source_confidence) VALUES (%s, "restroom", %s, %s, %s, %s, %s, %s, %s, 0.600) ON DUPLICATE KEY UPDATE name = VALUES(name)',
                (
                    venue_id,
                    name,
                    lat,
                    lng,
                    row.get("Location Type", ""),
                    gps_to_district(lat, lng),
                    (row.get("Location") or "").strip() or None,
                    (row.get("Website") or "").strip() or None,
                ),
            ),
            # 4b: 插入 restroom_profiles 详情表
            (
                "INSERT INTO restroom_profiles (venue_id, restroom_type, operator, status, handicap_accessible, changing_station, additional_notes) VALUES (%s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE status = VALUES(status)",
                (
                    venue_id,
                    (row.get("Restroom Type") or "").strip() or None,
                    (row.get("Operator") or "").strip() or None,
                    status,
                    True
                    if "accessible" in (row.get("Accessibility") or "").lower()
                    and "not" not in (row.get("Accessibility") or "").lower()
                    else None,
                    True
                    if (row.get("Changing Stations") or "").strip().lower() == "yes"
                    else None,
                    (row.get("Additional Notes") or "").strip() or None,
                ),
            ),
            # 4c: 插入 venue_source_links 来源追踪表
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, matched_method, match_confidence) VALUES (%s, "nyc_restrooms", %s, %s, "single_source", 0.600) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name),
            ),
        ]

        # 步骤 5：执行事务（3 条 INSERT 一起提交）
        if etl_execute(
            conn, statements, source="nyc_restrooms", record_id=source_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1

    # ──── 循环 2：导入公园厕所 ────
    # ──── 循环 2：导入公园厕所 ────
    # 注意：公园厕所没有 GPS 坐标，使用 lat=0, lng=0 占位
    for row in parks_data:
        # 步骤 1：验证必填字段（名称 + Borough）
        name = (row.get("Name") or "").strip()
        borough = (row.get("Borough") or "").strip()
        if not name or borough.lower() != "manhattan":
            skipped += 1
            continue

        # 步骤 2：生成唯一标识（只用 name + borough，因为没有坐标）
        source_id = source_hash(name, borough)
        venue_id = gen_vid("parks_toilets", source_id)
        location = (row.get("Location") or "").strip() or None

        # 步骤 3：构建三条 INSERT 语句
        statements = [
            # 3a: 插入 venues 主表（坐标用 0,0 占位，confidence 较低 0.3）
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, source_confidence) VALUES (%s, "restroom", %s, 0, 0, %s, NULL, %s, 0.300) ON DUPLICATE KEY UPDATE name = VALUES(name)',
                (venue_id, name, borough, location),
            ),
            # 3b: 插入 restroom_profiles 详情表
            (
                "INSERT INTO restroom_profiles (venue_id, restroom_type, operator, open_year_round, handicap_accessible, additional_notes) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE additional_notes = VALUES(additional_notes)",
                (
                    venue_id,
                    "park",           # 固定为 "park" 类型
                    "NYC Parks",      # 运营商固定
                    True
                    if (row.get("Open Year-Round") or "").strip().lower() == "yes"
                    else None,
                    #handicap_accessible 字段根据 "Handicap Accessible" 列判断，如果是 "yes" 则为 True，否则为 None（未知），因为公园厕所的无障碍信息可能不完整
                    True
                    if (row.get("Handicap Accessible") or "").strip().lower()
                    == "yes"
                    else None,
                    f"Location: {location}" if location else None,
                ),
            ),
            # 3c: 插入 venue_source_links 来源追踪表（confidence 0.3，低于 NYC 的 0.6）
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, matched_method, match_confidence) VALUES (%s, "parks_toilets", %s, %s, "single_source", 0.300) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name),
            ),
        ]

        # 步骤 4：功能是执行satements，成功则 imported+1，失败则 skipped+1 和 errors+1
        if etl_execute(conn, statements, source="parks_toilets", record_id=source_id):
            imported += 1
        else:
            skipped += 1
            errors += 1

    # 返回导入统计
    return {"imported": imported, "skipped": skipped, "errors": errors}
