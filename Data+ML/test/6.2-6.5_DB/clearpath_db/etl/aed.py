import datetime

from ..db import etl_execute, log_etl_error
from ..validation import gen_vid, gps_to_district, safe_int, source_hash


# etl_aed: AED 自动体外除颤器 ETL 导入函数
# 功能：将去重后的 AED 数据导入数据库
# 输入：conn（数据库连接）, data（dedup_aed 去重后的数据）
# 目标表：venues（主表）, emergency_assets（AED 详情表）, venue_source_links（来源表）
# 去重规则（已在 dedup 阶段完成）：
#   - 去重键：Entity_Name|Address|Floor（实体名+地址+楼层）
#   - 过滤：Borough == "manhattan"
#   - 保留策略：同一实体/地址/楼层只保留一条记录
# 返回：{"imported": 成功数, "skipped": 跳过数, "errors": 错误数}
def etl_aed(conn, data):
    imported = skipped = errors = 0   # 统计计数器

    for row in data:
        # 步骤 1：验证必填字段（实体名称）
        name = (row.get("Entity_Name") or "").strip()
        if not name:
            skipped += 1
            continue

        # 步骤 2：验证 GPS 坐标
        try:
            lat, lng = float(row["Latitude"]), float(row["Longitude"])
        except (ValueError, TypeError, KeyError) as error:
            log_etl_error("aed_inventory", name, error)
            skipped += 1
            errors += 1
            continue

        # 步骤 3：验证 Borough（曼哈顿）
        if (row.get("Borough") or "").strip().lower() != "manhattan":
            skipped += 1
            continue

        # 步骤 4：提取地址和楼层（用于去重键和存储）
        address = (row.get("Address") or "").strip()
        floor = (row.get("Floor") or "").strip()

        # 步骤 5：生成唯一标识（基于 name + address + floor）
        source_id = source_hash(name, address, floor)
        venue_id = gen_vid("aed_inventory", source_id)

        # 步骤 6：解析日期字段（格式：MM/DD/YYYY → YYYY-MM-DD）
        last_updated = None
        last_updated_raw = (row.get("Last Updated") or "").strip()
        if last_updated_raw:
            try:
                last_updated = datetime.datetime.strptime(
                    last_updated_raw, "%m/%d/%Y"
                ).strftime("%Y-%m-%d")
            except ValueError as error:
                log_etl_error("aed_inventory", source_id, error)
                errors += 1
        # 步骤 7：构建三条 INSERT 语句（事务性）
        statements = [
            # 7a: 插入 venues 主表（confidence 0.8，高于卫生间）
            (
                'INSERT INTO venues (venue_id, venue_type, name, latitude, longitude, borough, district, address, source_confidence) VALUES (%s, "emergencyasset", %s, %s, %s, %s, %s, %s, 0.800) ON DUPLICATE KEY UPDATE name = VALUES(name)',
                (
                    venue_id,
                    f"{name} AED",   # 名称后缀加 "AED" 以区分
                    lat,
                    lng,
                    (row.get("Borough") or "").strip() or None,
                    gps_to_district(lat, lng),
                    address or None,
                ),
            ),
            # 7b: 插入 emergency_assets 详情表
            (
                'INSERT INTO emergency_assets (venue_id, asset_type, floor, location_type, aed_count, trained_people_count, community_district, council_district, last_updated) VALUES (%s, "aed", %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE aed_count = VALUES(aed_count)',
                (
                    venue_id,
                    floor or None,
                    (row.get("Location Type") or "").strip() or None,
                    safe_int(row.get("AED_NumAeds")),              # AED 数量
                    safe_int(row.get("AED_NumPersonTrained")),     # 受训人员数
                    (row.get("Community_District") or "").strip() or None,
                    (row.get("Council_District") or "").strip() or None,
                    last_updated,
                ),
            ),
            # 7c: 插入 venue_source_links 来源追踪表
            (
                'INSERT INTO venue_source_links (venue_id, source_name, source_record_id, raw_name, raw_location_text, matched_method, match_confidence) VALUES (%s, "aed_inventory", %s, %s, %s, "single_source", 0.800) ON DUPLICATE KEY UPDATE match_confidence = VALUES(match_confidence)',
                (venue_id, source_id, name, address),
            ),
        ]

        # 步骤 8：执行事务
        if etl_execute(
            conn, statements, source="aed_inventory", record_id=source_id
        ):
            imported += 1
        else:
            skipped += 1
            errors += 1
    return {"imported": imported, "skipped": skipped, "errors": errors}
