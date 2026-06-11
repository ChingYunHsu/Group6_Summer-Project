from .validation import is_manhattan


def _stats(input_count, unique_count, duplicate_count):
    return {
        "input": input_count,
        "unique": unique_count,
        "duplicates": duplicate_count,
        "filtered": input_count - unique_count - duplicate_count,
    }


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
        key = name.lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, _stats(len(restrooms_data), len(deduped), duplicates)


def dedup_parks(parks_data):
    seen, deduped, duplicates = set(), [], 0
    for row in parks_data:
        name = (row.get("Name") or "").strip()
        borough = (row.get("Borough") or "").strip()
        if not name or borough.lower() != "manhattan":
            continue
        key = name.lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, _stats(len(parks_data), len(deduped), duplicates)


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


def dedup_healthcare(osm_features, nys_data):
    nys_deduped = []
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
    ]
    osm_deduped, matched = [], 0
    for feature in osm_features:
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        lng, lat = coords[0], coords[1]
        if not is_manhattan(lat, lng):
            continue
        if any(
            ((lat - nys_lat) ** 2 + (lng - nys_lng) ** 2) ** 0.5 * 111000 < 30
            for nys_lat, nys_lng in nys_coords
        ):
            matched += 1
            continue
        osm_deduped.append(feature)

    stats = {
        "nys": _stats(len(nys_data), len(nys_deduped), 0),
        "osm": {
            **_stats(len(osm_features), len(osm_deduped), matched),
            "gps_matches": matched,
        },
    }
    return nys_deduped, osm_deduped, stats


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
