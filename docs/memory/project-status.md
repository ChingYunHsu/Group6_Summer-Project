# ClearPath Current Project Status

> Updated: 2026-06-09 | openapi.yaml v1.4.0 | grill-with-docs decisions frozen

---

## Project Overview

- **Project Name**: ClearPath — Manhattan Accessibility Navigation
- **Tech Stack**: Flask + MySQL + React Native
- **Branches**: `main` (production), `alex` (development)
- **DB**: MySQL `clearpath` schema, 19 tables

## Database Connection

| Parameter | Value |
|-----------|-------|
| Host | 127.0.0.1:3306 |
| User | clearpath_app |
| Password | clearpath_app |
| Database | clearpath |

---

## Database Schema Status (18 tables)

### Completed Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `venues` | ~3,479 | Unified POI table (includes district, language, accessibility, warnings, weather_risk) |
| `venue_source_links` | ~3,479 | Data source tracking (1:1 with venues) |
| `restroom_profiles` | 476 | Restroom details |
| `healthcare_profiles` | 1,228 | Healthcare facility details |
| `emergency_assets` | ~3,279 | AED devices (with unique constraint) |
| `pedestrian_ramps` | 23,625 | Accessibility ramps (with district) |
| `venue_accessibility` | 0 | Venue accessibility details (pending) |
| `venue_language` | 63 | Venue multilingual support |
| `venue_warnings` | 0 | Venue warnings (pending) |
| `external_context_cache` | 1 | Weather API cache |
| `users` | 0 | Account system base (D1: email + password) |
| `user_favorite_venues` | 0 | Cross-device favorite sync |
| `notification_preferences` | 0 | Quiet hours + Push subscriptions |
| `report_categories` | 8 | Report category dictionary (D8: filter by venue type) |
| `busyness_forecasts` | 0 | 12-hour time-series forecast (D4: quiet/moderate/busy) |
| `venue_embeddings` | 0 | RAG vector storage (D9: MySQL JSON) |

### Modified Tables

| Table | Modification | Status |
|-------|-------------|--------|
| `user_reports` | ✅ Added `user_id` FK, DROP `reported_by`, `issue_type` → VARCHAR + FK | 2026-06-09 |
| `report_confirmations` | ✅ Added `user_id` FK + `UNIQUE (report_id, user_id)` | 2026-06-09 |
| `busyness_scores` | ✅ ENUM changed to `quiet/moderate/busy`, nullable | 2026-06-09 |

---

## venues Table Columns: 24

```
venue_id, venue_type, name, latitude, longitude, borough, district,
language_tags, primary_language, secondary_language, accessible_status,
accessibility_features, active_warning, open_now, address, phone, website,
opening_hours, photos, rating, weather_risk, source_confidence,
created_at, updated_at
```

---

## ETL Pipeline Status

- **Notebook**: `Data+ML/test/6.2-6.5_DB/database_build.ipynb` (49 cells, 24 code cells)
- **Schema**: `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql`
- **Data Sources**: `data_source/` (outside repo), managed by `clearpath_sources.json`
- **MySQL Docker**: `docker-compose.yml` at repo root, init: `docker/mysql/init/001_clearpath_schema.sql`
- **District Zoning**: ✅ Implemented (venues + pedestrian_ramps)
- **Weather API**: ✅ NWS integration, 1 cached entry
- **Venue Language**: ✅ LASS data, 63 matched

### ETL Row Counts (2026-06-05)

| Data Source | Manhattan | After ETL |
|-------------|-----------|-----------|
| NYC Public Restrooms | 358 | 349 imported |
| Parks Toilets | 129 | 127 imported |
| OSM Healthcare | 900 | 900 imported |
| NYS Health | 454 | 431 imported |
| AED Inventory | 3,393 | 3,279 imported (dedup) |
| Pedestrian Ramps | 23,625 | 23,625 imported |
| Weather (NWS API) | — | 1 cached |
| Venue Language (LASS) | 442 | 63 matched |

---

## OpenAPI Status (v1.4.0) — Contract ready, backend pending

- **Endpoints**: 20+
- **New Tags**: Busyness, Insights, Chatbot
- **Coverage**: ~90%
- **Gap Analysis**: `docs/memory/openapi_gap_finalacceptcriteria.md`

### OpenAPI Contract Status (YAML defined)

| Module | Endpoints | Contract | Backend |
|--------|-----------|----------|---------|
| Venues | `GET /venues`, `GET /venues/{id}` | ✅ | ✅ |
| Busyness | `GET /venues/{id}/busyness`, `GET /venues/{id}/busyness/forecast` | ✅ | ❌ No data source |
| Reports | `GET/POST /reports`, `POST /reports/{id}/confirmations` | ✅ | ❌ Missing users table |
| Insights | `GET /insights` | ✅ | ✅ |
| Chatbot | `POST /chatbot` | ✅ | ❌ RAG not implemented |
| User | profile, settings, languages, favourites, SOS, notification-prefs, account delete, medical-passport | ✅ | ❌ Missing users table |
| Routes | options, detail | ✅ | ✅ |
| Realtime | SSE map-updates | ✅ | ✅ |

---

## Sprint Pipeline Status

| Completed | Pending |
|-----------|---------|
| ✅ 19-table Schema | ❌ JWT Auth (backend impl) |
| ✅ ETL data ingestion | ❌ Profile CRUD (backend impl) |
| ✅ Mock data (v1.4.0) | ❌ Real-time telemetry pipeline |
| ✅ Weather API integration | ❌ 12-hour ML forecast (table ready) |
| ✅ Venue Language ETL | ❌ Report TTL (2h) |
| ✅ Schema sync mechanism (test→file) | ❌ Cascade delete API |
| ✅ District Zoning (venues + ramps) | ❌ Gemini RAG (table ready) |
| ✅ emergency_assets unique constraint | ❌ User auth system (users table ready) |
| ✅ OpenAPI v1.4.0 contract (20+ endpoints) | ❌ Docker schema sync (test→docker) |
| ✅ users + favorites + notifications tables | |
| ✅ report_categories + ALTER user_reports/confirmations | |
| ✅ busyness_forecasts + venue_embeddings tables | |

**Status Legend**: "Table ready" = DDL complete, awaiting backend code implementation

### Backend API Endpoints (Flask implementation, not DDL)

| Endpoint | Purpose | Dependency | Status |
|----------|---------|------------|--------|
| `POST /auth/register` | Email + password + full name registration | users table | ✅ Ready |
| `POST /auth/login` | Email + password → JWT | users table | ✅ Ready |
| `POST /auth/forgot-password` | Send reset link | users table | ✅ Ready |
| `POST /auth/reset-password` | Token + new password | users table | ✅ Ready |
| `POST /reports` | Submit report (login required) | users + report_categories tables | ✅ Ready |
| `POST /reports/{id}/confirmations` | Confirm report (login required) | users + UNIQUE constraint | ✅ Ready |
| `GET /venues/{id}/busyness/forecast` | 12h forecast | busyness_forecasts table | ✅ Ready |
| `POST /chatbot` | RAG query | venue_embeddings table | ✅ Ready |

---

## File Structure

```
docs/memory/
├── project-status.md          ← This file
├── project-issues.md          ← Current issues
├── execution-plan.md          ← Execution plan (DB schema focus)
├── context-terms.md           ← Domain glossary + 10 frozen decisions
├── openapi_gap_finalacceptcriteria.md  ← Gap analysis for review
└── MEMORY.md                  ← Index

src/
├── app.py              # Flask application entry
├── mock_data.py        # Mock data (v1.4.0)
└── api/                # API routes

Data+ML/test/6.2-6.5_DB/
├── database_build.ipynb      # ETL pipeline
├── 001_clearpath_schema.sql  # Database schema
├── README.md                 # Operating instructions
└── clearpath_sources.json    # Data source manifest
```
