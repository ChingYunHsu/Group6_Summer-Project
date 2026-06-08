# OpenAPI vs Requirements Document — Coverage & Conflict Analysis (Final)

> Compared files: `openapi.yaml` (v1.1.0) vs `(Final)ClearPathfaeturesandcriteria.docx`
> Analysis date: 2026-06-08 | Updated: 2026-06-08 (team decisions applied)

---

## 1. Resolved "False Conflicts"

The following issues were reviewed and confirmed **not to be conflicts**:

### 1.1 category vs venue_type — No Conflict
- `category` in the requirements doc is a frontend UI display term
- OpenAPI and DB both use `venue_type` consistently
- API layer mapping handles the translation; no change needed


### 1.2 Report Submission Authentication — No Conflict
- OpenAPI `POST /reports` and `POST /reports/{id}/confirmations` both use `BearerAuth` ✅
- US-04 Acceptance Criterion #1: unauthenticated guests are **intercepted** and shown a **Login Required modal**
- "Submit Anonymous Report" means **anonymized after submission** (US-05 #3: "strictly obfuscate all personal identifying metadata"), **not** anonymous submission without login
- **Team decision**: `user_reports` adds `user_id` FK, removes `anonymous`/`reported_by`; `report_confirmations` adds `user_id` + unique constraint `(report_id, user_id)`

### 1.3 Medical ID / Emergency Contacts — Removed from API (Team Decision)
- **Decision**: `GET /user/medical-id` and `GET /user/emergency-contacts` are **removed** from the backend API
- **Rationale**: Medical and emergency contact data stays **local on the device** for privacy
- **Impact on US-10**: SOS panic button still works (triggers emergency call + location share), but does not require server-side medical data storage
- **OpenAPI action**: Delete `medical-id` and `emergency-contacts` endpoints; UserProfile schema contains no medical fields

### 1.4 Report Confirmation Action Enum — Minor Alignment Needed
- US-06 specifies 2 buttons: **[Confirm]** and **[Resolve]**
- OpenAPI defines 5 enum values: `still_here`, `resolved`, `not_sure`, `still_out_of_order`, `open_now`
- Recommendation: keep the 5 API values (more flexible), frontend shows only Confirm/Resolve as primary actions

---

## 2. Confirmed Conflicts

### 2.1 12-Hour Busyness Forecast — DB Does Not Match API

| Layer | Current State |
|---|---|
| OpenAPI | `Venue.busyness_forecast_12h` — array of 12 `{offset_hours, percent, level}` objects ✅ |
| DB | Only `forecast_1h` (INT); `forecast_4h/8h` already dropped |
| Frontend (US-07) | Requires 12h bar chart + lowest-value highlight ("Best time to go today") |

**Resolution**: ~~Add a JSON column~~ → **Create independent `busyness_forecasts` table**.

> ~~JSON 列方案被否决：无法按时间点索引、ML pipeline 写入困难、无法追踪模型版本、历史预测不可覆盖。~~

```sql
CREATE TABLE busyness_forecasts (
  forecast_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  forecast_for DATETIME NOT NULL,            -- 预测的目标时间点
  predicted_score TINYINT UNSIGNED NOT NULL,  -- 0-100
  predicted_level ENUM('quiet','moderate','busy') NOT NULL,
  estimated_wait_minutes INT UNSIGNED,
  model_version VARCHAR(64) NOT NULL,
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_forecast (venue_id, forecast_for, model_version),
  INDEX idx_forecast_venue_time (venue_id, forecast_for),
  CONSTRAINT fk_forecast_venue FOREIGN KEY (venue_id)
    REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

**职责分离**：
- `busyness_scores` → 实时观测（当前时刻拥挤度，保留 `forecast_1h` 用于快速查询）
- `busyness_forecasts` → 未来 12h 时序预测（ML pipeline 写入，支持模型版本追踪）

**API 查询**：`WHERE venue_id = ? AND forecast_for >= NOW() ORDER BY forecast_for LIMIT 12`，直接返回 12 个时间点。

**优势**：可按时间点索引、ML pipeline 单行 INSERT、支持多模型版本共存、历史预测可追溯。

### 2.2 phone_number vs phone — Venue Schema Naming Inconsistency

| Location | Field Name |
|---|---|
| DB | `phone` |
| OpenAPI Venue | `phone_number` |
| OpenAPI UserProfile | `phone` |

**Resolution**: Rename `phone_number` to `phone` in the OpenAPI Venue schema to align with DB and UserProfile.

### 2.3 Web Read-Only Restriction — Not Reflected in API

- Requirements (US-04/05/06): Web platform must be **Read-Only** — hide submit/confirm/resolve buttons
- OpenAPI: all endpoints treat Mobile and Web identically
- **Current approach**: frontend controls UI visibility; API does not distinguish by platform (acceptable)

---

## 3. OpenAPI Gaps (Required by Document but Not Covered)

| Requirement | Priority | OpenAPI Status | Recommendation |
|---|---|---|---|
| **US-08** Busyness alert notification settings | Must Have | ❌ No endpoint | Add `GET/PUT /user/notification-preferences` |
| **US-09** Step-free route filtering | Must Have | ⚠️ Routes exist but missing accessibility mode | Add `accessibility_mode` field to RouteOption |
| **US-10** SOS panic button | Must Have | ❌ No endpoint | Add `POST /user/sos` (medical data stays local on device) |
| Real-time map updates (WebSocket/SSE) | Must Have | ❌ REST only | Consider `/ws/map-updates` or SSE endpoint |
| Advanced filter venue_type parameter | Must Have | ⚠️ Missing | Add `venue_type` query param to `GET /venues` |
| Structured opening hours | Should Have | ⚠️ String only | Consider structured object format |

---

## 4. Known Issues from Memory Files

| Issue | Status | Impact |
|---|---|---|
| Docker schema out of sync with test schema | Pending fix | Schema inconsistency on deployment |
| forecast_4h/8h dropped from DB | Resolved | Need new `busyness_forecasts` table (not JSON column) |
| emergency_assets unique constraint | Fixed | API layer does not expose emergency_assets endpoint |
| busyness_scores table has 0 rows | Unresolved | API fully defined but no actual data source |

---

## 5. Coverage Summary

| Module | Coverage | Notes |
|---|---|---|
| Find (Venue Discovery) | 85% | Language/accessibility filtering complete; missing advanced filter params |
| Report (Community Reports) | 85% | CRUD + auth consistent; action enum is extensible |
| Predict (Busyness Forecast) | 60% | 12h forecast defined but DB unsupported; missing alerts |
| Navigate (Routing) | 65% | Routes endpoint exists; missing step-free mode filtering |
| Connect (User/Safety) | 50% | Missing SOS endpoint + notification config; Medical ID intentionally excluded (device-local) |
| **Overall** | **~72%** | Core flows covered; key Must Haves have gaps |

---

## 6. Priority Fix Items

1. **Create `busyness_forecasts` table** — resolve 12h forecast data source gap (independent time-series table)
2. **Rename OpenAPI Venue `phone_number` to `phone`** — unify naming
3. **Add `POST /user/sos` endpoint** — US-10 Must Have (medical data stays local on device, no server-side medical endpoints)
4. **Add busyness alert notification endpoints** — US-08 Must Have missing
5. **Add `venue_type` query param to `GET /venues`** — support advanced filter panel
6. **Remove Medical ID / Emergency Contacts from OpenAPI** — team decision: device-local only
