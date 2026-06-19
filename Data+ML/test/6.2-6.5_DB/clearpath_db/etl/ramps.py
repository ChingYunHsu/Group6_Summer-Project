import re

from ..db import etl_executemany, log_etl_error
from ..validation import gps_to_district, safe_dec


RAMP_INSERT_SQL = (
    "INSERT INTO pedestrian_ramps "
    "(ramp_id, corner_id, latitude, longitude, borough, district, on_street, "
    "cross_street_1, cross_street_2, ramp_width, ramp_slope, dws_condition, "
    "ponding, obstacles_ramp, obstacles_landing) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
    "ON DUPLICATE KEY UPDATE dws_condition = VALUES(dws_condition)"
)

# etl_ramps: 行人坡道 ETL 导入函数
# 功能：将去重后的行人坡道数据导入数据库
# 输入：conn（数据库连接）, data（dedup_ramps 去重后的数据）
# 目标表：pedestrian_ramps（主表）
# 去重规则（已在 dedup 阶段完成）：
#   - 去重键：RampID（坡道唯一标识）
#   - 过滤：Borough == "1"（曼哈顿行政区代码）
#   - 保留策略：同一 RampID 只保留一条记录
# 返回：{"imported": 成功数, "skipped": 跳过数, "errors": 错误数}
def etl_ramps(conn, data):
    imported = skipped = errors = 0
    batch = []

    for row in data:
        if (row.get("Borough") or "").strip() != "1":
            skipped += 1
            continue
        # 提取 RampID 和 GPS 坐标，验证格式和有效性
        match = re.match(
            r"POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)",
            (row.get("the_geom") or "").strip(),
        )
        # 验证 RampID 和 GPS 坐标的存在和有效性，如果缺失或无效则跳过并统计
        ramp_id = (row.get("RampID") or "").strip()
        if not match or not ramp_id:
            skipped += 1
            continue
        try:
            lng, lat = float(match.group(1)), float(match.group(2))
        except (ValueError, TypeError) as error:
            log_etl_error("pedestrian_ramps", ramp_id, error)
            skipped += 1
            errors += 1
            continue
        batch.append(
            (
                ramp_id,
                (row.get("CornerID") or "").strip() or None,
                lat,
                lng,
                "Manhattan",
                gps_to_district(lat, lng),
                (row.get("Ramp_OnStreet") or "").strip() or None,
                (row.get("StName1") or "").strip() or None,
                (row.get("StName2") or "").strip() or None,
                safe_dec(row.get("RAMP_WIDTH")),
                safe_dec(row.get("RAMP_RUNNING_SLOPE_TOTAL")),
                (row.get("DWS_CONDITIONS") or "").strip() or None,
                (row.get("PONDING") or "").strip() or None,
                (row.get("OBSTACLES_RAMP") or "").strip() or None,
                (row.get("OBSTACLES_LANDING") or "").strip() or None,
            )
        )
        #当批次达到 1000 条时执行批量插入，成功则 imported+成功数，失败则 skipped+失败数 和 errors+失败数，然后清空批次列表继续处理剩余数据`
        if len(batch) >= 1000:
            success, failed = etl_executemany(
                conn,
                RAMP_INSERT_SQL,
                batch,
                source="pedestrian_ramps",
                record_id=f"batch-ending-{ramp_id}",
            )
            imported += success
            skipped += failed
            errors += failed
            batch = []
    
    # 这里的 record_id 使用了当前批次最后一条记录的 RampID，方便追踪哪个批次出现了问题
    if batch:
        success, failed = etl_executemany(
            conn,
            RAMP_INSERT_SQL,
            batch,
            source="pedestrian_ramps",
            record_id="final-batch",
        )
        imported += success
        skipped += failed
        errors += failed
    return {"imported": imported, "skipped": skipped, "errors": errors}
