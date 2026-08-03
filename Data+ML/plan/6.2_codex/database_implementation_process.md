# ClearPath Database Implementation Process

## 1. Input Scope Confirmed

This implementation follows the revised ClearPath database scope confirmed on 2026-06-02.

Only these nine sources are included:

| Type | Source | Implementation role |
| --- | --- | --- |
| Internal | User Reports Database | Runtime tables for reports and confirmations |
| Toilet | NYC Public Restrooms `i7jb-7jku` | Venue + restroom profile source |
| Toilet | Directory of Toilets in Public Parks `hjae-yuav` | Venue + restroom profile supplement |
| Healthcare | OpenStreetMap / Overpass POI | Broad healthcare venue source |
| Healthcare | NYS Health Facility General Information `vn5v-hh5r` | Official healthcare validation source |
| Healthcare | AED Inventory `2er2-jqsx` | Emergency asset venue source |
| Accessibility | Pedestrian Ramp Locations `ufzp-rrqu` | Wheelchair routing infrastructure |
| Traffic | Google Map API | Runtime route/context cache |
| Weather | Weather / NYC Urban Heat Portal | Runtime weather/heat context cache |

Excluded sources are intentionally not part of the MVP database path: `POI_accessibility.geojson`, HRSA, CityMD, Google Places, MTA, taxi, traffic volume, LASS, LEP, and other unlisted sources.

## 2. Design Decision

The database is implemented as one MySQL 8.4 schema named `clearpath`.

The design avoids one-table-per-source storage. Similar source types are merged into business objects:

- restrooms merge into `venues` + `restroom_profiles`
- healthcare POIs and NYS facilities merge into `venues` + `healthcare_profiles`
- AED records are displayable `venues` with details in `emergency_assets`
- pedestrian ramps stay separate in `pedestrian_ramps` because they support routing rather than venue search
- Google Maps and Weather are cached in `external_context_cache`
- live user reports are stored in `user_reports` and `report_confirmations`
- ML output is stored in `busyness_scores`

This keeps the schema compact while preserving source traceability through `venue_source_links`.

## 3. Files Implemented

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Adds local MySQL 8.4 service and schema initializer mount |
| `docker/mysql/init/001_clearpath_schema.sql` | Creates the 10-table ClearPath schema |
| `ml_training/plan/6.2_codex/001_clearpath_schema.sql` | Codex-owned copy of the Docker initializer schema |
| `backend/database/clearpath_sources.json` | Source manifest for the nine approved sources |
| `backend/database/validate_sources.py` | Validates retained local files and checks excluded files are unused |
| `backend/database/README.md` | Explains database scope, tables, and local setup |
| `ml_training/plan/database.md` | Updated architecture note aligned to the nine-source scope |
| `tests/test_database_plan.py` | Unit tests for manifest scope, source availability, and schema table set |

## 4. Schema Tables Created

The SQL initializer creates exactly these core tables:

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

The Docker initializer and the Codex copy under `ml_training/plan/6.2_codex` must remain identical. The `ml_training/plan/6.2` and `ml_training/plan/6.2_CC` directories are separate Claude/CC work areas and are not the source of truth for the Docker initializer.

Key relationships:

- profile tables reference `venues`
- source links reference `venues`
- reports optionally reference `venues`
- confirmations reference `user_reports`
- busyness scores reference `venues`
- external context cache optionally references `venues`

## 5. Validation Results

Commands run from the repository root:

```bash
python3 backend/database/validate_sources.py
python3 -m unittest tests/test_database_plan.py
docker compose config
```

Results:

- source manifest includes 9 approved sources
- 6 retained local source files exist
- excluded local files are not referenced
- schema defines the expected 10 tables
- Docker Compose configuration is valid

Local retained file counts found by the validator:

| File | Count |
| --- | ---: |
| `Public_Restrooms_20260526.csv` | 1,066 rows |
| `Directory_Of_Toilets_In_Public_Parks_20260526.csv` | 616 rows |
| `POI_healtcare.geojson` | 966 features |
| `Health_Facility_General_Information_20260526.csv` | 5,963 rows |
| `New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv` | 7,373 rows |
| `Pedestrian_Ramp_Locations_20260526.csv` | 217,679 rows |

## 6. Next Implementation Step

The next backend step is to add ETL loaders that read the six local retained files and populate the schema:

- restroom loader with dedupe into `venues` and `restroom_profiles`
- healthcare loader with OSM/NYS merge logic into `venues` and `healthcare_profiles`
- AED loader into `venues` and `emergency_assets`
- ramp loader into `pedestrian_ramps`

After ETL, Flask endpoints can be wired to the schema:

- `GET /api/v1/venues`
- `GET /api/v1/venues/{venue_id}`
- `POST /api/v1/reports`
- `POST /api/v1/reports/{report_id}/confirmations`
- `GET /api/v1/integrations/status`
