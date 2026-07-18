# ClearPath V2 deployment SOP

Last updated: 2026-07-18

## Deploy

From the project root, start MySQL and Redis. Set production values for
`API_KEY`, database credentials, and external-service keys before starting the
API.

```bash
docker compose up -d mysql redis

cd backend
python src/app.py
```

In a second terminal, refresh the current traffic context and publish V2's
12-hour curve. `--year 2025` identifies the NYC SODA source data only; current
windows use the actual pipeline run time.

```bash
cd /path/to/Group6_Summer-Project

.venv-1/bin/python Data+ML/test/6.15-6.20/src/busyness_ingestion.py \
  --year 2025 \
  --model-version nyc_traffic_context_v1

cd Data+ML/test/7.13-7.18
../../../.venv-1/bin/python forecast_v2_pattern.py \
  --labels output/serpapi_v2_labels_20260716/serpapi_popular_times_weak_labels.csv \
  --legacy-labels output/serpapi_repeat_audit/legacy_cached_baseline.csv \
  --output-dir output/v2_pattern_traffic_latest \
  --publish
```

The traffic script preserves `nyc_traffic_baseline_v1` for V2 training,
refreshes only `nyc_traffic_context_v1`, and removes only expired context rows.
The V2 script upserts its output as `model_version='forecast-v2'` in
`busyness_forecasts`.

Deploy the mobile client with its API base URL pointing at this API. The map's
initial request is `GET /api/v1/venues` with no filters.

## Basic post-deploy check

Run this against the deployed API.  It fails if the endpoint is unavailable,
if its `count` does not match the returned `items`, or if it returns five or
fewer venues.  This catches the DB-to-mock fallback and accidental list
truncation that would make the frontend show only five venues.

```bash
export CLEARPATH_API_URL='http://127.0.0.1:5000'
export API_KEY='your-deployed-api-key'

curl -fsS \
  -H "X-API-Key: $API_KEY" \
  "$CLEARPATH_API_URL/api/v1/venues" \
  | python3 -c 'import json, sys; payload = json.load(sys.stdin); count = payload.get("count"); items = payload.get("items", []); assert isinstance(count, int), "missing integer count"; assert count == len(items), f"count={count}, items={len(items)}"; assert count > 5, f"only {count} venues returned"; print(f"PASS: {count} venues returned")'
```

Then open the mobile map with no filters.  Its marker count must match the
printed API count.  If it does not, check the mobile client API base URL and
the active filters before changing the model or database.

## Busyness checks

Use a known V2 venue from the just-written curve (the second CSV line contains
one) and confirm both current traffic context and the 12-hour V2 forecast.

```bash
cd /path/to/Group6_Summer-Project/Data+ML/test/7.13-7.18
VENUE_ID=$(sed -n '2p' output/v2_pattern_traffic_latest/prediction_curve_v2_pattern.csv | cut -d, -f1)

curl -fsS -H "X-API-Key: $API_KEY" \
  "$CLEARPATH_API_URL/api/v1/venues/$VENUE_ID/busyness" \
  | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["busyness"]["data_mode"] == "live"; print("PASS: current traffic context")'

curl -fsS -H "X-API-Key: $API_KEY" \
  "$CLEARPATH_API_URL/api/v1/venues/$VENUE_ID/busyness/forecast" \
  | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["forecast_source"] == "busyness_forecasts"; assert p["model_version"] == "forecast-v2"; assert len(p["forecast"]) == 12; print("PASS: V2 12-hour forecast")'
```
