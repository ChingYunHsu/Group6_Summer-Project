# ClearPath Database Build — Documentation

**File**: `database_build.ipynb`
**Date**: 2026-06-05
**Scope**: Manhattan area data
**Total Cells**: 50 (24 code cells)

---

## Changelog

### 2026-06-05: Structure and Redundancy Refactoring (Round 2)

Modified file: `Data+ML/test/6.2-6.5_DB/database_build.ipynb`

#### Structural Adjustments

- Notebook reduced from 51 to 50 cells, with 24 code cells.
- Removed legacy schema migration cells referencing obsolete variables.
- Schema changes consolidated into a single `MIGRATIONS` list executed by `apply_migrations()`.
- Each migration entry now contains a stable name, type, target table/column, and SQL — no dependency on cell numbering.
- `column_exists()` and `table_exists()` retained as single-copy preflight check helpers.

#### ETL and Error Handling

- Added unified transaction functions:
  - `etl_execute()`: Executes a single statement or a group of statements for one record.
  - `etl_executemany()`: Executes batch inserts.
  - `log_etl_error()`: Prints data source, record ID, exception type, and message.
- Restroom, AED, Healthcare, Ramp, Weather, and Venue Language ETL now use the unified transaction functions.
- Removed duplicate `commit()` / `rollback()` templates from write logic.
- Replaced bare `except:` with specific data parsing exceptions or `pymysql.MySQLError`.
- Migrations treat MySQL duplicate object error codes `1050` and `1060` as skippable; other SQL errors abort and report the migration name.

#### Configuration Changes

Project paths and database connection now support environment variables:

| Environment Variable | Default |
|----------------------|---------|
| `CLEARPATH_PROJECT_ROOT` | Auto-detect project root containing `Data+ML` from current directory |
| `CLEARPATH_DATA_ROOT` | `<PROJECT_ROOT>/../data_source` |
| `CLEARPATH_DB_HOST` | `127.0.0.1` |
| `CLEARPATH_DB_PORT` | `3306` |
| `CLEARPATH_DB_USER` | `clearpath_app` |
| `CLEARPATH_DB_PASSWORD` | Empty string |
| `CLEARPATH_DB_NAME` | `clearpath` |

Local execution example:

```bash
export CLEARPATH_DB_PASSWORD=clearpath_app
jupyter notebook Data+ML/test/6.2-6.5_DB/database_build.ipynb
```

#### Validation Results

- Notebook passes `nbformat` structural validation.
- All 50 cells pass JSON parsing; 24 code cells pass AST syntax validation.
- Pylint `undefined-variable` check scores `10.00/10`.
- Transaction simulation tests cover success commit, failure rollback, and record-level error logging.
- Migration simulation test: first pass applies 22 items; second pass skips 21 existing objects, re-runs only 1 column type normalization.
- Existing database read-only preflight: 21 detectable migrations already applied, 0 pending.
- All code cell execution counts and outputs cleared to avoid stale results.

#### Validation Limitations

Full `Run All` was not executed against the live `clearpath` database. The Schema rebuild cell contains `DROP TABLE` which deletes existing data; the current `clearpath_app` account only has `clearpath.*` privileges and cannot create an isolated test database. Full flow should be validated in an isolated test database or a backup-restore environment.

> **Note**: The per-cell descriptions below are based on the post-refactoring structure. When navigating, prefer section headings and function names over fixed cell numbers.

---

## 1. Notebook Structure Overview

```
Part 1:  Data Source Validation          [Cells 2-3]
Part 2:  Schema Validation              [Cells 4-5]
Part 3:  Data Volume Comparison         [Cells 6-8]
Part 4:  Data Quality Check             [Cells 9-10]
Part 5:  ETL Data Import                [Cells 11-22]
Part 6:  Import Verification            [Cells 23-25]
Part 7:  Schema Update (API alignment)  [Cells 26-27]
Part 8:  Updated Table Structure        [Cells 28-29]
Part 10: Backend API Schema Alignment   [Cells 30-31]
Part 11: Table Completeness Validation  [Cells 32-33]
Part 12: Fix Plan Execution (Migration) [Cells 34-37]
Part 13: Weather ETL                    [Cells 38-40]
Part 14: Venue Language ETL             [Cells 41-43]
Part 15: Final Verification             [Cells 44-47]
Part 16: Conclusion                     [Cells 48-49]
```

---

## 2. Detailed Cell Reference

### Cell [0] — Title (Markdown)
- **Content**: Notebook title, date, scope, directory overview.

### Cell [1] — Initialization
- **Type**: Code
- **Purpose**: Import libraries, load configuration, define utility functions.
- **Contents**:
  - Imports: csv, json, re, hashlib, datetime, os, decimal, pathlib, pymysql
  - Config: MySQL connection, Manhattan BBOX, NYC BBOX, county-borough mapping, OSM category map
  - Utility functions: `is_manhattan()`, `source_hash()`, `gen_vid()`, `get_conn()`, `safe_int()`, `safe_dec()`
  - Schema helpers: `column_exists()`, `table_exists()`
  - ETL helpers: `log_etl_error()`, `etl_execute()`, `etl_executemany()`
- **Execution**: Must run first.

### Cell [3] — Data Source Validation
- **Type**: Code
- **Purpose**: Check data source files exist and count records.
- **Contents**: Reads `clearpath_sources.json`, verifies 6 local files.
- **Output**: Row/feature count per file.

### Cell [5] — Schema Validation
- **Type**: Code
- **Purpose**: Validate SQL schema file structure.
- **Contents**: Checks 10 expected tables match the schema.
- **Output**: Table count, excluded terms.

### Cell [8] — Data Volume Comparison
- **Type**: Code
- **Purpose**: Compare Manhattan-filtered record counts.
- **Contents**: 6 data sources — Expected vs Actual.
- **Output**: Per-source counts and difference percentage.

### Cell [10] — Data Quality Check
- **Type**: Code
- **Purpose**: Record-level field completeness analysis.
- **Contents**:
  - Step 1: Field completeness for all 6 data sources
  - Step 2: Identify sources with quality issues
  - Step 3: LASS venue_language pre-check
- **Output**: Coordinate/name completeness percentages per source.

### Cell [12] — ETL Utility and Dedup Functions
- **Type**: Code
- **Purpose**: Define ETL utility functions and dedup preprocessing functions.
- **Contents**:
  - MySQL connection test
  - Utility functions: `check_row()`, `validate_coords()`, `dedup_check()`, `fill_missing()`, `log_import()`
  - Dedup functions: `dedup_restrooms()`, `dedup_parks()`, `dedup_aed()`, `dedup_healthcare()`, `dedup_ramps()`
- **Execution**: Must run before any ETL.

### Cell [14] — Schema Rebuild
- **Type**: Code
- **Purpose**: Drop all tables and recreate from SQL schema.
- **Contents**:
  - `DROP TABLE IF EXISTS` (13 tables)
  - Re-execute `001_clearpath_schema.sql`
- **Output**: "Schema rebuilt: all tables dropped and recreated"
- **Execution**: Destructive — clears all data.

### Cell [16] — Restrooms ETL
- **Type**: Code
- **Purpose**: Import NYC Restrooms + Parks Toilets.
- **Contents**:
  - Phase 1: `dedup_restrooms()` + `dedup_parks()` preprocessing
  - Phase 2: `etl_restrooms()` → venues + restroom_profiles + venue_source_links
- **Output**: imported=476, skipped=1206

### Cell [18] — AED ETL
- **Type**: Code
- **Purpose**: Import AED Inventory.
- **Contents**:
  - Phase 1: `dedup_aed()` preprocessing
  - Phase 2: `etl_aed()` → venues + emergency_assets + venue_source_links
- **Output**: imported=1775, skipped=0

### Cell [20] — Healthcare ETL
- **Type**: Code
- **Purpose**: Import OSM + NYS Health (merged).
- **Contents**:
  - Phase 1: `dedup_healthcare()` preprocessing (NYS priority + OSM GPS match)
  - Phase 2: `etl_healthcare()` → venues + healthcare_profiles + venue_source_links
- **Output**: imported=1228, skipped=0

### Cell [22] — Ramps ETL
- **Type**: Code
- **Purpose**: Import Pedestrian Ramps.
- **Contents**:
  - Phase 1: `dedup_ramps()` preprocessing
  - Phase 2: `etl_ramps()` → pedestrian_ramps (batch insert)
- **Output**: imported=23625, skipped=0

### Cell [25] — Import Verification
- **Type**: Code
- **Purpose**: Verify post-import row counts.
- **Contents**: Checks 8 tables + venue_type breakdown.
- **Output**: Per-table row counts.

### Cell [27] — Schema Update (Legacy)
- **Type**: Code
- **Purpose**: Redirect to consolidated MIGRATIONS section.

### Cell [29] — Updated Table Structure
- **Type**: Code
- **Purpose**: Verify new tables and columns exist.
- **Contents**: SHOW TABLES + DESCRIBE.

### Cell [31] — Backend API Schema (Legacy)
- **Type**: Code
- **Purpose**: Redirect to consolidated MIGRATIONS section.

### Cell [33] — Table Completeness Validation
- **Type**: Code
- **Purpose**: Verify venues, user_reports columns and new tables.
- **Contents**: DESCRIBE venues, DESCRIBE user_reports, DESCRIBE new tables.

### Cell [35] — Migration Definitions
- **Type**: Code
- **Purpose**: Define `MIGRATIONS` list — single source of truth for all schema changes.
- **Contents**: 22 named migration entries with stable names, kind, target table/column, SQL.
- **Output**: "Migrations loaded: 22"

### Cell [37] — Migration Execution
- **Type**: Code
- **Purpose**: Execute migrations with preflight checks and error classification.
- **Contents**: `migration_is_applied()`, `apply_migrations()`, DUPLICATE_OBJECT_CODES handling.
- **Output**: APPLIED/SKIP per migration, final applied/skipped counts.

### Cell [39] — Weather API Test
- **Type**: Code
- **Purpose**: Test NWS API connectivity.
- **Contents**: Tests 5 endpoints (base, points, forecast, stations, observation).
- **Output**: "ALL PASS — API is ready for ETL"

### Cell [40] — Weather ETL
- **Type**: Code
- **Purpose**: Fetch current weather and cache.
- **Contents**:
  - `fetch_current_weather()` from NWS station
  - `classify_weather_risk()` → low/medium/high
  - Cache to external_context_cache
- **Output**: cached=1, failed=0

### Cell [42] — Venue Language ETL
- **Type**: Code
- **Purpose**: Import LASS language data into venue_language.
- **Contents**:
  - `parse_lass_languages()` → ISO codes
  - `find_nearest_venue()` → SQL Haversine GPS match
  - `etl_venue_language()` → venue_language table
- **Output**: inserted=61, skipped=381

### Cell [45] — Final Verification
- **Type**: Code
- **Purpose**: Verify all tables and columns after all ETL.
- **Contents**: SHOW TABLES + DESCRIBE for venues, venue_accessibility, venue_language, venue_warnings.

### Cell [46] — Schema Sync
- **Type**: Code
- **Purpose**: Sync `001_clearpath_schema.sql` from live database structure.
- **Contents**: SHOW CREATE TABLE for all 13 tables, writes to schema file.

### Cell [47] — Venue Language Verification
- **Type**: Code
- **Purpose**: Verify venue_language import results.
- **Contents**: Language support level breakdown, language tag frequency, sample records.

### Cell [48] — Final Database Verification
- **Type**: Code
- **Purpose**: Table row counts, venues vs venue_source_links consistency check, duplicate venue_id check.

---

## 3. Execution Order

### Option 1: Full Run (First-time)

```python
# Execute cells in order:
Cell 1   → Initialization
Cell 3   → Data Source Validation
Cell 5   → Schema Validation
Cell 8   → Data Volume Comparison
Cell 10  → Data Quality Check
Cell 12  → ETL Utility Functions
Cell 14  → Schema Rebuild (⚠️ destructive)
Cell 16  → Restrooms ETL
Cell 18  → AED ETL
Cell 20  → Healthcare ETL
Cell 22  → Ramps ETL
Cell 25  → Import Verification
Cell 29  → Updated Table Structure
Cell 33  → Table Completeness Validation
Cell 35  → Define MIGRATIONS
Cell 37  → Execute Schema Migration
Cell 39  → Weather API Test
Cell 40  → Weather ETL
Cell 42  → Venue Language ETL
Cell 45  → Final Table Structure Verification
Cell 46  → Schema Sync
Cell 47  → Venue Language Final Verification
Cell 48  → Final Database Verification
```

### Option 2: Re-run ETL (Without Schema Rebuild)

```python
# Skip Schema rebuild and migration cells:
Cell 1   → Initialization
Cell 8   → Data Volume Comparison
Cell 12  → ETL Utility Functions
Cell 16  → Restrooms ETL
Cell 18  → AED ETL
Cell 20  → Healthcare ETL
Cell 22  → Ramps ETL
Cell 25  → Import Verification
Cell 40  → Weather ETL
Cell 42  → Venue Language ETL
Cell 45  → Final Table Structure Verification
Cell 47  → Venue Language Final Verification
```

### Option 3: Verify Only

```python
# Read-only verification cells only:
Cell 1   → Initialization
Cell 25  → Import Verification
Cell 29  → Updated Table Structure
Cell 33  → Table Completeness Validation
Cell 45  → Final Table Structure Verification
Cell 47  → Venue Language Final Verification
Cell 48  → Final Database Verification
```

---

## 4. Safety Classification

| Type | Cells | Re-runnable | Description |
|------|-------|-------------|-------------|
| ✅ Safe | 1, 3, 5, 8, 10, 25, 29, 33, 39, 45, 47, 48 | Fully safe | Read-only or verification |
| ✅ Safe | 16, 18, 20, 22, 40, 42 | Safe | INSERT ... ON DUPLICATE KEY UPDATE |
| ⚠️ Destructive | 14 | ⚠️ Dangerous | DROP TABLE — clears all data |
| ❌ Not idempotent | 35, 37 | ❌ Errors on re-run | ALTER TABLE ADD COLUMN (preflight checks mitigate) |

---

## 5. ETL Pipeline Design

### Two-Phase ETL

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
Phase 2: Data Import (Cells 16, 18, 20, 22, 40, 42)
    │
    ├─ etl_restrooms()      → venues + restroom_profiles + venue_source_links
    ├─ etl_aed()            → venues + emergency_assets + venue_source_links
    ├─ etl_healthcare()     → venues + healthcare_profiles + venue_source_links
    ├─ etl_ramps()          → pedestrian_ramps
    ├─ etl_weather()        → external_context_cache
    └─ etl_venue_language() → venue_language
```

### Dedup Rules

| Function | Dedup Key | Filter | Output |
|----------|-----------|--------|--------|
| `dedup_restrooms()` | `name.lower()` | Manhattan GPS | `restrooms_deduped` |
| `dedup_parks()` | `name.lower()` | Manhattan Borough | `parks_deduped` |
| `dedup_aed()` | `ename|address|floor` | Manhattan Borough | `aed_deduped` |
| `dedup_healthcare()` | GPS <30m (NYS priority) | Manhattan | `nys_deduped, osm_deduped` |
| `dedup_ramps()` | `ramp_id` | Borough=1 | `ramps_deduped` |

### Data Source Confidence Levels

| Source | Confidence | Reason |
|--------|------------|--------|
| NYS Health | 0.9 | Official government data |
| AED Inventory | 0.8 | Verified inventory |
| NYC Restrooms | 0.6 | City data, may be outdated |
| OSM Healthcare | 0.5 | Community-sourced |
| Parks Toilets | 0.3 | No coordinates available |
| LASS Ratings | 0.4 | Government evaluation data |

---

## 6. Database Table Structure

### Core Tables

| Table | Rows | Description |
|-------|------|-------------|
| venues | 3,479 | Unified POI table |
| venue_source_links | 3,479 | Data source tracking (1:1 with venues) |

### Detail Tables

| Table | Rows | Description |
|-------|------|-------------|
| restroom_profiles | 476 | Restroom details |
| healthcare_profiles | 1,228 | Healthcare facility details |
| emergency_assets | 3,279 | AED device details |
| pedestrian_ramps | 23,625 | Pedestrian ramp data |
| venue_language | 63 | Multi-language support info |

### Runtime Tables (empty at MVP stage)

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
| external_context_cache | 1 | Weather API cache |

---

## 7. FAQ

### Q1: Schema rebuild error "Failed to open the referenced table 'venues'"

**Cause**: `venues` table was created last in the SQL file, but other tables reference it via foreign keys.

**Fix**: Already fixed in `001_clearpath_schema.sql` — `venues` is now created first.

### Q2: Does re-running ETL insert duplicate data?

**No.** All ETL functions use `INSERT ... ON DUPLICATE KEY UPDATE`. Re-running updates existing records.

### Q3: How to re-run ETL without clearing data?

Skip Cell [14] (Schema Rebuild) and execute the ETL cells directly (Cells 16, 18, 20, 22, 40, 42).

### Q4: Why does venue_language only have ~63 records?

LASS data covers government service centers — only 442 Manhattan records exist, and ~63 match existing venues within the 100m GPS threshold.

---

## 8. Data Source Reference

| Source | File | Records | Manhattan | Purpose |
|--------|------|---------|-----------|---------|
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

1. **Execution order**: Follow the recommended order to avoid dependency errors.
2. **Schema rebuild**: Cell [14] clears all data — use only on first run or when rebuilding.
3. **MySQL connection**: Ensure the MySQL Docker container is running.
4. **Data paths**: Data files are located at `data_source/` relative to the project root.
5. **Schema file**: `001_clearpath_schema.sql` has been fixed for correct table creation order.
6. **Cell numbering**: Section headings and function names are more reliable than cell numbers for navigation.
