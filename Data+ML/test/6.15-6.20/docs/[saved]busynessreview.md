# busyness_ingestion.py Feature Implementation Progress

> Initial review: 2026-06-15  
> Last updated: 2026-06-15  
> Source file: `Data+ML/test/6.15-5.20/src/busyness_ingestion.py`  
> Test file: `Data+ML/test/6.15-5.20/tests/test_busyness_ingestion.py`

## Implementation Progress

### Completed

| Date | Item | Status |
|------|------|------|
| 06-15 | `busyness_ingestion.py` ETL pipeline implementation | ✅ |
| 06-15 | All 44 unit tests passing | ✅ |
| 06-15 | 5 legacy interface tests fixed (`cursor.execute` -> `executemany.call_args`) | ✅ |
| 06-15 | `test_successful_insert` rows validation logic fixed (result==2 -> result==3) | ✅ |
| 06-15 | Stale xfail removed from `test_dropna_on_avg_vol_hh` | ✅ |
| 06-15 | `pytest-timeout` config written to pyproject.toml (`timeout = 30`) | ✅ |
| 06-15 | `dqr_cleaning_pipeline.ipynb` Part 8 - Busyness data overview | ✅ |
| 06-15 | notebook cell 19 - data scale and training target description | ✅ |
| 06-15 | notebook cell 23 - 12h forecast curve chart (deduplicated by district, multi-color) | ✅ |
| 06-15 | notebook cell 24 - forecast_1h JSON expansion preview | ✅ |
| 06-15 | Files organized into `6.15-5.20/` directory | ✅ |

### Pending

Null

### Current Data Status

```text
busyness_scores: 114,720 rows (4,780 venues × 24h)
model_version: nyc_traffic_baseline_v1
Granularity: district level (all venues in the same district share the same score)
Coverage: 28/28 segments -> 4,714 venues across 4 districts
DQ score: 96.3/100 (Excellent)
```

### Key Fix Log

#### test_busyness_ingestion.py - 5 legacy interface tests (2026-06-15)

Implementation changed to `cursor.executemany(sql, rows)`, but tests still assert `cursor.execute`. Fixes:

| Test | Before | After |
|------|--------|--------|
| `test_successful_insert` | `execute.assert_called()`, result==2 | `executemany.assert_called_once()`, result==3, len(rows)==3 |
| `test_default_model_version` | `execute.assert_called()` | `executemany.assert_called_once()` |
| `test_custom_model_version` | `call_args[0][1][-2]` | `rows[0][6]` (executemany row tuple) |
| `test_forecast_json_in_insert` | `call_args[0][1][3]` | `rows[0][3]` |
| `test_features_snapshot_default` | `call_args[0][1][-1]` | `rows[0][-1]` |

#### dqr_cleaning_pipeline.ipynb - Part 8 update (2026-06-15)

- Cell 19: Added data scale description (Cartesian product of all venues × 24h) and training target (predict 12h continuous values)
- Cell 23: Changed to deduplicate by district and pick representative venue, 4 colors for differentiation, legend moved to the right
- Cell 24: forecast_1h JSON expanded, showing 12h forecast trajectory

## Data Flow Overview

```
NYC SODA API (traffic volume)
  │
  ▼
fetch_busyness_data()     ← API fetch + EPSG2263->WGS84 + Manhattan filter
  │
  ▼
aggregate_by_segment()    ← group by segment+hour, recompute score
  │
  ▼
map_segments_to_venues()  ← haversine distance match -> venue_id + district
  │
  ▼
build_forecast_1h()       ← 12h rolling forecast window
  │
  ▼
insert_busyness_scores()  ← executemany write to MySQL busyness_scores table
  │
  ▼
Flask API (src/api/venues.py) ← read busyness_scores -> return to frontend
  │
  ▼
React frontend (frontend/web/src/data/venues.js) ← display busyness_level + percent + forecast
```

## Test Suite Structure (44 tests)

### 1. Score Classification - TestClassifyScore (4 tests)

**Source function**: `classify_score(score)` -> classifies into four-level labels

| Score range | Return value | Meaning |
|---------|--------|------|
| 0 | `no_data` | No data |
| 1-54 | `quiet` | Quiet (late night/early morning) |
| 55-69 | `moderate` | Moderate (off-peak) |
| 70+ | `busy` | Busy (peak) |

**Related**: `aggregate_by_segment` and `insert_busyness_scores` call this function internally to compute `busyness_level`. The frontend `src/api/venues.py`'s `_level_to_color` consumes these labels (quiet->green, moderate->yellow, busy->red).

---

### 2. GPS Coordinate Conversion - TestWktParsing + TestEpsgConversion (3 tests)

**Source functions**:
- `parse_wkt_point(wkt)` - extract x/y coordinates from WKT POINT string
- `epsg2263_to_wgs84(x, y)` - NYC State Plane (EPSG:2263) -> WGS84 lat/lng

**Related**: The traffic data fetched by `fetch_busyness_data` from the SODA API uses EPSG:2263 projected coordinates, which must be converted to lat/lng to do distance matching with venues' GPS coordinates.

---

### 3. Distance Calculation - TestHaversine (2 tests)

**Source function**: `haversine_m(lat1, lng1, lat2, lng2)` -> distance between two points (meters)

**Related**: `map_segments_to_venues` uses this function to determine whether a traffic segment is within a venue's 50m coverage range.

---

### 4. Segment Aggregation - TestAggregateBySegment (4 tests)

**Source function**: `aggregate_by_segment(df)` -> group by segment+hour and recompute score

Key behaviors:
- **Preserve GPS**: `lat`/`lng` columns not lost
- **Recompute score**: `score = avg_vol / peak_vol × 100`, does not use input value
- **Recompute level**: reclassify based on new score, ignoring input `busyness_level`

**Related**: The second step of `run_pipeline`, aggregates the raw data from `fetch_busyness_data` and passes it to `map_segments_to_venues`.

---

### 5. Venue Matching - TestMapSegmentsToVenues (7 tests)

**Source function**: `map_segments_to_venues(conn, segment_hourly)` -> map segments to nearby venues

Test coverage:
- Empty input -> empty result
- Basic match - segment GPS same as venue
- Too far (~5km) -> no match
- Same district aggregation - multiple venues in same district get same score
- Empty venues table -> empty result
- Multiple segments multiple districts -> matched separately
- Output column validation - result only contains `venue_id, district, hour, score, busyness_level`

**Related**: Reads all venues from the MySQL `venues` table and uses haversine distance for nearest matching.

---

### 6. Forecast Generation - TestBuildForecast1h (6 tests)

**Source function**: `build_forecast_1h(scores_df, target_hour)` -> 12-hour rolling forecast window

Key behaviors:
- **Fixed 12 entries**: output always 12 entries
- **Cross midnight**: target_hour=22 -> output hour 22, 23, 0, 1, ..., 9
- **Missing hours filled with no_data**: `percent=0, level='no_data'`
- **Structure validation**: each entry contains `offset_hours`, `percent`, `level`

**Related**: `insert_busyness_scores` calls this function inline when building rows, serializing the forecast JSON into the `busyness_scores.forecast_1h` column. The frontend `src/api/venues.py`'s `get_venue_busyness_forecast` reads this JSON and returns it to the user.

---

### 7. DB Write - TestInsertBusynessScores (6 tests)

**Source function**: `insert_busyness_scores(conn, venue_scores_df, ...)` -> executemany batch write

Key behaviors:
- Empty DataFrame -> returns 0
- Uses `cursor.executemany(sql, rows)` for batch insert
- `cursor.rowcount` returns affected row count
- Default `model_version='nyc_traffic_baseline_v1'`
- `features_snapshot` default format `nyc_traffic_{year}_manhattan`

**Related**: The written `busyness_scores` table is consumed by the backend API:
- `src/api/venues.py:80` `get_venue_busyness` - reads `score, level` and returns current busyness
- `src/api/venues.py:141` `get_venue_busyness_forecast` - reads `forecast_1h` and returns 12-hour forecast

---

### 8. API Data Fetch - TestFetchBusynessData (7 tests)

**Source function**: `fetch_busyness_data(year, boro)` -> fetch from NYC SODA API and convert coordinates

Test coverage:
- Empty API response -> empty DataFrame
- Manhattan boundary filter - only keep segments within Manhattan
- busyness_level derived from score
- API parameter validation - `$where` contains year and boro
- dropna handling - rows where `hh` is non-numeric are dropped
- Output column completeness

**Related**: The first step of the pipeline. Data source is the NYC TLC traffic volume API.

---

### 9. Pipeline Orchestration - TestRunPipeline (5 tests)

**Source function**: `run_pipeline(year, dry_run, model_version)` -> orchestrates the entire ETL flow

Test coverage:
- Empty traffic data -> early abort
- Empty aggregation result -> early abort
- dry_run mode -> does not call insert
- Normal run -> calls insert and passes model_version
- Empty venue mapping -> aborts and closes connection

---

## Related Files

| File | Role |
|------|------|
| `Data+ML/test/6.8-6.12_DB/dqr/busyness_ingestion.py` | ETL core implementation |
| `Data+ML/test/6.8-6.12_DB/tests/test_busyness_ingestion.py` | 44 unit tests |
| `src/api/venues.py` | Flask API, consumes busyness_scores table |
| `frontend/web/src/data/venues.js` | Frontend venue data |
| `pyproject.toml` | Project config, includes pytest timeout setting |
