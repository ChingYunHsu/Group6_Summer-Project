# ClearPath DB + ML Deployment SOP

Last updated: 2026-07-09

Scope: deploy the ClearPath MySQL/Redis infrastructure, run required DB migrations/seeds, execute the forecast-v2 Data/ML pipeline, write forecasts to `busyness_forecasts`, and smoke-test the backend API.

This SOP reflects the current Sprint 4 Data state:

- Forecast-v2 is the deployment path.
- V1 is legacy fallback only and must not be used as the normal deployment path.
- External feature ingestion is required before a production-style forecast-v2 run.
- O5 live DB 200-venue quality gate passed on 2026-07-08.
- ARIMA/LSTM remains deferred until enough production telemetry exists.

---

## 0. Deployment Rules

- Use forecast-v2 scripts, not V1 CSV staging imports.
- Do not re-run old notebook-driven SerpAPI/BestTime pipelines during deployment.
- Do not claim production-grade ML unless the quality gate passes on the target environment.
- Do not physically delete incident/report data during deployment checks.
- Treat V1 outputs as legacy risk only.

Current forecast-v2 files:

```text
Data+ML/test/7.6-7.11/external_feature_ingest.py
Data+ML/test/7.6-7.11/forecast_v2_feature_pipeline.py
Data+ML/test/7.6-7.11/forecast_v2_model.py
Data+ML/test/7.6-7.11/forecast_v2_writer.py
Data+ML/test/7.6-7.11/forecast_v2_quality_gate.py
Data+ML/test/7.6-7.11/output_live_200/
```

Current legacy V1 audit:

```text
Data+ML/test/6.28-7.3/output/forecast_v1_quality_gate_report.txt
```

V1 remains blocked due to a train/validation crossing key and is not the deployment path.

---

## 1. Server Preparation

From the project root:

```bash
cd /path/to/Group6_Summer-Project
```

Verify required tools:

```bash
docker --version
docker compose version
python3 --version
poetry --version
mysql --version
```

Python 3.11 is recommended for deployment. The local development virtualenv may use a newer Python, but CI Docker uses Python 3.11.

---

## 2. Environment Variables

Create backend `.env`:

```bash
cd backend
cp .env.example .env
```

Required runtime values:

```env
API_KEY=...
GOOGLE_MAPS_API_KEY=...
GEMINI_API_KEY=...
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=clearpath_app
DB_PASSWORD=clearpath_app
DB_NAME=clearpath
REDIS_URL=redis://127.0.0.1:6379/0
JWT_SECRET=...
PORT=5000
FLASK_ENV=production
DB_ENCRYPTION_CHECK=false
```

Notes:

- `MEDICAL_PROFILE_ENCRYPTION_KEY` is a legacy Fernet setting. Do not treat it as the current deployment blocker unless Backend reactivates that implementation.
- When backend is Dockerized later, DB/Redis hosts must change to `mysql` and `redis`.

Return to project root:

```bash
cd ..
```

---

## 3. Start MySQL and Redis

Current `docker-compose.yml` starts:

```text
clearpath-mysql       MySQL 8.4      localhost:3306
clearpath-redis       Redis 7        localhost:6379
clearpath-phpmyadmin  phpMyAdmin     localhost:8080
```

Start infrastructure:

```bash
docker compose up -d mysql redis phpmyadmin
docker compose ps
```

Wait for MySQL:

```bash
docker exec clearpath-mysql mysqladmin ping -h localhost -uclearpath_app -pclearpath_app
```

Do not add MySQL keyring flags or a `clearpath_mysql_keyring` volume unless the image startup options have been tested. Current minimal deployment keeps:

```env
DB_ENCRYPTION_CHECK=false
```

---

## 4. DB Migration and Seed Order

For a brand-new Docker volume, MySQL runs scripts under:

```text
docker/mysql/init/
```

Expected order:

```text
001_clearpath_schema.sql
002_add_busyness_unique_constraint.sql
003_add_user_profile_fields.sql
004_medical_profiles.sql
005_seed_venues.sql
006_seed_report_categories.sql
007_telemetry_audit_log.sql
```

For an existing volume, init scripts do not automatically re-run. Use the repeatable migration helper when available:

```bash
docker/mysql/apply_migrations.sh
```

If running SQL manually, run only the confirmed patch/seed file. Do not casually re-run `001_clearpath_schema.sql` on production without backup.

Deployment smoke checks:

```sql
SHOW TABLES;
SELECT COUNT(*) AS venues_count FROM venues;
SELECT COUNT(*) AS report_category_count FROM report_categories;
SELECT COUNT(*) AS forecast_count FROM busyness_forecasts;
SELECT COUNT(*) AS external_cache_count FROM external_context_cache;
```

Required table checks for current known gaps:

```sql
SHOW TABLES LIKE 'telemetry_audit_log';
SHOW TABLES LIKE 'venue_source_links';
```

If `telemetry_audit_log` or `venue_source_links` is missing, D3.1 live telemetry execute remains blocked.

---

## 5. Backend Startup

Install backend dependencies:

```bash
cd backend
poetry install
poetry run python src/app.py
```

Health check:

```bash
curl http://127.0.0.1:5000/api/v1/health
```

Current deployment limitation:

- Backend is not yet Dockerized.
- `docker-compose.yml` currently validates MySQL/Redis/phpMyAdmin only.
- Full backend container deployment is tracked separately in `docs/memory/Sprint3-4_execution-plan.md` as O12.

---

## 6. External Feature Ingest

Run external feature ingest before forecast-v2 feature generation. These commands fetch live/public sources and write to `external_context_cache`.

```bash
cd /path/to/Group6_Summer-Project
python Data+ML/test/7.6-7.11/external_feature_ingest.py --source weather --execute
python Data+ML/test/7.6-7.11/external_feature_ingest.py --source holiday --execute
python Data+ML/test/7.6-7.11/external_feature_ingest.py --source gbfs --execute
python Data+ML/test/7.6-7.11/external_feature_ingest.py --source mta_gtfs_rt --execute
```

Expected source status after a successful live run:

```text
weather_source = open_meteo
gbfs_source    = lyft_gbfs_2.3
mta_source     = gtfs_rt
```

MTA note:

- On 2026-07-08, anonymous MTA GTFS-RT request succeeded and cached `mta_source=gtfs_rt`.
- If the endpoint later requires a key, provide:

```bash
python Data+ML/test/7.6-7.11/external_feature_ingest.py \
  --source mta_gtfs_rt \
  --api-key-file /path/to/mta_api_key.txt \
  --execute
```

Verify cache:

```sql
SELECT context_type, request_key, valid_from, expires_at
FROM external_context_cache
ORDER BY valid_from DESC
LIMIT 10;
```

---

## 7. Forecast-v2 Pipeline

Run the live DB feature pipeline with an explicit venue count. The 200-venue run is the current validated gate.

```bash
python Data+ML/test/7.6-7.11/forecast_v2_feature_pipeline.py \
  --live-db \
  --n-synth-venues 200 \
  --output-dir Data+ML/test/7.6-7.11/output_live_200
```

Expected latest verified output:

```text
training rows   = 4,752
prediction rows = 2,400
prediction venues = 200
```

Then train/generate prediction curves:

```bash
python Data+ML/test/7.6-7.11/forecast_v2_model.py \
  --features Data+ML/test/7.6-7.11/output_live_200/forecast_v2_training_features.csv \
  --pred-features Data+ML/test/7.6-7.11/output_live_200/forecast_v2_prediction_features.csv \
  --output-dir Data+ML/test/7.6-7.11/output_live_200
```

Run the quality gate:

```bash
python Data+ML/test/7.6-7.11/forecast_v2_quality_gate.py \
  --output-dir Data+ML/test/7.6-7.11/output_live_200
```

Required pass conditions:

```text
OVERALL VERDICT: PASS
humidity_pct=-1 ratio = 0%
rolling window leakage gate = PASS
train/val split duplicate gate = PASS
external feature gate = PASS
12h curve gate = PASS
```

If the quality gate is `BLOCKED`, do not run writer `--execute`. Fix the gate first.

---

## 8. Write Forecast-v2 to DB

Dry-run first:

```bash
python Data+ML/test/7.6-7.11/forecast_v2_writer.py \
  --csv Data+ML/test/7.6-7.11/output_live_200/prediction_curve_v2.csv \
  --model-version forecast-v2 \
  --dry-run
```

Execute only after dry-run and quality gate pass:

```bash
python Data+ML/test/7.6-7.11/forecast_v2_writer.py \
  --csv Data+ML/test/7.6-7.11/output_live_200/prediction_curve_v2.csv \
  --model-version forecast-v2 \
  --execute
```

Verify:

```sql
SELECT model_version, COUNT(*) AS forecast_rows
FROM busyness_forecasts
GROUP BY model_version
ORDER BY forecast_rows DESC;

SELECT venue_id, forecast_for, predicted_score, predicted_level, model_version, generated_at
FROM busyness_forecasts
WHERE model_version = 'forecast-v2'
ORDER BY generated_at DESC
LIMIT 12;
```

---

## 9. API Smoke Tests

Backend health:

```bash
curl http://127.0.0.1:5000/api/v1/health
```

Venue forecast:

```bash
curl http://127.0.0.1:5000/api/v1/venues/seed-healthcare-bellevue-001/busyness/forecast
```

If the seed venue has no forecast rows, select a real venue from DB:

```sql
SELECT venue_id, COUNT(*) AS n
FROM busyness_forecasts
WHERE model_version = 'forecast-v2'
GROUP BY venue_id
ORDER BY n DESC
LIMIT 5;
```

Expected API behavior:

```text
model_version = forecast-v2
12 forecast points for latest generated batch
external_feature_status present when backend supports metadata
no 500 on missing/no_data venue
```

---

## 10. Rollback

Rollback forecast-v2 forecasts only:

```sql
DELETE FROM busyness_forecasts
WHERE model_version = 'forecast-v2';
```

Rollback external feature cache only if a bad ingest payload was written:

```sql
DELETE FROM external_context_cache
WHERE context_type IN (
  'weather_forecast',
  'public_holidays',
  'gbfs_station_status',
  'mta_realtime'
);
```

Do not delete Docker volumes unless intentionally rebuilding the full database:

```bash
# Avoid unless full rebuild is intended.
docker compose down -v
```

---

## 11. Legacy V1 Policy

Do not use V1 as the normal deployment path.

Legacy V1 files may remain for audit/backfill reference:

```text
Data+ML/test/6.28-7.3/output/prediction_curve_v1.csv
Data+ML/test/6.28-7.3/output/model_test_predictions_v1.csv
Data+ML/test/6.28-7.3/output/forecast_v1_quality_gate_report.txt
```

Known V1 risk:

```text
forecast-v1 quality gate = BLOCKED
reason = 1 train/val crossing key
Ridge val R2 = -0.058
```

Only use V1 for retrospective analysis or explicit fallback with risk noted.

---

## 12. Operations to Avoid

Do not run old generative workflows during deployment:

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

These scripts belong to historical data collection, legacy feature building, or separate telemetry work. The current deployment path is forecast-v2.

---

## 13. Final Deployment Checklist

Before merging or deploying:

- MySQL and Redis are healthy.
- Required init/migration scripts have been applied.
- `report_categories` is seeded.
- `external_context_cache` contains fresh weather/holiday/GBFS/MTA rows.
- Forecast-v2 live DB 200 run completed.
- `forecast_v2_quality_gate.py` returns PASS.
- `forecast_v2_writer.py --dry-run` succeeds.
- `forecast_v2_writer.py --execute` succeeds.
- Forecast API returns a 12-point curve.
- V1 is not presented as production model output.

