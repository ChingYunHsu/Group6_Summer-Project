---
name: openapi-vs-schema-gap
description: "OpenAPI vs Schema gap analysis — what YAML has that DB lacks, and vice versa. For backend alignment."
metadata: 
  node_type: memory
  originSessionId: 7b932f05-f9c3-4325-b4b3-931164d7f61e
---

# OpenAPI vs Database Schema Gap Analysis

## Current State (2026-06-07)

- **OpenAPI v1.1.0**: 14 endpoints, 25 schema objects
- **Schema**: 13 tables (MySQL)
- **Final Requirements**: 14 user stories, 57 acceptance criteria

## Score: OpenAPI 65/100, Schema 50/100

OpenAPI is ~1 Sprint ahead of Schema.

---

## What OpenAPI Has That Schema Lacks

| OpenAPI Definition | Required Schema Table | Priority |
|---|---|---|
| `UserProfile` schema | `users` table | P0 |
| `Favourite` schema + `GET /favourites` | `user_favorite_venues` table | P1 |
| `LanguageOption` (native + English names) | `language_options` dictionary | P1 |
| `busyness_forecast_12h[]` (12-point array) | `busyness_forecasts` table | P1 |
| `is_favourite` on Venue | Needs favourites table JOIN | P1 |
| `forecast_mode` (live/predicted) | No DB column exists | P2 |
| `supported_services` on Venue | No DB column exists | P2 |

## What Schema Has That OpenAPI Lacks

| Schema Table | Status | Note |
|---|---|---|
| `venue_warnings` | Not exposed | May be inlined into Venue response |
| `emergency_assets` | Not exposed | AED data, may not need endpoint |
| `pedestrian_ramps` | Not exposed | Accessibility data |
| `venue_source_links` | Internal only | RAG source tracking |

## Gaps in Both (Final Requires, Neither Has)

| Missing Item | Impact | Priority |
|---|---|---|
| `users` table | Cannot authenticate | P0 |
| `user_reports.user_id` | Anonymous reports violate Final | P0 |
| `report_confirmations.user_id` | No duplicate vote prevention | P0 |
| `notification_preferences` table | No quiet hours / push alerts | P1 |
| `busyness_forecasts` table | 12h chart uses fake data | P1 |
| `report_categories` dictionary | ENUM changes require migration | P2 |
| `users.deleted_at` | No soft delete for account removal | P2 |

## Conflicts Between OpenAPI and Final

| Conflict | OpenAPI Says | Final Says | Action |
|---|---|---|---|
| Medical ID endpoint | `GET /api/v1/user/medical-id` exists | Medical data must be local-only | **Remove endpoint** |
| Emergency contacts endpoint | `GET /api/v1/user/emergency-contacts` exists | Contacts must be local-only | **Remove endpoint** |
| Report submission | No `security` on `POST /reports` | Login required to submit | **Add security** |
| Report confirmation | No user identification | Login required, dedup per user | **Add user_id** |
| Busyness levels | `quiet/moderate/busy` (3 levels) | Needs 4th level confirmation | **Align** |

---

## Recommended Backend Sprint Plan

### Sprint 1: Database Foundation
1. Create `users` table (auth_subject, email, display_name, preferred_language, account_status, deleted_at)
2. Create `user_favorite_venues` table (user_id, venue_id, unique constraint)
3. Create `busyness_forecasts` table (venue_id, forecast_for, predicted_score, predicted_level, model_version)

### Sprint 2: Report Auth
1. Add `user_id` column to `user_reports` (NOT NULL, FK to users)
2. Drop `anonymous` and `reported_by` columns
3. Add `user_id` column to `report_confirmations` (NOT NULL, unique constraint with report_id)
4. Add JWT/auth middleware to `POST /reports` and `POST /confirmations`

### Sprint 3: OpenAPI Alignment
1. Remove `GET /api/v1/user/medical-id` endpoint + `MedicalId` schema
2. Remove `GET /api/v1/user/emergency-contacts` endpoint + `EmergencyContact` schema
3. Add `security: [BearerAuth]` to report endpoints
4. Create `notification_preferences` table
5. Add `DELETE /api/v1/account` endpoint

### Sprint 4: Polish
1. Create `report_categories` dictionary table
2. Add `forecast_mode` and `supported_services` to venues
3. Sync Data+ML schema with docker/mysql schema
4. Update mock data and ETL validation

---

## Field Name Mismatches

| OpenAPI Field | Schema Column | Resolution |
|---|---|---|
| `phone_number` | `phone` | Backend maps |
| `busyness_level` (quiet/moderate/busy) | `level` (low/medium/high/unknown) | Unify naming |
| `issue_type` (6 values) | `issue_type` (6 values) | Same, but Final wants different set |

---

## Related Memories
- [[final-requirements-database-impact]] — Full requirements impact analysis
- [[pipeline-requirements]] — Sprint 2-4 Backend/Data pipeline needs

---

## Historical Baseline Consolidation (2026-06-02 to 2026-06-03)

The detailed bilingual analyses remain available at:

- `Data+ML/test/6.2-6.5_DB/api_schema_gap_analysis_en.md`
- `Data+ML/test/6.2-6.5_DB/[CN]api_schema_gap_analysis_cn.md`

They compared the early API mock/contract with the database schema and proposed
schema additions for:

- venue photos, rating, weather risk, language, accessibility, and warnings;
- report description, photos, expiry, reporter metadata, and language;
- confirmation language;
- busyness forecast fields;
- `venue_accessibility`, `venue_language`, and `venue_warnings`.

The 2026-06-03 implementation summary reports that these schema changes were
applied at that time. The remaining API-layer responsibilities were:

| API responsibility | Database source |
|---|---|
| Rename `accuracy_meters` to `accuracy_m` | `venues.accuracy_meters` or query result |
| Resolve API `source` | `venue_source_links.source_name` / source confidence |
| Compute `open_now` | `opening_hours` plus current time |
| Compute `busyness_color` | busyness score/level |
| Aggregate confirmation count/latest action | `report_confirmations` |
| Aggregate live report count | active `user_reports` |
| Derive badge text | confirmation/report state |

### Current Interpretation

These historical documents are evidence of the earlier contract, not the
current source of truth:

- `phone_number` was later standardized to `phone`.
- `supported_services` remains an API-computed field.
- scalar `forecast_4h` and `forecast_8h` were later removed; current Final
  requirements need a proper time-series forecast model.
- historical anonymous reporter fields do not satisfy the Final requirement
  that reports and confirmations are tied to authenticated users.
- server-side medical Profile storage proposed by older pipeline work is
  superseded by the Final privacy boundary.

Use the current sections above and
`final-requirements-database-impact.md` when implementing new backend work.
