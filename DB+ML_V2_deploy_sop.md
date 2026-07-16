# ClearPath V2 deployment SOP

Last updated: 2026-07-16

## Deploy

From the project root, start the backing services and API.  Set the production
values for `API_KEY`, database credentials, and any external-service keys in
the deployment environment before starting the API.

```bash
docker compose up -d mysql redis

cd backend
python src/app.py
```

Deploy the mobile client with its API base URL pointing at this API.  The map's
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
