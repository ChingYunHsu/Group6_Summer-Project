# Venue Spatial Coverage Testing Standard Operating Procedure (SOP)

> Date: 2026-06-15  
> Scope: Spatial coverage testing of Citi Bike, MTA subway, and NYC traffic data  
> Input: `Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv`  
> Status: Approved implementation plan

## 1. Objective

Measure how many project venues have at least one usable data source point within a reasonable GPS radius.
This phase only measures spatial feature availability; it does not evaluate prediction quality, correlation, or production model weight.

Test radii:

```text
100m, 200m, 300m, 400m, 500m
```

Data source attribution order:

```text
Citi Bike -> Citi Bike + MTA -> Citi Bike + MTA + Traffic
```

No pass/fail coverage threshold is defined before reviewing the results.

## 2. Fixed Decisions

### 2.1 Venue Dataset

- Use the currently provided `venues_clean.csv`.
- Expected input scale: 4,838 rows before `venue_id` deduplication.
- Do not repeat the coordinate validation already completed in ETL.
- Deduplicate venue rows by `venue_id`, keeping the first row.
- Records with the same coordinates but different `venue_id` are retained as separate denominator records.
- Record the duplicate `venue_id` count in the run metadata.
- Do not clean or exclude records based on `borough` during this SOP.

### 2.2 Required Grouping Dimensions

Generate results for the following dimensions:

- Overall
- `venue_type` (venue type)
- `district` (district)

The initial version does not generate a `venue_type × district` crosstab.

Currently expected venue types include:

```text
emergencyasset (AED)
healthcare (healthcare)
restroom (restroom)
```

### 2.3 Data Source Priority

1. Citi Bike GBFS
2. MTA subway
3. NYC traffic

NYC pedestrian sensors are excluded from the main coverage sequence because their effective spatial coverage is too sparse.
They remain suitable for use in later model calibration.

BestTime is excluded from this coverage test because it is a paid venue-level data source and is unlikely to match most emergency assets and restrooms.

## 3. Traffic Data Ingestion Decision

Retain NYC traffic as a candidate spatial data source, but do not reuse
`Data+ML/test/6.15-5.20/src/busyness_ingestion.py` as the production ingestion pipeline.

Current disposition:

```text
Data source: retained for coverage testing
Existing ingestion implementation: prototype only
Current prediction weight: 0
Database writes during coverage testing: prohibited
```

Traffic data may only receive future model weight after the following conditions are met:

- venue-time repeated aggregation is fixed;
- database writes are truly idempotent;
- historical data source year and prediction timestamp semantics are fixed;
- correlation with pedestrian or traffic-derived activity metrics is measured;
- ablation testing shows measurable prediction improvement.

Spatial coverage alone is not evidence that traffic data predicts pedestrian or venue busyness.

## 4. File Inventory

Create:

```text
Data+ML/test/6.15-5.20/src/venue_coverage.py
Data+ML/test/6.15-5.20/src/run_venue_coverage.py
Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Planning document:

```text
Data+ML/test/6.15-5.20/docs/venue_coverage_sop_zh.md
```

This work does not modify the `busyness_scores` or `busyness_forecasts` tables.

## 5. CLI Interface Contract

Run from the project root:

```bash
python Data+ML/test/6.15-5.20/src/run_venue_coverage.py \
  --venue-file Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv \
  --radii 100,200,300,400,500 \
  --sources citibike,mta,traffic \
  --traffic-year 2025 \
  --output-dir Data+ML/test/6.15-5.20/output/venue_coverage
```

Defaults:

```text
--radii          100,200,300,400,500
--sources        citibike,mta,traffic
--traffic-year   2025
--page-size      5000
--connect-timeout 2
--read-timeout   5
--max-retries    3
```

The order of `--sources` defines the incremental combination attribution.

The CLI must reject the following cases:

- empty radius list;
- non-positive radius;
- decreasing or duplicate radii;
- unsupported data source name;
- page size greater than 5,000;
- missing venue input file.

## 6. API Data Source Contracts

### 6.1 Citi Bike

Endpoints:

```text
https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_information.json
https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_status.json
```

Rules:

- Use `station_information` to obtain `station_id`, name, latitude, and longitude.
- Use `station_status` to identify stations currently installed and operating (if available).
- Associate via `station_id`.
- Do not treat bikes or docking points as venue foot traffic at this phase.
- Record the feed `last_updated`, TTL, fetch time, raw station count, and retained point count.

Normalized point format:

```text
source = citibike
source_id = station_id
name = station name
latitude (latitude)
longitude (longitude)
source_timestamp (source timestamp)
```

### 6.2 MTA Subway

Default dataset:

```text
MTA Station Complexes
Dataset ID: 5f5g-n3cz
API: https://data.ny.gov/resource/5f5g-n3cz.json
```

Rules:

- Read station complex ID, name, and coordinates directly.
- No OD aggregation query required.
- No `--mta-year` parameter required.
- Record the dataset ID, query statement, fetch time, raw API row count, and retained point count.

Normalized point format:

```text
source = mta
source_id = complex_id
name = complex_name (station complex name)
latitude (latitude)
longitude (longitude)
source_timestamp (source timestamp)
```

### 6.3 NYC Traffic

Use the official NYC SODA traffic dataset already referenced by the project:

```text
Dataset ID: 7ym2-wayt
API: https://data.cityofnewyork.us/resource/7ym2-wayt.json
```

Rules:

- Filter by the requested `--traffic-year`.
- Use server-side grouping by `segmentid`.
- Request one representative geometry per segment.
- Convert EPSG:2263 segment geometry to the WGS84 coordinate system.
- Use one representative point per segment for coverage testing.
- Do not compute busyness scores.
- Do not invoke database insert code.
- Record the year, dataset ID, query statement, coordinate conversion failure count, and retained point count.

Normalized point format:

```text
source = traffic
source_id = segmentid
name = street or segment label
latitude (latitude)
longitude (longitude)
source_timestamp (source timestamp)
```

## 7. API Execution Strategy

### 7.1 Pagination

- Maximum page size: 5,000.
- Use `$limit` and `$offset` SODA pagination when server-side grouped results still exceed one page.
- Stop only when a page contains fewer records than the requested page size.
- Add a safety cap of 20,000 unique points per data source.
- If the safety cap is exceeded, fail that data source rather than silently truncating.

### 7.2 Timeout and Retry

Use:

```python
timeout = (2, 5)
```

Meaning:

- connection timeout: 2 seconds;
- response read timeout: 5 seconds.

Retry each failed request up to three times with the following delays:

```text
1 second, 2 seconds, 4 seconds
```

Retry connection errors, read timeouts, HTTP 429, and HTTP 5xx responses. Do not retry other HTTP 4xx responses.

### 7.3 Failure Isolation

Each data source runs independently.

If a data source still fails after retrying:

- set its metadata status to `failed`;
- record the exception type and a concise error message;
- continue processing successfully fetched data sources;
- do not represent the failed data source as zero coverage;
- do not generate any combined results that include the failed data source.

Example:

```text
Citi Bike succeeds, MTA fails, Traffic succeeds:
- generate Citi Bike standalone coverage result;
- generate Traffic standalone coverage result;
- do not generate Citi Bike + MTA combination;
- do not generate Citi Bike + MTA + Traffic combination.
```

## 8. Point Normalization and Deduplication

For each data source:

1. Parse the API response into the normalized point schema.
2. Drop records with missing, non-numeric, or unconvertible API coordinates.
3. Deduplicate by `source_id`, keeping the first valid record.
4. If multiple remaining IDs have the exact same latitude and longitude, keep one coordinate for spatial computation.
5. Retain the following counts:
   - raw record count;
   - valid record count;
   - unique source ID count;
   - unique coordinate count;
   - rejected record count.

Do not persist raw API responses or normalized point snapshots to disk. Data source points exist in memory only during the run.

## 9. Spatial Algorithm

Use `sklearn.neighbors.BallTree` with the Haversine metric.

Processing flow for each successful data source:

1. Convert data source and venue coordinates from degrees to radians.
2. Build a BallTree from the unique data source coordinates.
3. Query the nearest data source point for each deduplicated venue.
4. Convert the angular distance to meters using the following formula:

```text
distance_m = angular_distance × 6,371,008.8
```

5. Store the nearest `source_id` and nearest distance for each venue.
6. Compute all radius flags from this single nearest distance result.

Do not rebuild or query the tree separately for each radius.

Coverage rule:

```text
covered(source, radius) = nearest_distance_m <= radius
```

## 10. Coverage Metrics

### 10.1 Single-Source Coverage

For each data source, radius, and grouping dimension:

```text
venue_count (venue count)
covered_count (covered count)
coverage_rate (coverage rate)
newly_covered_count_vs_previous_radius (newly covered count vs previous radius)
marginal_gain_percentage_points (marginal gain percentage points)
```

At 100m, the coverage of the previous radius is zero.

```text
coverage_rate = covered_count / venue_count
marginal_gain_pp = current_coverage_rate - previous_coverage_rate
```

### 10.2 Combined Coverage

For each radius, apply data sources in the fixed CLI order:

```text
C1 = Citi Bike
C2 = Citi Bike or MTA
C3 = Citi Bike or MTA or Traffic
```

Report at each stage:

```text
cumulative_covered_count (cumulative covered count)
cumulative_coverage_rate (cumulative coverage rate)
incremental_unique_covered_count (incremental unique covered count)
incremental_gain_percentage_points (incremental gain percentage points)
```

The incremental count of a newly added data source includes only venues not already covered by a previous data source at the same radius.

### 10.3 Distance Distribution

For each single source and grouping dimension, report:

```text
nearest_distance_median (nearest distance median)
nearest_distance_p90 (nearest distance 90th percentile)
nearest_distance_max (nearest distance maximum)
```

## 11. Output Structure

Each run uses UTC time:

```text
Data+ML/test/6.15-5.20/output/venue_coverage/
  runs/
    YYYYMMDDTHHMMSSZ/
      venue_coverage_detail.csv
      coverage_summary.csv
      coverage_report.md
      run_metadata.json
      coverage_by_radius.png
      incremental_coverage.png
      venue_type_coverage_heatmap.png
      uncovered_venue_distribution.png
  latest/
    venue_coverage_detail.csv
    coverage_summary.csv
    coverage_report.md
    run_metadata.json
    coverage_by_radius.png
    incremental_coverage.png
    venue_type_coverage_heatmap.png
    uncovered_venue_distribution.png
```

The timestamped run directory is written first. The `latest/` directory is updated only after all required artifacts for that run are successfully generated.

### 11.1 `venue_coverage_detail.csv`

One row per deduplicated venue.

Required base columns:

```text
venue_id (venue ID)
venue_type (venue type)
district (district)
latitude (latitude)
longitude (longitude)
```

Columns for each successful data source:

```text
{source}_nearest_source_id (nearest data source ID)
{source}_nearest_distance_m (nearest distance meters)
{source}_covered_100m (100m covered)
{source}_covered_200m (200m covered)
{source}_covered_300m (300m covered)
{source}_covered_400m (400m covered)
{source}_covered_500m (500m covered)
```

Columns for failed data sources may be absent, but the failure must be explicitly recorded in `run_metadata.json` and `coverage_report.md`.

### 11.2 `coverage_summary.csv`

Required columns:

```text
scope (scope)
group_name (group name)
group_value (group value)
coverage_kind (coverage kind)
source_or_combination (data source or combination)
radius_m (radius meters)
venue_count (venue count)
covered_count (covered count)
coverage_rate (coverage rate)
incremental_covered_count (incremental covered count)
marginal_gain_pp (marginal gain percentage points)
nearest_distance_median (nearest distance median)
nearest_distance_p90 (nearest distance 90th percentile)
```

Values:

```text
scope: overall | venue_type | district
coverage_kind: standalone | cumulative
```

Distance distribution fields are populated on single-source rows and left empty on cumulative combination rows.

### 11.3 `run_metadata.json`

Required sections:

```json
{
  "run_id": "YYYYMMDDTHHMMSSZ",
  "started_at": "ISO-8601 UTC",
  "completed_at": "ISO-8601 UTC",
  "timezone": "UTC",
  "venue_input": {},
  "parameters": {},
  "sources": {},
  "software": {},
  "artifacts": []
}
```

Recorded content:

- venue file path and row count;
- unique venue count and duplicate `venue_id` count;
- radii and data source order;
- MTA and Traffic years;
- API URL, dataset ID, request parameters, and query statement;
- API fetch time and maximum data source timestamp;
- data source data age or `timestamp_unavailable`;
- raw, valid, unique ID, unique coordinate, and rejected counts;
- data source status, retry count, and failure message;
- Python and package versions;
- artifact file names.

### 11.4 `coverage_report.md`

Required sections:

1. Run summary
2. Data source status and timeliness
3. Overall single-source coverage
4. Cumulative coverage and data source marginal contribution
5. Coverage by `venue_type`
6. Coverage by district
7. Nearest distance distribution
8. Uncovered venue count
9. Data quality warnings
10. Interpretation constraints

Do not automatically recommend a production radius. Present the marginal results from 100m to 500m for review.

## 12. Static Visualizations

Use PNG format, 1,600 × 900 pixels, 150 DPI. Do not generate interactive maps.

Required charts:

### `coverage_by_radius.png` (coverage by radius)

- X axis: radius
- Y axis: coverage rate
- One line per single data source
- Additional line for valid cumulative combinations

### `incremental_coverage.png` (incremental coverage)

- Bar chart grouped by radius
- Show the contribution percentage points of each data source in the combination order

### `venue_type_coverage_heatmap.png` (venue type coverage heatmap)

- Rows: venue types
- Columns: data sources/combinations and radii
- Cells: coverage rate

### `uncovered_venue_distribution.png` (uncovered venue distribution)

Use a static grouped bar chart rather than a map:

- X axis: district or venue type
- Y axis: count still uncovered
- Series: radius or final combination

Each chart must include a title, axis labels, a legend where applicable, and the data source/run timestamp.

## 13. Test-Driven Implementation Tasks

### Task 1: CLI Parsing and Validation

Files:

```text
Create: Data+ML/test/6.15-5.20/src/run_venue_coverage.py
Create: Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Tests:

- defaults parse correctly;
- configurable MTA and Traffic years are preserved;
- data source order is maintained;
- invalid radii and page sizes raise errors;
- missing venue file fails before API calls.

Run:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py -k cli
```

Expected: CLI tests pass.

### Task 2: HTTP Client, Retry, and Data Source Isolation

Files:

```text
Create: Data+ML/test/6.15-5.20/src/venue_coverage.py
Modify: Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Tests:

- each request uses `timeout=(2, 5)`;
- transient failures retry three times with `1/2/4` delays;
- non-retryable 4xx fails immediately;
- pagination stops on a short page;
- data source fails when exceeding 20,000 unique points;
- one data source failing does not stop other data sources;
- combinations including a failed data source are omitted.

Run:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py -k 'http or retry or pagination or isolation'
```

Expected: HTTP behavior tests pass without live network access.

### Task 3: Data Source Adapters

Files:

```text
Modify: Data+ML/test/6.15-5.20/src/venue_coverage.py
Modify: Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Tests:

- Citi Bike information/status association;
- MTA server-side unique station resolution;
- Traffic unique segment resolution and coordinate conversion;
- requested year appears in the data source query;
- data source ID deduplication;
- duplicate coordinate removal;
- invalid API coordinates are rejected and counted;
- data source timeliness metadata is populated.

Run:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py -k source
```

Expected: data source adapter tests pass using fixtures or mocked responses.

### Task 4: BallTree Distance Computation

Files:

```text
Modify: Data+ML/test/6.15-5.20/src/venue_coverage.py
Modify: Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Tests:

- known coordinate pairs produce the expected Haversine distance within tolerance;
- nearest data source ID is correct;
- the exact 100m boundary is covered;
- a single tree query supports all five radius flags;
- venue deduplication is performed only via `venue_id`;
- identical coordinates but different venue IDs remain separate.

Run:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py -k 'distance or balltree or dedup'
```

Expected: spatial tests pass.

### Task 5: Coverage Aggregation

Files:

```text
Modify: Data+ML/test/6.15-5.20/src/venue_coverage.py
Modify: Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Tests:

- single-source coverage per radius;
- radius marginal count and percentage point computation;
- cumulative data source order;
- incremental unique attribution;
- overall aggregation;
- `venue_type` aggregation;
- district aggregation;
- no `venue_type × district` crosstab;
- median and P90 distance.

Run:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py -k coverage
```

Expected: aggregation tests pass.

### Task 6: Artifacts and Visualizations

Files:

```text
Modify: Data+ML/test/6.15-5.20/src/venue_coverage.py
Modify: Data+ML/test/6.15-5.20/src/run_venue_coverage.py
Modify: Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Tests:

- detail CSV contract;
- summary CSV contract;
- metadata JSON contract;
- Markdown required sections;
- all four PNG files exist and are non-empty;
- timestamped run directory is created;
- `latest/` is updated only after full success;
- no raw API responses or data source point snapshots are written.

Run:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py -k 'artifact or report or chart or metadata'
```

Expected: output contract tests pass.

### Task 7: Full Validation and Live Smoke Test

Run unit tests:

```bash
pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py
```

Expected: all coverage tests pass.

Run the live API smoke test:

```bash
python Data+ML/test/6.15-5.20/src/run_venue_coverage.py \
  --venue-file Data+ML/test/6.15-5.20/tests/output/venues_clean.csv \
  --radii 100,200,300,400,500 \
  --sources citibike,mta,traffic \
  --mta-year 2025 \
  --traffic-year 2025 \
  --output-dir Data+ML/test/6.15-5.20/output/venue_coverage
```

Expected:

- process exit code 0 when at least one data source succeeds;
- data source failures are visible and not represented as zero coverage;
- a complete timestamped run directory exists;
- `latest/` points to the newly completed result;
- no MySQL tables are modified.

## 14. Review Checklist

Before interpreting the results, confirm:

- [ ] Venue denominator and duplicate counts are recorded.
- [ ] All data source statuses are explicit.
- [ ] API query years and dataset IDs are recorded.
- [ ] No data source silently stops at 5,000 rows.
- [ ] Failed data sources are excluded from affected combinations.
- [ ] Both single-source and cumulative coverage are presented.
- [ ] Results include overall, venue type, and district views.
- [ ] Marginal change at each 100m increment is shown.
- [ ] Traffic is not described as observed pedestrian busyness.
- [ ] No prediction weight is inferred from spatial coverage.
- [ ] No raw API responses are persisted.
- [ ] No database writes occurred.

## 15. Post-Test Decisions

After reviewing the generated coverage report, decide:

1. Which radius provides an acceptable coverage-versus-locality tradeoff.
2. Whether Traffic adds enough unique spatial coverage to justify further validation work.
3. Which venue types or districts need fallback features.
4. Whether to add pedestrian sensors as a calibration label.
5. Whether to advance from spatial coverage testing to temporal correlation and model ablation analysis.

Do not assign production weights until the temporal validation phase is complete.
