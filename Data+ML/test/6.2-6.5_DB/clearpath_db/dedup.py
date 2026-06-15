from .validation import is_manhattan


# _stats: 辅助函数，计算去重统计信息
# 输入：总记录数、去重后数量、重复数量
# 输出：包含 input/unique/duplicates/filtered 的字典
def _stats(input_count, unique_count, duplicate_count):
    return {
        "input": input_count,
        "unique": unique_count,
        "duplicates": duplicate_count,
        "filtered": input_count - unique_count - duplicate_count,
    }


# dedup_restrooms: NYC 公共卫生间去重
# 去重键：name.lower()（设施名称小写）
# 过滤：曼哈顿 GPS 边界框 + 验证经纬度
# 返回：(去重后数据, 统计字典)
def dedup_restrooms(restrooms_data):
    seen, deduped, duplicates = set(), [], 0
    for row in restrooms_data:
        name = (row.get("Facility Name") or "").strip()
        try:
            lat = float(row.get("Latitude", 0) or 0)
            lng = float(row.get("Longitude", 0) or 0)
        except (ValueError, TypeError, KeyError):
            continue
        if not name or not is_manhattan(lat, lng):
            continue
        # keep the same name expressions with different cases,
        key = name.lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, _stats(len(restrooms_data), len(deduped), duplicates)


# dedup_parks: 公园厕所去重
# 去重键：name.lower()（公园名称小写）
# 过滤：Borough == "manhattan"（无 GPS 坐标）
# 返回：(去重后数据, 统计字典),seen 用来存储以访问变量,duplicated 用来统计重复数量,最后返回去重后的数据和统计信息
def dedup_parks(parks_data):
    seen, deduped, duplicates = set(), [], 0
    for row in parks_data:
        name = (row.get("Name") or "").strip()
        borough = (row.get("Borough") or "").strip()
        # name and borough check
        if not name or borough.lower() != "manhattan":
            continue
        #duplicated check
        key = name.lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, _stats(len(parks_data), len(deduped), duplicates)


# dedup_aed: AED 自动体外除颤器去重
# 去重键：Entity_Name|Address|Floor（实体+地址+楼层）
# 过滤：Borough == "manhattan"
# 返回：(去重后数据, 统计字典)
def dedup_aed(aed_data):
    seen, deduped, duplicates = set(), [], 0
    for row in aed_data:
        name = (row.get("Entity_Name") or "").strip()
        address = (row.get("Address") or "").strip()
        floor = (row.get("Floor") or "").strip()

        if not name or (row.get("Borough") or "").strip().lower() != "manhattan":
            continue
        key = f"{name.lower()}|{address.lower()}|{floor.lower()}"

        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, _stats(len(aed_data), len(deduped), duplicates)


# dedup_healthcare: 医疗设施跨源去重（NYS + OSM）
# 去重策略：NYS 优先 + OSM GPS 匹配（<30 米）
# 输入：osm_features (GeoJSON), nys_data (CSV)
# 返回：(nys_deduped, osm_deduped, stats_dict)
def dedup_healthcare(osm_features, nys_data):
    nys_deduped = [] # 存储去重后的 NYS 数据
    for row in nys_data:
        if (row.get("Facility County") or "").strip() != "New York":
            continue
        name = (row.get("Facility Name") or "").strip()
        try:
            lat = float(row.get("Facility Latitude", ""))
            lng = float(row.get("Facility Longitude", ""))
        except (ValueError, TypeError, KeyError):
            continue
        if name and is_manhattan(lat, lng):
            nys_deduped.append(row)

    nys_coords = [
        (
            float(row["Facility Latitude"]),
            float(row["Facility Longitude"]),
        )
        for row in nys_deduped
    ] # 提前提取 NYS 的经纬度坐标列表，避免在 OSM 循环中重复计算
    osm_deduped, matched = [], 0  # 存储去重后的 OSM 数据和 GPS 匹配计数
    for feature in osm_features:
        coords = feature.get("geometry", {}).get("coordinates", [])
        #check GPS  and borough
        if len(coords) < 2:
            continue
        lng, lat = coords[0], coords[1]
        if not is_manhattan(lat, lng):
            continue
        # 检查 OSM 记录是否在任何 NYS 记录的 30 米范围内，如果是则认为是重复并跳过，否则保留
        if any(
            ((lat - nys_lat) ** 2 + (lng - nys_lng) ** 2) ** 0.5 * 111000 < 30 for nys_lat, nys_lng in nys_coords):
            matched += 1
            continue
        osm_deduped.append(feature) # 只有当 OSM 记录没有 GPS 匹配到任何 NYS 记录时才保留

    stats = {
        "nys": _stats(len(nys_data), len(nys_deduped), 0),
        "osm": {
            **_stats(len(osm_features), len(osm_deduped), matched),
            "gps_matches": matched,
        },
    }
    return nys_deduped, osm_deduped, stats


# dedup_ramps: 行人坡道去重
# 去重键：RampID（坡道唯一标识）
# 过滤：Borough == "1"（曼哈顿行政区代码）
# 返回：(去重后数据, 统计字典)
def dedup_ramps(ramps_data):
    seen, deduped, duplicates = set(), [], 0
    for row in ramps_data:
        if (row.get("Borough") or "").strip() != "1":
            continue
        ramp_id = (row.get("RampID") or "").strip()
        if not ramp_id:
            continue
        if ramp_id in seen:
            duplicates += 1
            continue
        seen.add(ramp_id)
        deduped.append(row)
    return deduped, _stats(len(ramps_data), len(deduped), duplicates)
