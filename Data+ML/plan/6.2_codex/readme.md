# ClearPath 6.2 Codex Work Log

## 1. Directory Boundaries

`ml_training/plan/6.2_codex` is a Codex-specific workspace, used to store Codex's organization of the database schema, data source scope, process records, and follow-up tasks.

Boundary conventions:

- `ml_training/plan/6.2_codex`: Codex work records and Codex schema copy.
- `ml_training/plan/6.2_CC`: CC / Claude-style reference documents, not to be modified by Codex.
- `ml_training/plan/6.2`: if it exists, it should be treated as another agent / Claude task area, not to be modified by Codex.
- The Docker initialization main schema currently uses the Codex scheme: `docker/mysql/init/001_clearpath_schema.sql`.

## 2. Objectives for This Round

The goal of this round is to establish the database and data foundation for the ClearPath Sprint 1 Data Analysis & ML Lead work:

- Clearly retain the data source scope.
- Design a reasonable number of MySQL 8.4 tables.
- Merge similar data sources to avoid one-table-per-source.
- Retain data lineage tracking.
- Provide a structural foundation for subsequent ETL, API, and ML busyness prediction.
- Generate process documentation and a follow-up task list.

## 3. Confirmed Data Source Scope

Use only 9 sources:

| Type | Source | Role |
| --- | --- | --- |
| Internal | User Reports Database | Real-time reports and confirmations |
| Toilet | NYC Public Restrooms `i7jb-7jku` | Primary restroom data |
| Toilet | Directory of Toilets in Public Parks `hjae-yuav` | Park restroom supplement |
| Healthcare | OpenStreetMap / Overpass POI | Broad-coverage medical POI |
| Healthcare | NYS Health Facility General Information `vn5v-hh5r` | Official healthcare facility verification |
| Healthcare | AED Inventory `2er2-jqsx` | AED / emergency asset |
| Accessibility | Pedestrian Ramp Locations `ufzp-rrqu` | Wheelchair routing infrastructure |
| Traffic | Google Map API | Routing / traffic context cache |
| Weather | Weather / NYC Urban Heat Portal | Weather / heat risk context cache |

Explicitly excluded:

- `POI_accessibility.geojson`
- HRSA
- CityMD
- Google Places
- MTA outages / stations
- Taxi data
- Traffic volume counts
- Language datasets
- Any data source not listed among the 9 sources

## 4. Completed Tasks

### 4.1 Database schema

Designed and landed a MySQL 8.4 / 10-table Codex schema:

1. `venues`
2. `venue_source_links`
3. `restroom_profiles`
4. `healthcare_profiles`
5. `emergency_assets`
6. `pedestrian_ramps`
7. `user_reports`
8. `report_confirmations`
9. `busyness_scores`
10. `external_context_cache`

Corresponding files:

- `docker/mysql/init/001_clearpath_schema.sql`
- `ml_training/plan/6.2_codex/001_clearpath_schema.sql`

The two schema copies should remain completely identical.

### 4.2 Data source manifest and validation

Added:

- `backend/database/clearpath_sources.json`
- `backend/database/validate_sources.py`
- `backend/database/README.md`

Purpose:

- Record the 9 retained sources.
- Record deprecated local files.
- Verify that 6 local data files exist.
- Prevent deprecated sources from being mistakenly added to the MVP database path.

### 4.3 Database architecture documentation

Extended:

- `ml_training/plan/database.md`
- `ml_training/plan/6.2_codex/database.md`

The content absorbs the CC document structure but keeps the Codex 9-source + 10-table scheme. New highlights:

- Requirements origin and current constraints
- Overall architecture
- Cloud MySQL table layering
- ER diagram
- Data merge rules
- Field mapping summary
- Data quality issues
- Index strategy
- API and database mapping
- ETL Flow
- Non-functional requirements
- Acceptance criteria

### 4.4 Process documentation

Written:

- `ml_training/plan/6.2_codex/database_implementation_process.md`

Recorded content:

- Input scope
- Design decisions
- Implemented files
- 10 tables
- Validation commands and results
- Next steps for ETL / API integration

### 4.5 Testing and validation

Added:

- `test/6.2_DB/test_database_plan.py`

Passed validation:

```bash
python3 -m unittest test/6.2_DB/test_database_plan.py
python3 backend/database/validate_sources.py
docker compose config
cmp docker/mysql/init/001_clearpath_schema.sql ml_training/plan/6.2_codex/001_clearpath_schema.sql
```

Validation results:

- The schema contains only the Codex 10 tables.
- The manifest contains only the 9 sources.
- The 6 local data files exist.
- The Docker Compose config is valid.
- The Docker initializer is identical to the Codex schema copy.

## 5. Key Judgments for This Round

### 5.1 Responsibility split between Data Lead and Backend Lead

Data & ML Lead is responsible for:

- Data source selection
- Data collection
- Data cleaning
- Field mapping
- Data quality issues
- Deduplication rules
- ETL logic
- ML features and `busyness_scores` output

Backend Lead is responsible for:

- Flask API and database connection
- endpoint implementation
- Docker / MySQL runtime environment
- Database connection pool, transactions, deployment
- Implementation of non-functional requirements in the backend architecture

Shared boundaries:

- Schema conceptual design
- API contract and database field alignment
- Query paths and index strategy

### 5.2 Current completion status

If the goal is "database setup architecture analysis + schema landing design," the current completion is about **80%**.

If the goal is "a complete database system that is runnable with real data," the current completion is about **45%-50%**.

Not yet completed:

- Actually starting MySQL and performing table creation checks.
- ETL scripts to import CSV / GeoJSON.
- Restroom, healthcare, and AED deduplication and merge logic.
- Flask API querying the database.
- ML baseline / dummy score written to `busyness_scores`.
- Real integration of Google Maps / Weather cache.

## 6. File Index

| File | Purpose |
| --- | --- |
| `ml_training/plan/6.2_codex/readme.md` | Codex work record overview |
| `ml_training/plan/6.2_codex/todolist.md` | Sprint 1 follow-up task list |
| `ml_training/plan/6.2_codex/001_clearpath_schema.sql` | Codex schema copy |
| `ml_training/plan/6.2_codex/database.md` | Codex architecture document copy |
| `ml_training/plan/6.2_codex/database_implementation_process.md` | Process record |
| `ml_training/plan/database.md` | Current main database architecture document |
| `docker/mysql/init/001_clearpath_schema.sql` | Docker MySQL initializer |
| `backend/database/clearpath_sources.json` | Data source manifest |
| `backend/database/validate_sources.py` | Data source validation script |
| `tests/test_database_plan.py` | schema / manifest test |

## 7. Notes

- Do not directly merge `toilets`, `reports`, `busyness_predictions`, `traffic_cache`, and `weather_cache` from the CC schema into the Codex schema.
- CC documents can be used as a reference for presentation / task breakdown / field mapping, but the source of truth for the Docker initializer is the Codex 10-table schema.
- If the schema needs to be modified later, update all of the following at the same time:
  - `docker/mysql/init/001_clearpath_schema.sql`
  - `ml_training/plan/6.2_codex/001_clearpath_schema.sql`
  - `ml_training/plan/database.md`
  - `test/6.2_DB/test_database_plan.py`
