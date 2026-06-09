# ClearPath Database Fix Plan

**Date**: 2026-06-03  
**Goal**: Align database Schema with eq_sprint1 backend API code

---

## Conflict Summary

| Level | Count | Description |
|-------|:-----:|-------------|
| 🔴 Critical | 2 | venue_type enum mismatch; API doesn't handle all confirmation actions |
| 🟡 Missing Fields | 15 | venues missing 11 columns, reports missing 4 columns |
| 🟠 Redundant Fields | 7 | Schema has fields that API doesn't use |
| 🔵 Behavioral | 2 | reports endpoint has no auth; time format inconsistency |

---

## Fix Options

### Option A: Modify Schema (Recommended)

**Principle**: Schema is the data source, API is the consumer. Schema should accommodate API requirements.

#### Step 1: Extend venue_type Enum

```sql
ALTER TABLE venues MODIFY COLUMN venue_type ENUM(
    'restroom', 'healthcare', 'emergency_asset',
    'clinic', 'pharmacy', 'hospital', 'dentist', 'laboratory'
) NOT NULL;
```

#### Step 2: Add Columns to venues

```sql
-- Language support
ALTER TABLE venues ADD COLUMN IF NOT EXISTS language_tags JSON AFTER borough;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS primary_language VARCHAR(10) AFTER language_tags;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS secondary_language VARCHAR(10) AFTER primary_language;

-- Accessibility status
ALTER TABLE venues ADD COLUMN IF NOT EXISTS accessible_status ENUM(
    'full_access', 'partial', 'step_free_route_only', 'none'
) DEFAULT 'none' AFTER secondary_language;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS accessibility_features JSON AFTER accessible_status;

-- Warnings
ALTER TABLE venues ADD COLUMN IF NOT EXISTS active_warning BOOLEAN DEFAULT FALSE AFTER accessibility_features;

-- Photos and rating
ALTER TABLE venues ADD COLUMN IF NOT EXISTS photos JSON AFTER opening_hours;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS rating DECIMAL(3,2) AFTER photos;

-- Weather risk
ALTER TABLE venues ADD COLUMN IF NOT EXISTS weather_risk ENUM('low', 'medium', 'high') DEFAULT 'low' AFTER rating;
```

#### Step 3: Add Columns to user_reports

```sql
-- Anonymous and description
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS anonymous BOOLEAN DEFAULT FALSE AFTER accuracy_meters;
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS description TEXT AFTER anonymous;
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS photos JSON AFTER description;

-- Reporter
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS reported_by VARCHAR(50) DEFAULT 'anonymous' AFTER photos;

-- Expiry in minutes (align with API)
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS expires_in_minutes INT DEFAULT 120 AFTER status;

-- Multi-language
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS default_language VARCHAR(10) AFTER expires_in_minutes;
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS fallback_language VARCHAR(10) AFTER default_language;
```

#### Step 4: Add Column to report_confirmations

```sql
ALTER TABLE report_confirmations ADD COLUMN IF NOT EXISTS language VARCHAR(10) AFTER action;
```

#### Step 5: Add Columns to busyness_scores

```sql
ALTER TABLE busyness_scores ADD COLUMN IF NOT EXISTS forecast_1h INT AFTER estimated_wait_minutes;
ALTER TABLE busyness_scores ADD COLUMN IF NOT EXISTS forecast_4h INT AFTER forecast_1h;
ALTER TABLE busyness_scores ADD COLUMN IF NOT EXISTS forecast_8h INT AFTER forecast_4h;
```

#### Step 6: Create 3 New Tables

```sql
-- Venue accessibility
CREATE TABLE IF NOT EXISTS venue_accessibility (
    venue_id VARCHAR(36) PRIMARY KEY,
    wheelchair_friendly BOOLEAN DEFAULT FALSE,
    step_free_route BOOLEAN DEFAULT FALSE,
    accessible_toilet BOOLEAN DEFAULT FALSE,
    entrance_width_cm INT,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);

-- Venue language
CREATE TABLE IF NOT EXISTS venue_language (
    venue_id VARCHAR(36) PRIMARY KEY,
    language_tag JSON,
    language_support_level ENUM('full', 'partial', 'none') DEFAULT 'none',
    chatbot_enabled BOOLEAN DEFAULT FALSE,
    chatbot_welcoming_message TEXT,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);

-- Venue warnings
CREATE TABLE IF NOT EXISTS venue_warnings (
    venue_id VARCHAR(36) PRIMARY KEY,
    active_warning BOOLEAN DEFAULT FALSE,
    warning_detail TEXT,
    wait_alert BOOLEAN DEFAULT FALSE,
    replacement_suggestion JSON,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

---

### Option B: Modify API Layer (Alternative)

If Schema changes are not desired, map fields in the API layer:

| API Field | Schema Field | Mapping Logic |
|-----------|-------------|---------------|
| venue_type | venue_type | Map: clinic → healthcare |
| active_warning | none | Compute from reports table |
| open_now | none | Compare opening_hours with current time |
| expires_in_minutes | expires_at | Compute (expires_at - NOW()) / 60 |
| confirmation_count | none | Aggregate report_confirmations |

**Drawback**: Extra computation on every query, poor performance.

---

## Recommended Approach

**Choose Option A (Modify Schema)** for these reasons:
1. Better data consistency
2. Higher query performance
3. Minimal backend code changes
4. Follows "Schema is the source of truth" design principle

---

## Execution Order

| Step | Operation | Owner | Status |
|------|-----------|-------|--------|
| 1 | Modify venues enum | Data Lead | ⏳ |
| 2 | Add venues columns | Data Lead | ⏳ |
| 3 | Add user_reports columns | Data Lead | ⏳ |
| 4 | Add report_confirmations column | Data Lead | ⏳ |
| 5 | Add busyness_scores columns | Data Lead | ⏳ |
| 6 | Create 3 new tables | Data Lead | ⏳ |
| 7 | Update 001_clearpath_schema.sql | Data Lead | ⏳ |
| 8 | Update mock_data.py | Backend Lead | ⏳ |
| 9 | Update API response serialization | Backend Lead | ⏳ |
| 10 | Update unit tests | Collaborative | ⏳ |

---

## API Layer Computed Fields (No Storage Needed)

| Field | Computation Logic |
|-------|-------------------|
| distance_m | Haversine formula |
| busyness_color | Map score to color (green/yellow/orange/red) |
| live_report_count | COUNT active reports for venue |
| badge_text | Derive from confirmation count and report status |
| open_now | Compare opening_hours with current time |
| confirmation_count | COUNT confirmations for report |
| latest_action | Most recent confirmation action |
