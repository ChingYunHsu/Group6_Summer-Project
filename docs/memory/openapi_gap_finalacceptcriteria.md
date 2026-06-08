# OpenAPI vs Requirements — Gap Status (v1.4.0)

> Compared files: `openapi.yaml` (v1.4.0) + `src/mock_data.py` vs `(Final)ClearPathfaeturesandcriteria.docx`
> Analysis date: 2026-06-08 | Updated: 2026-06-09 (v1.4.0 full reconciliation)

---

## 1. Resolved Conflicts

### 1.1 category vs venue_type — No Conflict
- `category` in the requirements doc is a frontend UI display term
- OpenAPI and DB both use `venue_type` consistently
- API layer mapping handles the translation; no change needed
- **Note**: OpenAPI enum uses `emergencyasset` (no underscore), DB uses `emergency_asset` (with underscore) — separate YAML-DB alignment issue, tracked elsewhere

### 1.2 Report Submission Authentication — Resolved
- OpenAPI `POST /reports` and `POST /reports/{id}/confirmations` both use `BearerAuth` ✅
- US-04: unauthenticated guests are **intercepted** with **Login Required modal**
- "Submit Anonymous Report" means **anonymized after submission**, not anonymous submission
- **Team decision (applied in YAML)**: `ReportConfirmationRequest` now requires `user_id` (L1082); `anonymous` retained as optional display flag (L1065-1067)

### 1.3 Medical ID / Emergency Contacts — Removed from API (Team Decision)
- `GET /user/medical-id` and `GET /user/emergency-contacts` are **not in OpenAPI** ✅
- Medical data stays **local on the device** for privacy
- SOS panic button works without server-side medical data
- `UserSettings.show_medical_id_on_sos` is a device-local toggle, not a server endpoint

### 1.4 Report Confirmation Action Enum — Accepted
- US-06 specifies 2 buttons: **[Confirm]** and **[Resolve]**
- OpenAPI defines 5 enum values: `still_here`, `resolved`, `not_sure`, `still_out_of_order`, `open_now`
- Keep the 5 API values (more flexible), frontend shows only Confirm/Resolve as primary actions

### 1.5 Busyness Forecast — Fully Resolved (v1.4.0)
- **OpenAPI**: `Venue.busyness_forecast_12h` array + dedicated endpoints:
  - `GET /venues/{id}/busyness` — realtime snapshot (L141)
  - `GET /venues/{id}/busyness/forecast` — 12h forecast + best_time_to_go_today (L174)
- **DB**: `VenueBusyness` schema no longer has `forecast_4h`/`forecast_8h` (removed in v1.4.0)
- **Resolution**: Create independent `busyness_forecasts` table (pending DB work)

### 1.6 phone_number vs phone — Resolved
- DB: `phone` | OpenAPI Venue: `phone` | OpenAPI UserProfile: `phone` — all aligned ✅

### 1.7 Web Read-Only Restriction — Accepted as-is
- Requirements: Web platform must be **Read-Only**
- OpenAPI: all endpoints treat Mobile and Web identically
- Frontend controls UI visibility; API does not distinguish by platform (acceptable)

---

## 2. All Previous Gaps — Now Resolved (v1.4.0)

| # | Old Gap | Priority | Resolution in v1.4.0 |
|---|---------|----------|---------------------|
| 1 | Busyness realtime + forecast endpoint missing | Must Have | ✅ `GET /venues/{id}/busyness` + `/busyness/forecast` added (L141-205) |
| 2 | AI Chatbot / RAG endpoint missing | Must Have | ✅ `POST /api/v1/chatbot` added (L349-380) |
| 3 | Account Delete endpoint missing | Should Have | ✅ `DELETE /api/v1/user/account` added (L599-618) |
| 4 | Favourites CRUD (PUT/DELETE missing) | Should Have | ✅ `POST /user/favourites` (L465) + `DELETE /user/favourites/{venue_id}` (L491) added |
| 5 | PDF Medical Passport endpoint missing | Should Have | ✅ `GET /user/medical-passport` added (L620-646) |
| 6 | Insights tagged under Reports | Minor | ✅ Re-tagged to `Insights` (L325); `timeframe` param added |
| 7 | issue_type enum missing 2 values | Must Have | ✅ Now 8 values: added `ramp_blocked`, `closed_early` (L1047-1055) |
| 8 | `anonymous` field kept but login required | Minor | ✅ Kept as optional display flag with description (L1065-1067) |
| 9 | Missing `user_id` on confirmations | Must Have | ✅ `ReportConfirmationRequest.user_id` now required (L1082-1093) |
| 10 | GET /reports no filtering params | Must Have | ✅ `venue_id`, `issue_type`, `status` params added (L212-237) |
| 11 | Report.status missing `expired` | P2 | ✅ Now `[active, resolved, expired]` (L1151) |
| 12 | VenueBusyness stale forecast_4h/8h | P2 | ✅ Removed from VenueBusyness (L944-961) |
| 13 | RouteOption missing per-mode breakdown | P2 | ✅ `summary_by_mode` + `RouteModeSummary` added (L1611-1634) |

---

## 3. Current Remaining Issues (YAML vs mock vs Criteria)

### 3.1 ⚠️ mock_data.py Alignment Gaps

| Item | mock_data.py | OpenAPI v1.4.0 | Status |
|------|-------------|----------------|--------|
| `REPORT_CONFIRMATION_TEMPLATE` | Missing `user_id` | Required field (L1082) | ⚠️ Gap |
| `INSIGHTS_DASHBOARD.district` | `"Midtown East"` (title case) | Enum lowercase `midtown_east` | ⚠️ Mismatch |
| `FAVOURITE_CREATE_TEMPLATE` | Present | `FavouriteCreateRequest` schema | ✅ Aligned |
| `DELETE_ACCOUNT_RESPONSE` | Present | `DeleteAccountResponse` schema | ✅ Aligned |
| `MEDICAL_PASSPORT_RESPONSE` | Present | `MedicalPassportResponse` schema | ✅ Aligned |
| `CHATBOT_RESPONSE` | Present | `ChatbotResponse` schema | ✅ Aligned |
| `VENUE_FORECASTS` | Present | `VenueBusynessForecastResponse` | ✅ Aligned |
| `ROUTE_OPTIONS.summary_by_mode` | Present | `RouteOptionsResponse.summary_by_mode` | ✅ Aligned |
| `REPORTS[3].status` | `"expired"` | `Report.status` enum includes `expired` | ✅ Aligned |
| `REPORTS[2].issue_type` | `"ramp_blocked"` | `ReportSubmission` includes `ramp_blocked` | ✅ Aligned |

### 3.2 ⚠️ busyness_forecasts DB Table — Pending

- OpenAPI defines `GET /venues/{id}/busyness/forecast` returning 12h forecast
- mock_data.py provides static forecast data
- **DB `busyness_scores` table has 0 rows**; no `busyness_forecasts` table exists yet
- API contract is complete; data source is not

---

## 4. Coverage Summary (v1.4.0)

| Module | Coverage | Notes |
|---|---|---|
| Find (Venue Discovery) | ~95% | venue_type, language, accessibility, structured hours, photos, ratings all covered |
| Report (Community Reports) | ~90% | 8 issue types, filtering, expired status, user_id auth — all in YAML |
| Predict (Busyness Forecast) | ~85% | Endpoints + schema complete; DB table pending |
| Navigate (Routing) | ~90% | step-free mode, per-mode breakdown (transit/walk/drive) |
| Connect (User/Safety) | ~90% | SOS, notification prefs, account delete, favourites CRUD, medical passport |
| Assist (Chatbot) | ~80% | Chatbot endpoint + schema complete; RAG pipeline not yet implemented |
| **Overall** | **~90%** | API contract nearly complete; main gap is DB busyness data pipeline |

---

## 5. Priority Fix Items (v1.4.0)

### P0 — Data Pipeline
1. **Create `busyness_forecasts` table** — DB data source for forecast endpoint

### P1 — Alignment
2. **Fix mock_data.py** — add `user_id` to `REPORT_CONFIRMATION_TEMPLATE`; fix `INSIGHTS_DASHBOARD.district` case
