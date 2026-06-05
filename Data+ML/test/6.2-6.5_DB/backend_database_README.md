# ClearPath Database Implementation

This directory implements the approved ClearPath database architecture for the nine retained data sources.

## Scope

The backend uses one MySQL/MariaDB schema named `clearpath`. Source files remain ETL inputs under `../data_source`; they are not exposed as one-table-per-source application tables.

Included sources:

- Internal User Reports Database
- NYC Public Restrooms `i7jb-7jku`
- Directory of Toilets in Public Parks `hjae-yuav`
- OpenStreetMap / Overpass healthcare POI
- NYS Health Facility General Information `vn5v-hh5r`
- AED Inventory `2er2-jqsx`
- Pedestrian Ramp Locations `ufzp-rrqu`
- Google Map API
- Weather / NYC Urban Heat Portal

Excluded local files are listed in `clearpath_sources.json` and must not be added to the MVP ETL path unless the team revises the source scope.

## Tables

The SQL initializer creates:

- `venues`
- `venue_source_links`
- `restroom_profiles`
- `healthcare_profiles`
- `emergency_assets`
- `pedestrian_ramps`
- `user_reports`
- `report_confirmations`
- `busyness_scores`
- `external_context_cache`

## Local MySQL

From the repository root:

```bash
docker compose up -d mysql
```

The initializer at `docker/mysql/init/001_clearpath_schema.sql` runs when the MySQL volume is first created.

## Source Validation

Run:

```bash
python3 backend/database/validate_sources.py
```

The validator checks that all retained local source files exist and that excluded local files are not referenced by the ClearPath database manifest.
