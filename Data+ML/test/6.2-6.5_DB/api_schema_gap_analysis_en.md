# ClearPath API-to-Schema Gap Analysis

**Date:** 2026-06-02  
**Sources:** `src/mock_data.py`, Team6_Contract.pdf (Endpoint Shared Contract), `docker/mysql/init/001_clearpath_schema.sql`

---

## 1. Overview

This document consolidates two analyses:

1. **API Contract vs Schema** — field-level mapping from the shared PDF contract to MySQL tables.
2. **Mock Data vs Schema** — field-level mapping from `src/mock_data.py` to MySQL tables.

The goal is to identify every gap, determine whether it requires a schema change or can be resolved at the API layer, and provide a single prioritized implementation plan.

---

## 2. Field Mapping — Venues

### 2.1 GET /api/v1/venues (List)

| API Field | Type | Mock Data Field | DB Column | Status |
|-----------|------|----------------|-----------|--------|
| venue_id | string | venue_id | venues.venue_id | ✅ Aligned |
| name | string | name | venues.name | ✅ Aligned |
| category | string | venue_type | venues.venue_type | ⚠️ Enum values need alignment |
| lat | number | latitude | venues.latitude | ✅ Aligned |
| lng | number | longitude | venues.longitude | ✅ Aligned |
| distance_m | number | — | — | ✅ Computed at API layer (no storage) |
| address | string | — | venues.address | ✅ Aligned |
| **accessibility.wheelchair_friendly** | bool | accessible_status | — | ❌ **New table needed** |
| **accessibility.step_free_route** | bool | accessibility_features | — | ❌ **New table needed** |
| **accessibility.accessible_toilet** | bool | accessibility_features | — | ❌ **New table needed** |
| **accessibility.entrance_width_cm** | int | — | — | ❌ **New table needed** |
| **warnings.active_warning** | bool | active_warning | — | ❌ **Derived from reports** |
| **warnings.warning_detail** | string | — | — | ❌ **New table needed** |
| **warnings.wait_alert** | bool | — | — | ❌ **New table needed** |
| **warnings.replacement_suggestion** | object[] | — | — | ❌ **New table needed** |
| **language.language_tag** | string[] | language_tags | — | ❌ **New table needed** |
| **language.language_support_level** | string | — | — | ❌ **New table needed** |
| **language.chatbot_enabled** | bool | — | — | ❌ **New table needed** |
| **language.chatbot_welcoming_message** | string | — | — | ❌ **New table needed** |
| **busyness.busyness_score** | int | busyness_percent | busyness_scores.score | ✅ Aligned |
| **busyness.busyness_status** | string | busyness_level | busyness_scores.level | ⚠️ Enum mapping needed |
| **busyness.busyness_color** | string | — | — | ✅ Computed at API layer |
| **busyness.estimated_wait_minutes** | int | avg_wait_minutes | busyness_scores.estimated_wait_minutes | ✅ Aligned |
| **busyness.forecast_1h** | int | — | — | ❌ **Column needed** |
| **busyness.forecast_4h** | int | — | — | ❌ **Column needed** |
| **busyness.forecast_8h** | int | — | — | ❌ **Column needed** |

### 2.2 GET /api/v1/venues/{venue_id} (Detail — extra fields)

| API Field | Type | Mock Data Field | DB Column | Status |
|-----------|------|----------------|-----------|--------|
| phone | string | — | venues.phone | ✅ Aligned |
| hours | string | — | venues.opening_hours | ✅ Aligned |
| **photos** | string[] | — | — | ❌ **Column needed** |
| **rating** | float | — | — | ❌ **Column needed** |
| source | string | — | venues.source_confidence | ⚠️ Name mismatch |
| data_confidence | float | — | venues.source_confidence | ✅ Aligned |
| created_at | string | — | venues.created_at | ✅ Aligned |
| open_now | bool | open_now | — | ⚠️ **Computed at API layer** |
| weather_risk | string | weather_risk | — | ❌ **Column needed or computed** |

---

## 3. Field Mapping — Reports

### 3.1 POST /api/v1/reports (Create)

| API Field | Type | Mock Data Field | DB Column | Status |
|-----------|------|----------------|-----------|--------|
| issue_type | string | issue_type | user_reports.issue_type | ⚠️ Enum values need alignment |
| venue_id | string | venue_id | user_reports.venue_id | ✅ Aligned |
| lat | number | latitude | user_reports.latitude | ✅ Aligned |
| lng | number | longitude | user_reports.longitude | ✅ Aligned |
| accuracy_m | number | — | user_reports.accuracy_meters | ⚠️ Name mismatch |
| **anonymous** | bool | reported_by | — | ❌ **Column needed** |
| **description** | string | — | — | ❌ **Column needed** |
| **photos** | string[] | — | — | ❌ **Column needed** |

### 3.2 GET /api/v1/reports (List)

| API Field | Type | Mock Data Field | DB Column | Status |
|-----------|------|----------------|-----------|--------|
| report_id | string | report_id | user_reports.report_id | ✅ Aligned |
| issue_type | string | issue_type | user_reports.issue_type | ✅ Aligned |
| venue_id | string | venue_id | user_reports.venue_id | ✅ Aligned |
| venue_name | string | — | — | ✅ JOIN venues.name |
| venue_category | string | — | — | ✅ JOIN venues.venue_type |
| lat | number | latitude | user_reports.latitude | ✅ Aligned |
| lng | number | longitude | user_reports.longitude | ✅ Aligned |
| accuracy_m | number | — | user_reports.accuracy_meters | ⚠️ Name mismatch |
| status | string | status | user_reports.status | ✅ Aligned |
| created_at | string | created_at | user_reports.created_at | ✅ Aligned |
| expires_at | string | expires_in_minutes | user_reports.expires_at | ⚠️ Format differs (timestamp vs duration) |
| **confirmations.count** | int | confirmation_count | — | ❌ **Need aggregate query** |
| **confirmations.latest_action** | string | — | — | ❌ **Need JOIN report_confirmations** |
| **confirmations.latest_action_at** | string | — | — | ❌ **Need JOIN report_confirmations** |
| **photos** | string[] | — | — | ❌ **Column needed** |
| **language.default_language** | string | — | — | ❌ **Column needed** |
| **language.fallback_language** | string | — | — | ❌ **Column needed** |
| live_report_count | int | live_report_count | — | ⚠️ **Computed: COUNT active reports** |
| badge_text | string | badge_text | — | ⚠️ **Computed at API layer** |

### 3.3 POST /api/v1/reports/{report_id}/confirmations

| API Field | Type | Mock Data Field | DB Column | Status |
|-----------|------|----------------|-----------|--------|
| report_id | string | — | report_confirmations.report_id | ✅ Aligned |
| action | string | — | report_confirmations.action | ⚠️ Enum values need alignment |
| **language** | string | — | — | ❌ **Column needed** |

### 3.4 GET /api/v1/integrations/status

No direct DB mapping. Returns external service connectivity status.

---

## 4. Required Schema Changes

### 4.1 New Columns on `venues`

```sql
-- Contact info (phone, photos, rating)
ALTER TABLE venues ADD COLUMN phone VARCHAR(64) AFTER opening_hours;
ALTER TABLE venues ADD COLUMN photos JSON AFTER phone;
ALTER TABLE venues ADD COLUMN rating DECIMAL(3,2) AFTER photos;

-- Weather risk level
ALTER TABLE venues ADD COLUMN weather_risk ENUM('low', 'medium', 'high') DEFAULT 'low' AFTER rating;

-- Language support fields
ALTER TABLE venues ADD COLUMN language_tags JSON AFTER borough;
ALTER TABLE venues ADD COLUMN primary_language VARCHAR(10) AFTER language_tags;
ALTER TABLE venues ADD COLUMN secondary_language VARCHAR(10) AFTER primary_language;

-- Accessibility status fields
ALTER TABLE venues ADD COLUMN accessible_status ENUM('full_access', 'partial', 'step_free_route_only', 'none') DEFAULT 'none' AFTER secondary_language;
ALTER TABLE venues ADD COLUMN accessibility_features JSON AFTER accessible_status;

-- Warning fields
ALTER TABLE venues ADD COLUMN active_warning BOOLEAN DEFAULT FALSE AFTER accessibility_features;
```

### 4.2 New Columns on `user_reports`

```sql
-- Anonymous, description, photos fields
ALTER TABLE user_reports ADD COLUMN anonymous BOOLEAN DEFAULT FALSE AFTER accuracy_meters;
ALTER TABLE user_reports ADD COLUMN description TEXT AFTER anonymous;
ALTER TABLE user_reports ADD COLUMN photos JSON AFTER description;
ALTER TABLE user_reports ADD COLUMN reported_by VARCHAR(50) DEFAULT 'anonymous' AFTER photos;

-- Multi-language support fields
ALTER TABLE user_reports ADD COLUMN default_language VARCHAR(10) AFTER reported_by;
ALTER TABLE user_reports ADD COLUMN fallback_language VARCHAR(10) AFTER default_language;
```

### 4.3 New Column on `report_confirmations`

```sql
ALTER TABLE report_confirmations ADD COLUMN language VARCHAR(10) AFTER action;
```

### 4.4 New Columns on `busyness_scores`

```sql
-- Forecast fields (1h/4h/8h)
ALTER TABLE busyness_scores ADD COLUMN forecast_1h INT AFTER estimated_wait_minutes;
ALTER TABLE busyness_scores ADD COLUMN forecast_4h INT AFTER forecast_1h;
ALTER TABLE busyness_scores ADD COLUMN forecast_8h INT AFTER forecast_4h;
```

### 4.5 New Table: `venue_accessibility`

```sql
CREATE TABLE IF NOT EXISTS venue_accessibility (
    venue_id VARCHAR(36) PRIMARY KEY,
    wheelchair_friendly BOOLEAN DEFAULT FALSE,
    step_free_route BOOLEAN DEFAULT FALSE,
    accessible_toilet BOOLEAN DEFAULT FALSE,
    entrance_width_cm INT,
    CONSTRAINT fk_accessibility_venue
        FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

### 4.6 New Table: `venue_language`

```sql
CREATE TABLE IF NOT EXISTS venue_language (
    venue_id VARCHAR(36) PRIMARY KEY,
    language_tag JSON,
    language_support_level ENUM('full', 'partial', 'none') DEFAULT 'none',
    chatbot_enabled BOOLEAN DEFAULT FALSE,
    chatbot_welcoming_message TEXT,
    CONSTRAINT fk_language_venue
        FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

### 4.7 New Table: `venue_warnings`

```sql
CREATE TABLE IF NOT EXISTS venue_warnings (
    venue_id VARCHAR(36) PRIMARY KEY,
    active_warning BOOLEAN DEFAULT FALSE,
    warning_detail TEXT,
    wait_alert BOOLEAN DEFAULT FALSE,
    replacement_suggestion JSON,
    CONSTRAINT fk_warnings_venue
        FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

---

## 5. API-Layer Computed Fields (No Schema Change)

These fields are present in the API response but should be **computed at runtime**, not stored:

| Field | Computation Logic |
|-------|-------------------|
| `distance_m` | Haversine formula from user location to venue |
| `busyness_color` | Map busyness_score to color (green/yellow/orange/red) |
| `live_report_count` | `SELECT COUNT(*) FROM user_reports WHERE venue_id = ? AND status = 'active'` |
| `badge_text` | Derived from confirmation_count and report status |
| `open_now` | Compare `opening_hours` with current time |
| `confirmations.count` | `SELECT COUNT(*) FROM report_confirmations WHERE report_id = ?` |
| `confirmations.latest_action` | `SELECT action FROM report_confirmations WHERE report_id = ? ORDER BY created_at DESC LIMIT 1` |
| `venue_name` / `venue_category` | JOIN with `venues` table |

---

## 6. Summary

| Category | New Columns | New Tables | API-Layer Only |
|----------|-------------|------------|----------------|
| `venues` | +10 fields | — | 1 (open_now) |
| `user_reports` | +6 fields | — | 2 (live_report_count, badge_text) |
| `report_confirmations` | +1 field | — | 1 (language) |
| `busyness_scores` | +3 fields | — | — |
| `venue_accessibility` | — | ✅ New table | — |
| `venue_language` | — | ✅ New table | — |
| `venue_warnings` | — | ✅ New table | — |
| Computed fields | — | — | +8 fields |

---

## 7. Next Steps

1. Update the Docker initializer SQL (`docker/mysql/init/001_clearpath_schema.sql`) with all schema changes.
2. Align `src/mock_data.py` to match the new schema fields.
3. Update API response serialization in `src/api/venues.py` and `src/api/reports.py`.
4. Add unit tests in `tests/test_database_plan.py` for new tables and fields.
