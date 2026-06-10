# BestTime Manhattan Minimal Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal, testable BestTime integration for Manhattan that can forecast one specific venue’s busyness and return nearby venue data suitable for a heatmap, with a local-only plaintext API-key smoke test.

**Architecture:** Keep the first slice narrow. Add one BestTime client wrapper, one dedicated Manhattan demo route, and one automated test path that mocks BestTime responses. The route will call BestTime’s new forecast endpoint for a single venue and the venue filter endpoint for a Manhattan area heatmap, then normalize both payloads into one response for the frontend.

**Tech Stack:** Flask, requests, Python 3.11, unittest/mock, BestTime API.

---

### Task 1: Add a dedicated BestTime client and Manhattan demo route

**Files:**
- Create: `Group6_Summer-Project/src/services/besttime_client.py`
- Create: `Group6_Summer-Project/src/api/besttime_manhattan.py`
- Create: `Group6_Summer-Project/tests/api/test_besttime_manhattan.py`
- Modify: `Group6_Summer-Project/src/app.py`
- Modify: `Group6_Summer-Project/pyproject.toml`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock, patch

from app import create_app


class BestTimeManhattanDemoTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    @patch("services.besttime_client.requests.get")
    @patch("services.besttime_client.requests.post")
    def test_manhattan_demo_route_returns_forecast_and_heatmap(self, mock_post, mock_get):
        mock_forecast = MagicMock()
        mock_forecast.raise_for_status.return_value = None
        mock_forecast.json.return_value = {
            "status": "OK",
            "venue_info": {
                "venue_id": "ven_demo_123",
                "venue_name": "Mount Sinai Hospital",
                "venue_address": "1468 Madison Ave, New York, NY 10029",
                "venue_lat": 40.7831,
                "venue_lng": -73.9712,
            },
            "analysis": [{"day_int": 2, "busy_hours": [8, 9, 10]}],
        }

        mock_heatmap = MagicMock()
        mock_heatmap.raise_for_status.return_value = None
        mock_heatmap.json.return_value = {
            "status": "OK",
            "venues_n": 1,
            "venues": [
                {
                    "venue_id": "ven_heat_001",
                    "venue_name": "Nearby Clinic",
                    "venue_lat": 40.784,
                    "venue_lng": -73.97,
                    "day_raw_whole": [20, 30, 40, 50, 60, 70, 80, 90, 100],
                }
            ],
        }

        mock_post.return_value = mock_forecast
        mock_get.return_value = mock_heatmap

        response = self.client.post(
            "/api/v1/integrations/besttime/manhattan/demo",
            json={
                "api_key_private": "pri_test_plaintext",
                "venue_name": "Mount Sinai Hospital",
                "venue_address": "1468 Madison Ave, New York, NY 10029",
                "lat": 40.7831,
                "lng": -73.9712,
                "radius": 2500,
                "day_int": 2,
                "hour_min": 8,
                "hour_max": 18,
                "types": "HOSPITAL,PHARMACY,DOCTOR",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["venue"]["forecast"]["venue_info"]["venue_id"], "ven_demo_123")
        self.assertEqual(payload["heatmap"]["venues_n"], 1)
        self.assertEqual(payload["region"], "Manhattan")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd Group6_Summer-Project
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: FAIL because `services.besttime_client` and the Manhattan route do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/services/besttime_client.py
import requests

BESTTIME_FORECAST_URL = "https://besttime.app/api/v1/forecasts"
BESTTIME_FILTER_URL = "https://besttime.app/api/v1/venues/filter"


def create_forecast(api_key_private: str, venue_name: str, venue_address: str) -> dict:
    response = requests.post(
        BESTTIME_FORECAST_URL,
        params={
            "api_key_private": api_key_private,
            "venue_name": venue_name,
            "venue_address": venue_address,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def filter_manhattan(api_key_private: str, lat: float, lng: float, radius: int, day_int: int, hour_min: int, hour_max: int, types: str) -> dict:
    response = requests.get(
        BESTTIME_FILTER_URL,
        params={
            "api_key_private": api_key_private,
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "day_int": day_int,
            "hour_min": hour_min,
            "hour_max": hour_max,
            "types": types,
            "foot_traffic": "both",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
```

```python
# src/api/besttime_manhattan.py
from flask import Blueprint, current_app, jsonify, request

from services.besttime_client import create_forecast, filter_manhattan

bp = Blueprint("besttime_manhattan", __name__)


@bp.post("/api/v1/integrations/besttime/manhattan/demo")
def manhattan_demo():
    payload = request.get_json(silent=True) or {}
    api_key_private = payload.get("api_key_private") or current_app.config.get("BESTTIME_API_KEY", "")
    if not api_key_private:
        return jsonify({"error": "BESTTIME_API_KEY is required."}), 400

    venue_name = payload.get("venue_name", "Mount Sinai Hospital")
    venue_address = payload.get("venue_address", "1468 Madison Ave, New York, NY 10029")
    lat = float(payload.get("lat", 40.7831))
    lng = float(payload.get("lng", -73.9712))
    radius = int(payload.get("radius", 2500))
    day_int = int(payload.get("day_int", 2))
    hour_min = int(payload.get("hour_min", 8))
    hour_max = int(payload.get("hour_max", 18))
    types = payload.get("types", "HOSPITAL,PHARMACY,DOCTOR")

    forecast = create_forecast(api_key_private, venue_name, venue_address)
    heatmap = filter_manhattan(api_key_private, lat, lng, radius, day_int, hour_min, hour_max, types)

    return jsonify(
        {
            "region": "Manhattan",
            "venue": {
                "name": venue_name,
                "address": venue_address,
                "forecast": forecast,
            },
            "heatmap": heatmap,
        }
    )
```

```python
# src/app.py
from api.besttime_manhattan import bp as besttime_manhattan_bp

# register the blueprint with the existing app
app.register_blueprint(besttime_manhattan_bp)
```

Add `requests` to `pyproject.toml` so the client can make outbound HTTP calls.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd Group6_Summer-Project
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS, with the route returning both the single-venue forecast and the Manhattan heatmap payload.

- [ ] **Step 5: Commit**

```bash
git add Group6_Summer-Project/src/services/besttime_client.py Group6_Summer-Project/src/api/besttime_manhattan.py Group6_Summer-Project/src/app.py Group6_Summer-Project/pyproject.toml Group6_Summer-Project/tests/api/test_besttime_manhattan.py
git commit -m "feat: add BestTime Manhattan demo endpoint"
```

### Task 2: Add a plaintext API-key smoke-test note for local verification

**Files:**
- Create: `docs/besttime/manhattan-smoke-test.md`

- [ ] **Step 1: Write the smoke-test note**

```markdown
## Manhattan smoke test

The endpoint must accept a literal `api_key_private` in the request body for local verification only. The manual curl command below uses a non-secret demo string so the flow is explicit without introducing a committed secret.
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
test -f docs/besttime/manhattan-smoke-test.md
```

Expected: FAIL because the documentation file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```markdown
curl -sS -X POST "http://127.0.0.1:5000/api/v1/integrations/besttime/manhattan/demo" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key_private": "pri_local_demo_key",
    "venue_name": "Mount Sinai Hospital",
    "venue_address": "1468 Madison Ave, New York, NY 10029",
    "lat": 40.7831,
    "lng": -73.9712,
    "radius": 2500,
    "day_int": 2,
    "hour_min": 8,
    "hour_max": 18,
    "types": "HOSPITAL,PHARMACY,DOCTOR"
  }' | jq '.region, .venue.forecast.venue_info.venue_id, .heatmap.venues_n'
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
test -f docs/besttime/manhattan-smoke-test.md
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/besttime/manhattan-smoke-test.md
git commit -m "docs: add BestTime Manhattan smoke test"
```

## Self-Review

The plan covers the Manhattan-specific forecast path, the heatmap path, and the plaintext request-body smoke test. The only intentional scope limit is that this is a single demo endpoint, not a generalized BestTime abstraction for all boroughs or all venue classes.
