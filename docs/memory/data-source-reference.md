# Data Source Reference

来源：`Data+ML/test/6.2-6.5_DB/README.md` §8

## 数据源清单

| Source | File | Total Records | Manhattan | Purpose |
|--------|------|---------------|-----------|---------|
| NYC Public Restrooms | Public_Restrooms_20260526.csv | 1,066 | 358 | Restrooms |
| Parks Toilets | Directory_Of_Toilets_In_Public_Parks_20260526.csv | 616 | 129 | Park toilets |
| OSM Healthcare | POI_healtcare.geojson | 966 | 900 | Healthcare facilities |
| NYS Health Facility | Health_Facility_General_Information_20260526.csv | 5,963 | 454 | Healthcare facilities |
| AED Inventory | New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv | 7,373 | 3,393 | AED devices |
| Pedestrian Ramps | Pedestrian_Ramp_Locations_20260526.csv | 217,679 | 23,625 | Pedestrian ramps |
| LASS Ratings | Language_Access_Secret_Shopper_(LASS)_Ratings_20260526.csv | 1,231 | 442 | Multi-language support |
| Weather API | NWS API (weather.gov) | — | — | Weather data |

## Manhattan 过滤方法

| Data Source | Filter Method | Code | Notes |
|-------------|:-------------:|------|-------|
| Public Restrooms | GPS bounding box | `is_manhattan(lat, lng)` | lat 40.700~40.880, lng -74.020~-73.907 |
| Parks Toilets | Borough field | `Borough == 'manhattan'` | No coordinates in source |
| OSM Healthcare | GPS bounding box | `is_manhattan(lat, lng)` | From GeoJSON `geometry.coordinates` |
| NYS Health Facility | County field | `Facility County == 'New York'` | New York County = Manhattan |
| AED Inventory | Borough field | `Borough == 'manhattan'` | Borough column from source |
| Pedestrian Ramps | Borough code | `Borough == '1'` | Manhattan Borough code is `'1'` |

## ETL 后行数（2026-06-05 运行结果）

| Table | Rows | Description |
|-------|------|-------------|
| venues | 3,479 | Main venue table (with district zoning) |
| venue_source_links | 3,479 | Data source tracking |
| restroom_profiles | 476 | NYC + Parks restrooms |
| healthcare_profiles | 1,228 | NYS + OSM healthcare |
| emergency_assets | 3,279 | AED (deduped) |
| pedestrian_ramps | 23,625 | Manhattan ramps (with district zoning) |
| external_context_cache | 1 | Current weather + risk_level |
| venue_language | 63 | LASS language support data |
| user_reports | 0 | Runtime (empty) |
| report_confirmations | 0 | Runtime (empty) |
| busyness_scores | 0 | ML model (empty) |
| venue_accessibility | 0 | Pending (empty) |
| venue_warnings | 0 | Runtime (empty) |

## Filter → ETL 对应关系

```
Part 3 (Volume Comparison)          Part 5 (ETL)
─────────────────────────          ─────────────
NYC Restrooms (358)     ──┐
                          ├──→ etl_restrooms()  (Cell 16)
Parks Toilets (129)     ──┘

OSM Healthcare (900)    ──┐
                          ├──→ etl_healthcare() (Cell 20)
NYS Health (454)        ──┘

AED Inventory (3,393)   ────→ etl_aed()        (Cell 18)

Pedestrian Ramps (23,625) ──→ etl_ramps()      (Cell 22)

Weather API             ────→ etl_weather()     (Cell 40)
LASS Ratings (442)      ────→ etl_venue_language() (Cell 42)
```
