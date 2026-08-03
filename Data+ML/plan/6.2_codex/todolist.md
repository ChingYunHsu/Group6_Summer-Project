# ClearPath Sprint 1 Codex TODO

## P0 - Must complete this week

### 1. MySQL table creation verification

- [ ] Start MySQL:
  - `docker compose up -d mysql`
- [ ] Confirm container health:
  - `docker compose ps`
- [ ] Connect to MySQL and check schema:
  - `SHOW DATABASES;`
  - `USE clearpath;`
  - `SHOW TABLES;`
- [ ] Verify the 10 tables are actually created:
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
- [ ] Record `SHOW TABLES` / `DESCRIBE` results into the process documentation.

### 2. ETL base framework

- [ ] Create an ETL directory, e.g. `backend/database/etl/`.
- [ ] Add common configuration:
  - Data source root directory
  - MySQL connection configuration
  - Manhattan bounding box constant
- [ ] Add common utilities:
  - CSV reader
  - GeoJSON reader
  - `POINT (lng lat)` parser
  - source hash generator
  - boolean normalization
  - safe decimal parser
- [ ] Add `run_all.py` to run loaders in order.

### 3. Public Restrooms loader

- [ ] Read `Public_Restrooms_20260526.csv`.
- [ ] Write to `venues`:
  - `venue_type = restroom`
  - name / latitude / longitude / address / website
- [ ] Write to `restroom_profiles`:
  - restroom type
  - status
  - operator
  - ADA accessibility
  - changing station
  - notes
- [ ] Write to `venue_source_links`.
- [ ] Support repeated runs without duplicate inserts.

### 4. OSM Healthcare loader

- [ ] Read `POI_healtcare.geojson`.
- [ ] Parse GeoJSON coordinates, note the order is `[lng, lat]`.
- [ ] Filter out outlier points clearly outside Manhattan / NYC.
- [ ] Write to `venues`:
  - `venue_type = healthcare`
  - name / latitude / longitude / address / phone / website / opening hours
- [ ] Write to `healthcare_profiles`:
  - healthcare category
  - speciality
  - facility type
- [ ] Write to `venue_source_links`.

### 5. AED loader

- [ ] Read `New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv`.
- [ ] Generate a stable source hash using `Entity_Name + Address`.
- [ ] Write to `venues`:
  - `venue_type = emergency_asset`
  - name / address / borough / latitude / longitude
- [ ] Write to `emergency_assets`:
  - floor
  - location type
  - AED count
  - trained people count
  - last updated
- [ ] Write to `venue_source_links`.

## P1 - Sprint 1 strongly supporting tasks

### 6. NYS Health Facility loader

- [ ] Read `Health_Facility_General_Information_20260526.csv`.
- [ ] Filter out records missing coordinates, record skipped count.
- [ ] Map `Facility County = New York` to Manhattan.
- [ ] Write to `venues` and `healthcare_profiles`.
- [ ] Apply initial matching rules against OSM healthcare:
  - exact / near name
  - coordinate proximity
  - address similarity
- [ ] Write matching results to `venue_source_links`.

### 7. Parks Toilets loader

- [ ] Read `Directory_Of_Toilets_In_Public_Parks_20260526.csv`.
- [ ] Record the missing coordinates issue.
- [ ] Prefer matching existing restroom venues by name / borough / location.
- [ ] Do not force geocoding for now; records that cannot be matched go into a skipped / review log.
- [ ] Add matched records to `restroom_profiles` and `venue_source_links`.

### 8. Pedestrian Ramps loader

- [ ] Read `Pedestrian_Ramp_Locations_20260526.csv`.
- [ ] Do a Manhattan subset or chunked import first, to avoid processing 200k+ rows at once which slows down the dev environment.
- [ ] Parse `the_geom` into latitude / longitude.
- [ ] Write to `pedestrian_ramps`.
- [ ] Output import count, skipped count, and outlier geometry count.

### 9. Data quality report

- [ ] Output row count / imported count / skipped count for each source.
- [ ] Record main issues:
  - Parks Toilets missing coordinates
  - NYS Health missing coordinates
  - OSM tags unstable
  - AED has no stable ID
  - Pedestrian Ramps large data volume
- [ ] Form data quality bullet points usable for Presentation 3.

### 10. Baseline `busyness_scores`

- [ ] Design an MVP baseline score, do not commit to a final ML model.
- [ ] Initial inputs can include:
  - venue type
  - active report count
  - hour of day
  - weather cache placeholder
- [ ] Write sample data into `busyness_scores` for frontend pin color testing.
- [ ] Record follow-up scikit-learn model plan.

## P2 - Follow-up enhancement tasks

### 11. External context cache

- [ ] Design Google Maps cache request key.
- [ ] Design Weather / Urban Heat cache request key.
- [ ] Clarify cache expiry:
  - route / distance matrix: 30 minutes or request dependent
  - weather current: 1 hour
  - urban heat static: long-lived
- [ ] Do not force real API integration in Sprint 1 for now.

### 12. API contract alignment

- [ ] Confirm `/api/v1/venues` return fields with Backend Lead.
- [ ] Clarify database direct fields vs API derived fields.
- [ ] Handle fallback:
  - `language_tags = []`
  - `primary_language = null`
  - `secondary_language = null`
  - `active_warning` derived from `user_reports`
  - `accessible_status` derived from restroom / ramps / reports

### 13. Presentation 3 preparation

- [ ] Prepare the Data Analytics talk structure:
  - data sources
  - collection method
  - cleaning / merging
  - quality problems
  - early insights
  - ML plan
- [ ] Prepare the data source volume table.
- [ ] Prepare the data quality issues table.
- [ ] Prepare the ML roadmap:
  - baseline score
  - feature engineering
  - model comparison later

## Continuous verification commands

Run after every schema / manifest / source scope change:

```bash
python3 -m unittest tests/test_database_plan.py
python3 backend/database/validate_sources.py
docker compose config
cmp docker/mysql/init/001_clearpath_schema.sql ml_training/plan/6.2_codex/001_clearpath_schema.sql
```

## Do not do

- [ ] Do not modify `ml_training/plan/6.2_CC/*`.
- [ ] Do not directly add old tables from the CC schema back into the Docker schema:
  - `toilets`
  - `reports`
  - `busyness_predictions`
  - `users`
  - `saved_venues`
  - `traffic_cache`
  - `weather_cache`
  - `accessibility_infrastructure`
- [ ] Do not reintroduce deprecated data sources:
  - `POI_accessibility.geojson`
  - HRSA
  - CityMD
  - Google Places
  - MTA
  - Taxi
  - Traffic Volume
  - Language datasets
