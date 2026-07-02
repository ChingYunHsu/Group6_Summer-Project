# ClearPath DB + ML Deployment SOP

Last updated: 2026-06-30
Scope: Deploy the project's MySQL database, Flask API service, and pre-generated ML busyness results to the server.

## 0. Core Principles

This SOP only covers server deployment and import sequence.

- Import existing local JSON / CSV files directly into the server or database.
- Do not re-call external APIs such as SerpAPI, BestTime, or NYC SODA.
- Do not re-run notebooks to regenerate data.
- Do not retrain models online unless explicitly updating the model version.
- The primary data source for ML results is the existing CSVs under `Data+ML/test/6.28-7.3/output/`.

Key pre-built files:

```text
Data+ML/test/6.28-7.3/output/pipeline_outputs_manifest.csv
Data+ML/test/6.28-7.3/output/ml_training_frame_v1.csv
Data+ML/test/6.28-7.3/output/model_metrics_v1.csv
Data+ML/test/6.28-7.3/output/model_test_predictions_v1.csv
Data+ML/test/6.28-7.3/output/prediction_curve_v1.csv
Data+ML/test/6.28-7.3/output/besttime_forecast_summary.csv
Data+ML/test/6.28-7.3/output/besttime_forecast_raw/*.json
Data+ML/test/6.22-6.27/output/serpapi_raw_responses/*.json
```

## 1. Server Preparation

Navigate to the project root directory:

```bash
cd Group6_Summer-Project
```

Verify the following are installed on the server:

```bash
docker --version
docker compose version
python3 --version
poetry --version
mysql --version
```

Python 3.11 is recommended. Backend dependencies are managed via `backend/pyproject.toml`.

## 2. Environment Variable Configuration

Copy the backend environment variable template:

```bash
cd backend
cp .env.example .env
```

The following variables already exist in `backend/.env.example`; copy the file and replace the placeholder values:

```env
API_KEY=...
BESTTIME_API_KEY=...
GOOGLE_MAPS_API_KEY=...
GEMINI_API_KEY=...
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=clearpath_app
DB_PASSWORD=clearpath_app
DB_NAME=clearpath
REDIS_URL=redis://127.0.0.1:6379/0
DB_ENCRYPTION_CHECK=false
JWT_SECRET=...
MEDICAL_PROFILE_ENCRYPTION_KEY=...
```

For production, manually add or override these runtime variables if they are not already present in the copied `.env`:

```env
PORT=5000
FLASK_ENV=production
```

Return to the project root directory:

```bash
cd ..
```

## 3. Start Database and Redis

The current `docker-compose.yml` starts the following services:

- `clearpath-mysql`: MySQL 8.4, port `3306`
- `clearpath-redis`: Redis 7, port `6379`
- `clearpath-phpmyadmin`: phpMyAdmin, port `8080`

Current minimal deployment uses the standard `mysql:8.4` image without MySQL keyring startup flags. Do not add these options unless the image and MySQL keyring component configuration have been updated and tested:

```yaml
--early-plugin-load=keyring_file.so
--keyring_file_data=/var/lib/mysql-keyring/keyring
```

For this minimal deployment, keep the backend setting:

```env
DB_ENCRYPTION_CHECK=false
```

Start the services:

```bash
docker compose up -d mysql redis phpmyadmin
```

Check the containers:

```bash
docker compose ps
```

Wait for the MySQL health check to pass:

```bash
docker exec clearpath-mysql mysqladmin ping -h localhost -uclearpath_app -pclearpath_app
```

## 4. Database Initialization Order

When the Docker volume is created for the first time, MySQL automatically executes the init scripts in filename order:

```text
docker/mysql/init/001_clearpath_schema.sql
docker/mysql/init/002_add_busyness_unique_constraint.sql
docker/mysql/init/003_add_user_profile_fields.sql
docker/mysql/init/004_medical_profiles.sql
docker/mysql/init/005_seed_venues.sql
```

These SQL files are mounted to:

```text
/docker-entrypoint-initdb.d
```

For a brand-new server, running `docker compose up -d mysql` requires no manual SQL execution.

If the MySQL volume already exists, the init SQL scripts will not automatically re-run. Only manually execute them when schema patches are confirmed to be needed:

```bash
docker exec -i clearpath-mysql mysql -uroot -pclearpath_root clearpath < docker/mysql/init/002_add_busyness_unique_constraint.sql
docker exec -i clearpath-mysql mysql -uroot -pclearpath_root clearpath < docker/mysql/init/003_add_user_profile_fields.sql
docker exec -i clearpath-mysql mysql -uroot -pclearpath_root clearpath < docker/mysql/init/004_medical_profiles.sql
docker exec -i clearpath-mysql mysql -uroot -pclearpath_root clearpath < docker/mysql/init/005_seed_venues.sql
```

Do not casually re-run `001_clearpath_schema.sql` on a production database. It contains the main schema, and although most statements use `CREATE TABLE IF NOT EXISTS`, you should back up first.

## 5. Verify Database Connection

```bash
mysql -h 127.0.0.1 -P 3306 -u clearpath_app -pclearpath_app clearpath
```

Or:

```bash
docker exec -it clearpath-mysql mysql -u clearpath_app -pclearpath_app clearpath
```

Basic checks:

```sql
SHOW TABLES;
SELECT COUNT(*) AS venues_count FROM venues;
SELECT COUNT(*) AS busyness_count FROM busyness_scores;
SELECT COUNT(*) AS forecast_count FROM busyness_forecasts;
```

## 6. Backend Dependency Installation

```bash
cd backend
poetry install
```

Run locally or start in the foreground on the server:

```bash
poetry run python src/app.py
```

The backend will listen on:

```text
0.0.0.0:5000
```

Health check:

```bash
curl http://127.0.0.1:5000/api/v1/health
```

If deploying via a system service or process manager, keep the startup command as:

```bash
cd /path/to/Group6_Summer-Project/backend
poetry run python src/app.py
```

## 7. ML File Deployment Order

Sync the existing local output files to the server project directory, preserving the original paths:

```bash
rsync -av Data+ML/test/6.28-7.3/output/ user@server:/path/to/Group6_Summer-Project/Data+ML/test/6.28-7.3/output/
rsync -av Data+ML/test/6.22-6.27/output/ user@server:/path/to/Group6_Summer-Project/Data+ML/test/6.22-6.27/output/
```

Verify the files on the server:

```bash
cd /path/to/Group6_Summer-Project
test -f Data+ML/test/6.28-7.3/output/pipeline_outputs_manifest.csv
test -f Data+ML/test/6.28-7.3/output/model_test_predictions_v1.csv
test -f Data+ML/test/6.28-7.3/output/prediction_curve_v1.csv
test -d Data+ML/test/6.28-7.3/output/besttime_forecast_raw
test -f Data+ML/test/6.22-6.27/output/venue_label_status_grouped_view.csv
test -d Data+ML/test/6.22-6.27/output/serpapi_raw_responses
```

Do not run the following scripts as part of the server deployment workflow:

```bash
python Data+ML/test/6.28-7.3/src/ml_feature_pipeline.py
python Data+ML/test/6.28-7.3/src/build_populartimes_training_data.py
python Data+ML/test/6.28-7.3/src/ml_modeling.py
bash Data+ML/test/6.22-6.27/src/run_phased.sh
python Data+ML/test/6.22-6.27/src/run_phased_search.py
python Data+ML/test/6.22-6.27/src/serpapi_client.py
python Data+ML/test/6.22-6.27/src/venue_serpapi.py
python Data+ML/test/6.22-6.27/src/backfill_healthcare_ratings_to_db.py
python Data+ML/test/6.22-6.27/src/build_healthcare_coverage_label_view.py
python Data+ML/test/6.22-6.27/src/build_healthcare_prediction_groups.py
python Data+ML/test/6.15-6.20/src/busyness_ingestion.py
python Data+ML/test/6.15-6.20/src/live_capacity_telemetry.py
```

These scripts are used to rebuild features, re-parse cached data, rewrite derived CSVs, update database metadata from generated files, or fetch external data online. The current deployment requirement is to directly import existing CSV/JSON files.

## 8. Direct Import of ML CSVs into MySQL

It is recommended to use temporary staging tables for import, then write to the production tables. This avoids modifying the original CSVs and makes rollback easier.

Enable local infile:

```bash
mysql --local-infile=1 -h 127.0.0.1 -P 3306 -u clearpath_app -pclearpath_app clearpath
```

### 8.1 Import Test Set Predictions into busyness_scores

CSV:

```text
Data+ML/test/6.28-7.3/output/model_test_predictions_v1.csv
```

Create staging table:

```sql
DROP TABLE IF EXISTS stg_model_test_predictions_v1;

CREATE TABLE stg_model_test_predictions_v1 (
  source_file VARCHAR(255),
  prediction_group_id VARCHAR(128),
  venue_id VARCHAR(36),
  place_title VARCHAR(255),
  day_of_week VARCHAR(16),
  hour INT,
  busyness_score DECIMAL(6,2),
  is_business_hours VARCHAR(16),
  hours_status VARCHAR(64),
  model_name VARCHAR(64),
  predicted_score DECIMAL(6,2),
  predicted_level VARCHAR(16),
  serving_predicted_level VARCHAR(16),
  abs_error DECIMAL(6,2)
);
```

Import CSV:

```sql
LOAD DATA LOCAL INFILE 'Data+ML/test/6.28-7.3/output/model_test_predictions_v1.csv'
INTO TABLE stg_model_test_predictions_v1
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
```

Write to production table:

```sql
INSERT INTO busyness_scores (
  venue_id,
  score,
  level,
  estimated_wait_minutes,
  forecast_1h,
  forecast_start_time,
  forecast_end_time,
  model_version,
  features_snapshot_id
)
SELECT
  s.venue_id,
  LEAST(100, GREATEST(0, ROUND(s.predicted_score))),
  CASE
    WHEN s.serving_predicted_level IN ('quiet','moderate','busy','no_data')
      THEN s.serving_predicted_level
    WHEN s.predicted_level IN ('quiet','moderate','busy','no_data')
      THEN s.predicted_level
    ELSE 'no_data'
  END,
  NULL,
  JSON_ARRAY(
    JSON_OBJECT(
      'offset_hours', 0,
      'percent', LEAST(100, GREATEST(0, ROUND(s.predicted_score))),
      'level', COALESCE(s.serving_predicted_level, s.predicted_level, 'no_data')
    )
  ),
  TIMESTAMP(CURRENT_DATE, MAKETIME(COALESCE(s.hour, 0), 0, 0)),
  TIMESTAMP(CURRENT_DATE, MAKETIME(COALESCE(s.hour, 0), 0, 0)) + INTERVAL 1 HOUR,
  CONCAT('healthcare_populartimes_', s.model_name, '_v1'),
  CONCAT('model_test_predictions_v1:', s.source_file)
FROM stg_model_test_predictions_v1 s
JOIN venues v ON v.venue_id = s.venue_id
WHERE s.venue_id IS NOT NULL
ON DUPLICATE KEY UPDATE
  score = VALUES(score),
  level = VALUES(level),
  forecast_1h = VALUES(forecast_1h),
  forecast_end_time = VALUES(forecast_end_time),
  features_snapshot_id = VALUES(features_snapshot_id),
  created_at = CURRENT_TIMESTAMP;
```

### 8.2 Import 12-Hour Prediction Curve into busyness_forecasts

CSV:

```text
Data+ML/test/6.28-7.3/output/prediction_curve_v1.csv
```

Create staging table:

```sql
DROP TABLE IF EXISTS stg_prediction_curve_v1;

CREATE TABLE stg_prediction_curve_v1 (
  model_name VARCHAR(64),
  venue_id VARCHAR(36),
  prediction_group_id VARCHAR(128),
  day_of_week VARCHAR(16),
  hour INT,
  predicted_score DECIMAL(6,2),
  predicted_level VARCHAR(16)
);
```

Import CSV:

```sql
LOAD DATA LOCAL INFILE 'Data+ML/test/6.28-7.3/output/prediction_curve_v1.csv'
INTO TABLE stg_prediction_curve_v1
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
```

Write to production table:

```sql
INSERT INTO busyness_forecasts (
  venue_id,
  forecast_for,
  predicted_score,
  predicted_level,
  estimated_wait_minutes,
  model_version
)
SELECT
  s.venue_id,
  TIMESTAMP(CURRENT_DATE, MAKETIME(COALESCE(s.hour, 0), 0, 0)),
  LEAST(100, GREATEST(0, ROUND(s.predicted_score))),
  CASE
    WHEN s.predicted_level IN ('quiet','moderate','busy','no_data')
      THEN s.predicted_level
    ELSE 'no_data'
  END,
  NULL,
  CONCAT('healthcare_populartimes_', s.model_name, '_v1')
FROM stg_prediction_curve_v1 s
JOIN venues v ON v.venue_id = s.venue_id
WHERE s.venue_id IS NOT NULL
ON DUPLICATE KEY UPDATE
  predicted_score = VALUES(predicted_score),
  predicted_level = VALUES(predicted_level),
  estimated_wait_minutes = VALUES(estimated_wait_minutes),
  generated_at = CURRENT_TIMESTAMP;
```

## 9. Optional: Import Healthcare Prediction Group Metadata

If the `venues` table in the server database does not yet have healthcare SerpAPI / prediction group fields, you can write them back using existing CSVs.

First, do a dry-run:

```bash
cd Data+ML/test/6.22-6.27
python src/write_healthcare_prediction_groups_to_db.py
```

After confirming the output is correct, perform the live write:

```bash
CLEARPATH_DB_HOST=127.0.0.1 \
CLEARPATH_DB_PORT=3306 \
CLEARPATH_DB_USER=clearpath_app \
CLEARPATH_DB_PASSWORD=clearpath_app \
CLEARPATH_DB_NAME=clearpath \
python src/write_healthcare_prediction_groups_to_db.py --live
```

This script does not call external APIs; it only reads:

```text
Data+ML/test/6.22-6.27/output/venue_label_status_grouped_view.csv
```

## 10. Verify ML Import Results

```sql
SELECT COUNT(*) AS staging_predictions
FROM stg_model_test_predictions_v1;

SELECT model_version, COUNT(*) AS rows_written
FROM busyness_scores
GROUP BY model_version
ORDER BY rows_written DESC;

SELECT model_version, COUNT(*) AS forecast_rows
FROM busyness_forecasts
GROUP BY model_version
ORDER BY forecast_rows DESC;

SELECT venue_id, score, level, forecast_start_time, forecast_end_time, model_version
FROM busyness_scores
ORDER BY created_at DESC
LIMIT 10;
```

API verification:

```bash
curl http://127.0.0.1:5000/api/v1/venues/seed-healthcare-bellevue-001/busyness
curl http://127.0.0.1:5000/api/v1/venues/seed-healthcare-bellevue-001/busyness/forecast
```

If the seed venue query returns no ML results, switch to a `venue_id` that exists in the staging table:

```sql
SELECT venue_id, place_title, model_name
FROM stg_model_test_predictions_v1
LIMIT 5;
```

## 11. Full Server Execution Sequence

Recommended deployment order:

```bash
# 1. Enter the project
cd /path/to/Group6_Summer-Project

# 2. Start infrastructure services
docker compose up -d mysql redis phpmyadmin

# 3. Wait for MySQL to be healthy
docker compose ps
docker exec clearpath-mysql mysqladmin ping -h localhost -uclearpath_app -pclearpath_app

# 4. Install backend dependencies
cd backend
poetry install

# 5. Configure .env
cp .env.example .env
# Edit .env

# 6. Start Flask API
poetry run python src/app.py

# 7. Open another terminal, import existing ML CSVs
cd /path/to/Group6_Summer-Project
mysql --local-infile=1 -h 127.0.0.1 -P 3306 -u clearpath_app -pclearpath_app clearpath

# 8. Execute the SQL in Section 8 within MySQL

# 9. Verify the API
curl http://127.0.0.1:5000/api/v1/health
```

## 12. Rollback and Re-import

To rollback only the current ML import:

```sql
DELETE FROM busyness_scores
WHERE model_version LIKE 'healthcare_populartimes_%_v1';

DELETE FROM busyness_forecasts
WHERE model_version LIKE 'healthcare_populartimes_%_v1';
```

Drop staging tables:

```sql
DROP TABLE IF EXISTS stg_model_test_predictions_v1;
DROP TABLE IF EXISTS stg_prediction_curve_v1;
```

To re-import, simply re-execute Section 8. Do not delete the MySQL Docker volume unless you intend to rebuild the entire database.

The current minimal compose file should only keep the MySQL data volume:

```yaml
clearpath_mysql_data:
```

Do not add a `clearpath_mysql_keyring` volume for this deployment path. A keyring volume alone does not enable MySQL keyring support and can cause confusion if the corresponding MySQL startup options are not supported by the image.

## 13. Operations to Avoid During Deployment

Do not execute these generative workflows during server deployment:

```bash
python Data+ML/test/6.28-7.3/src/ml_feature_pipeline.py
python Data+ML/test/6.28-7.3/src/build_populartimes_training_data.py
python Data+ML/test/6.28-7.3/src/ml_modeling.py
bash Data+ML/test/6.22-6.27/src/run_phased.sh
python Data+ML/test/6.22-6.27/src/run_phased_search.py
python Data+ML/test/6.22-6.27/src/serpapi_client.py
python Data+ML/test/6.22-6.27/src/venue_serpapi.py
python Data+ML/test/6.22-6.27/src/backfill_healthcare_ratings_to_db.py
python Data+ML/test/6.22-6.27/src/build_healthcare_coverage_label_view.py
python Data+ML/test/6.22-6.27/src/build_healthcare_prediction_groups.py
python Data+ML/test/6.15-6.20/src/busyness_ingestion.py
python Data+ML/test/6.15-6.20/src/live_capacity_telemetry.py
```

Reasons:

- `ml_feature_pipeline.py` will rebuild `output/*.csv` from scratch.
- `build_populartimes_training_data.py` will re-parse cached JSON and overwrite label CSVs.
- `ml_modeling.py` is model-building support code, not a deployment import step.
- `run_phased.sh`, `run_phased_search.py`, `serpapi_client.py`, and `venue_serpapi.py` are SerpAPI-related and may trigger external API calls.
- `build_healthcare_coverage_label_view.py` and `build_healthcare_prediction_groups.py` rewrite derived healthcare label/group CSVs.
- `backfill_healthcare_ratings_to_db.py` and `live_capacity_telemetry.py` write back to the database and are not part of the direct CSV import path.
- `busyness_ingestion.py` will request the NYC SODA API and regenerate baselines.

The current deployment only uses already persisted CSV / JSON files.
