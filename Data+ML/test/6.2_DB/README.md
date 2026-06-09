# ClearPath Database Build Notebook Documentation

**File**: `database_build.ipynb`
**Date**: 2026-06-05
**Scope**: Manhattan region data
**Total Cells**: 51

---

## 1. Notebook Structure

```
Part 1:  Data Source Validation       [Cell 0-3]
Part 2:  Schema Validation            [Cell 4-5]
Part 3:  Data Count Comparison        [Cell 6-8]
Part 4:  Data Quality Check           [Cell 9-10]
Part 5:  ETL Data Import              [Cell 11-24]
Part 6:  Import Validation            [Cell 25-27]
Part 7:  Schema Update (API)          [Cell 28-30]
Part 8:  Table Structure Validation   [Cell 31-32]
Part 10: Backend API Alignment        [Cell 33-35]
Part 11: Table Completion Validation  [Cell 36-37]
Part 12: Fix Plan Execution           [Cell 38-40]
Part 13: Final Verification           [Cell 41-43]
Part 14: Weather ETL                  [Cell 44-46]
Part 15: Venue Language ETL           [Cell 47-50]
```

---

## 2. Cell Details

### Cell [0] - Title
- **Type**: Markdown
- **Function**: Notebook title and description

### Cell [1] - Initialization
- **Type**: Code
- **Function**: Import libraries, config, define utility functions
- **Content**:
  - Imports: csv, json, re, hashlib, datetime, pymysql
  - Config: MySQL connection, Manhattan BBOX, NYC BBOX
  - Utils: `is_manhattan()`, `source_hash()`, `gen_vid()`, `get_conn()`
- **Execution**: ✅ Must run first

### Cell [3] - Data Source Validation
- **Type**: Code
- **Function**: Check if data source files exist
- **Content**: Read `clearpath_sources.json`, validate 6 local files
- **Output**: Row count/feature count per file

### Cell [5] - Schema Validation
- **Type**: Code
- **Function**: Validate SQL Schema file structure
- **Content**: Check 10 tables match expected structure
- **Output**: Table count, excluded terms

### Cell [8] - Data Count Comparison
- **Type**: Code
- **Function**: Compare Manhattan data counts
- **Content**: Expected vs Actual for 6 data sources
- **Output**: Count and difference percentage per source

### Cell [10] - Data Quality Check
- **Type**: Code
- **Function**: Record-level field completeness analysis
- **Content**:
  - Step 1: Field completeness for all 6 data sources
  - Step 2: Identify sources with quality issues
  - Step 3: LASS venue_language pre-check
- **Output**: Coordinate/name completeness percentage per source

### Cell [12] - ETL Utility Functions
- **Type**: Code
- **Function**: Define ETL utility and dedup preprocessing functions
- **Content**:
  - MySQL connection test
  - Utils: `check_row()`, `validate_coords()`, `dedup_check()`, `fill_missing()`, `log_import()`
  - Dedup: `dedup_restrooms()`, `dedup_parks()`, `dedup_aed()`, `dedup_healthcare()`, `dedup_ramps()`
- **Execution**: ✅ Required before ETL

### Cell [14] - Schema Rebuild
- **Type**: Code
- **Function**: Drop all tables and rebuild Schema
- **Content**:
  - DROP TABLE IF EXISTS (13 tables)
  - Re-execute `001_clearpath_schema.sql`
- **Output**: "Schema rebuilt: all tables dropped and recreated"
- **Execution**: ⚠️ Dangerous - will clear all data

### Cell [16] - Restrooms ETL
- **Type**: Code
- **Function**: Import NYC Restrooms + Parks Toilets
- **Content**:
  - Phase 1: `dedup_restrooms()` + `dedup_parks()` preprocessing
  - Phase 2: `etl_restrooms()` import to venues + restroom_profiles + venue_source_links
- **Output**: imported=476, skipped=1206

### Cell [19] - AED ETL
- **Type**: Code
- **Function**: Import AED Inventory
- **Content**:
  - Phase 1: `dedup_aed()` preprocessing
  - Phase 2: `etl_aed()` import to venues + emergency_assets + venue_source_links
- **Output**: imported=1781, skipped=...

### Cell [22] - Healthcare ETL
- **Type**: Code
- **Function**: Import OSM + NYS Health (merged)
- **Content**:
  - Phase 1: `dedup_healthcare()` preprocessing (NYS priority + OSM GPS matching)
  - Phase 2: `etl_healthcare()` import to venues + healthcare_profiles + venue_source_links
- **Output**: imported=1317, skipped=84

### Cell [24] - Ramps ETL
- **Type**: Code
- **Function**: Import Pedestrian Ramps
- **Content**:
  - Phase 1: `dedup_ramps()` preprocessing
  - Phase 2: `etl_ramps()` import to pedestrian_ramps (batch insert)
- **Output**: imported=23625, skipped=194054

### Cell [27] - Import Validation
- **Type**: Code
- **Function**: Validate data counts after import
- **Content**: Check 8 tables row counts + data source distribution
- **Output**: Row count statistics per table

### Cell [29-30] - Schema Update (API)
- **Type**: Code
- **Function**: Create new tables, add new fields
- **Content**:
  - Create: venue_accessibility, venue_language, venue_warnings
  - Modify: venues, user_reports, report_confirmations, busyness_scores
- **Output**: "Schema update applied"

### Cell [32] - Table Structure Validation
- **Type**: Code
- **Function**: Validate new tables and fields
- **Content**: SHOW TABLES + DESCRIBE
- **Output**: Table count, field list

### Cell [34-35] - Backend API Alignment
- **Type**: Code
- **Function**: Align with Backend API Schema
- **Content**: Add language_tags, accessible_status, weather_risk fields
- **Output**: "Backend API schema update applied"

### Cell [37] - Table Completion Validation
- **Type**: Code
- **Function**: Validate all tables and fields
- **Content**: SHOW TABLES + DESCRIBE venues + DESCRIBE user_reports
- **Output**: Table count, field list

### Cell [39] - Fix Plan Execution
- **Type**: Code
- **Function**: Execute fix_plan.md Schema optimization
- **Content**: Modify venue_type enum, add new fields, create new tables
- **Output**: "Fix plan applied successfully"

### Cell [41] - Final Verification
- **Type**: Code
- **Function**: Verify all tables and fields
- **Content**: SHOW TABLES + DESCRIBE
- **Output**: Table count, field list

### Cell [42] - Schema Sync
- **Type**: Code
- **Function**: Sync Schema file with database
- **Content**: Export CREATE TABLE statements from database
- **Output**: "Schema file updated"

### Cell [44] - Weather API Test
- **Type**: Code
- **Function**: Test NWS API connection
- **Content**: Test 5 API endpoints
- **Output**: "ALL PASS — API is ready for ETL"

### Cell [45] - Weather ETL
- **Type**: Code
- **Function**: Fetch weather data and cache
- **Content**:
  - Get current weather
  - Get 7-day forecast
  - Classify weather risk
  - Cache to external_context_cache
- **Output**: cached=2, failed=1

### Cell [47] - Venue Language ETL
- **Type**: Code
- **Function**: Import LASS language data to venue_language
- **Content**:
  - Parse LASS language strings
  - GPS match venues
  - Insert venue_language table
- **Output**: inserted=61, skipped=381

### Cell [49] - Venue Language Validation
- **Type**: Code
- **Function**: Validate venue_language import results
- **Content**: Language support level distribution, language tag frequency, sample records
- **Output**: Detailed import statistics

---

## 3. Execution Order

### Option 1: First-time Execution (Full Process)

```python
# Execute cells in order
Cell 1  → Initialization
Cell 3  → Data Source Validation
Cell 5  → Schema Validation
Cell 8  → Data Count Comparison
Cell 10 → Data Quality Check
Cell 12 → ETL Utility Functions
Cell 14 → Schema Rebuild (⚠️ Clears data)
Cell 16 → Restrooms ETL
Cell 22 → Healthcare ETL
Cell 19 → AED ETL
Cell 24 → Ramps ETL
Cell 27 → Import Validation
Cell 29 → Schema Update (API)
Cell 30 → Execute Schema Update
Cell 32 → Table Structure Validation
Cell 34 → Backend API Alignment
Cell 35 → Execute Backend API Alignment
Cell 37 → Table Completion Validation
Cell 39 → Fix Plan SQL
Cell 40 → Execute Fix Plan
Cell 41 → Final Verification
Cell 42 → Schema Sync
Cell 44 → Weather API Test
Cell 45 → Weather ETL
Cell 47 → Venue Language ETL
Cell 49 → Venue Language Validation
```

### Option 2: Re-execute ETL (Without Clearing Schema)

```python
# Skip Schema rebuild and Schema update
Cell 1  → Initialization
Cell 8  → Data Count Comparison
Cell 12 → ETL Utility Functions
Cell 16 → Restrooms ETL
Cell 22 → Healthcare ETL
Cell 19 → AED ETL
Cell 24 → Ramps ETL
Cell 27 → Import Validation
Cell 45 → Weather ETL
Cell 47 → Venue Language ETL
Cell 49 → Venue Language Validation
```

### Option 3: Validation Only

```python
# Only execute validation cells
Cell 1  → Initialization
Cell 27 → Import Validation
Cell 32 → Table Structure Validation
Cell 41 → Final Verification
Cell 49 → Venue Language Validation
```

---

## 4. Safety Classification

| Type | Cells | Re-execution | Description |
|------|-------|--------------|-------------|
| ✅ Safe | 1, 3, 5, 8, 10, 27, 32, 41, 49 | Completely safe | Read-only or validation operations |
| ✅ Safe | 16, 22, 19, 24, 45, 47 | Safe | INSERT ... ON DUPLICATE KEY UPDATE |
| ⚠️ Warning | 14 | ⚠️ Dangerous | DROP TABLE, will clear data |
| ❌ Unsafe | 29, 30, 34, 35, 39, 40 | ❌ Re-execution error | ALTER TABLE ADD COLUMN |

---

## 5. ETL Process Details

### Two-Phase ETL Design

```
Phase 1: Dedup Preprocessing (Cell 12)
    │
    ├─ dedup_restrooms()    → restrooms_deduped
    ├─ dedup_parks()        → parks_deduped
    ├─ dedup_aed()          → aed_deduped
    ├─ dedup_healthcare()   → nys_deduped, osm_deduped
    └─ dedup_ramps()        → ramps_deduped
    │
    ▼
Phase 2: Data Import (Cell 16, 19, 22, 24)
    │
    ├─ etl_restrooms()      → venues + restroom_profiles + venue_source_links
    ├─ etl_aed()            → venues + emergency_assets + venue_source_links
    ├─ etl_healthcare()     → venues + healthcare_profiles + venue_source_links
    └─ etl_ramps()          → pedestrian_ramps
```

### Dedup Rules

| Function | Dedup Key | Filter Condition | Output |
|----------|-----------|------------------|--------|
| `dedup_restrooms()` | `name.lower()` | Manhattan GPS | `restrooms_deduped` |
| `dedup_parks()` | `name.lower()` | Manhattan Borough | `parks_deduped` |
| `dedup_aed()` | `ename\|address` | Manhattan Borough | `aed_deduped` |
| `dedup_healthcare()` | GPS <30m (NYS priority) | Manhattan | `nys_deduped, osm_deduped` |
| `dedup_ramps()` | `ramp_id` | Borough=1 | `ramps_deduped` |

### Data Source Confidence

| Data Source | Confidence | Reason |
|-------------|------------|--------|
| NYS Health | 0.9 | Official government data |
| AED Inventory | 0.8 | Verified inventory |
| NYC Restrooms | 0.6 | City data, may be outdated |
| OSM Healthcare | 0.5 | Community-contributed data |
| Parks Toilets | 0.3 | No coordinate data |
| LASS Ratings | 0.4 | Government assessment data |

---

## 6. Database Table Structure

### Main Tables

| Table | Rows | Description |
|-------|------|-------------|
| venues | 3,564 | Unified POI table |
| venue_source_links | 3,564 | Data source tracking |

### Detail Tables

| Table | Rows | Description |
|-------|------|-------------|
| restroom_profiles | 476 | Restroom details |
| healthcare_profiles | 1,313 | Healthcare facility details |
| emergency_assets | 1,775 | AED device details |
| pedestrian_ramps | 23,625 | Pedestrian ramp data |
| venue_language | 61 | Multi-language support info |

### Runtime Tables (Empty in MVP)

| Table | Rows | Description |
|-------|------|-------------|
| user_reports | 0 | User-reported events |
| report_confirmations | 0 | User confirmations/votes |
| busyness_scores | 0 | ML busyness prediction |
| venue_accessibility | 0 | Accessibility info (pending) |
| venue_warnings | 0 | Warning info (runtime) |

### Cache Tables

| Table | Rows | Description |
|-------|------|-------------|
| external_context_cache | 2 | Weather API cache |

---

## 7. FAQ

### Q1: Schema rebuild error "Failed to open the referenced table 'venues'"

**Cause**: `venues` table was created last in SQL file, but other tables reference it via foreign keys.

**Solution**: Fixed `001_clearpath_schema.sql` to create `venues` table first.

### Q2: Will re-executing ETL insert duplicate data?

**No**. All ETL functions use `INSERT ... ON DUPLICATE KEY UPDATE`, re-execution updates existing records.

### Q3: How to re-execute ETL without clearing data?

Skip Cell [14] (Schema Rebuild), execute Cell [16], [19], [22], [24] directly.

### Q4: Why does venue_language table only have 61 records?

LASS data is government service center assessment data, only 442 Manhattan records, of which 61 can GPS-match with venues table.

### Q5: What is forecast_1h JSON format?

`forecast_1h` is JSON type storing 12-hour prediction array: `{"forecast": [h0, h1, ..., h11], "hours": ["08:00", "09:00", ...]}`. Use `JSON_EXTRACT(forecast_1h, '$.forecast[N]')` to get specific hour prediction.

---

## 8. Data Sources

| Data Source | File | Records | Manhattan | Purpose |
|-------------|------|---------|-----------|---------|
| NYC Public Restrooms | Public_Restrooms_20260526.csv | 1,066 | 358 | Restrooms |
| Parks Toilets | Directory_Of_Toilets_In_Public_Parks_20260526.csv | 616 | 129 | Park toilets |
| OSM Healthcare | POI_healtcare.geojson | 966 | 900 | Healthcare facilities |
| NYS Health Facility | Health_Facility_General_Information_20260526.csv | 5,963 | 454 | Healthcare facilities |
| AED Inventory | New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv | 7,373 | 3,393 | AED devices |
| Pedestrian Ramps | Pedestrian_Ramp_Locations_20260526.csv | 217,679 | 23,625 | Pedestrian ramps |
| LASS Ratings | Language_Access_Secret_Shopper_(LASS)_Ratings_20260526.csv | 1,231 | 442 | Multi-language support |
| Weather API | NWS API (weather.gov) | — | — | Weather data |

---

## 9. Notes

1. **Execution Order**: Follow recommended order to avoid dependency errors
2. **Schema Rebuild**: Cell [14] clears all data, use only for first-time execution or rebuild
3. **MySQL Connection**: Ensure MySQL Docker container is running
4. **Data Path**: Data files located at `/Users/alex/Documents/COMP47360-Research_Practicum/data_source/`
5. **Schema File**: `001_clearpath_schema.sql` has fixed table creation order
6. **forecast_1h**: Now JSON type, stores 12-hour prediction array, forecast_4h/8h removed
