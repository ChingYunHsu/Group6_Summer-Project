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


def etl_ramps(conn, data):
    imported = skipped = errors = 0
    batch = []
    for row in data:
        if (row.get("Borough") or "").strip() != "1":
            skipped += 1
            continue
        match = re.match(
            r"POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)",
            (row.get("the_geom") or "").strip(),
        )
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
