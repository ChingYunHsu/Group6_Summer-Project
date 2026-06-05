# ClearPath Schema Fix Summary

**Date:** 2026-06-03  
**Source:** [CN]fix_plan.md + api_schema_gap_analysis_en.md  
**Status:** ✅ Schema synced, API layer pending

---

## 1. Execution Log

| Step | Operation | Status |
|------|-----------|--------|
| 1 | venues enum expansion (+6 values) | ✅ |
| 2 | venues add 9 columns | ✅ |
| 3 | user_reports add 7 columns | ✅ |
| 4 | report_confirmations add 1 column | ✅ |
| 5 | busyness_scores add 3 columns | ✅ |
| 6 | create venue_accessibility table | ✅ |
| 7 | create venue_language table | ✅ |
| 8 | create venue_warnings table | ✅ |
| 9 | sync docker/mysql/init/001_clearpath_schema.sql | ✅ |
| 10 | sync Data+ML/test/6.2_DB/001_clearpath_schema.sql | ✅ |
| 11 | update mock_data.py | ⏳ |
| 12 | update API response serialization | ⏳ |
| 13 | update unit tests | ⏳ |

---

## 2. Schema Changes Detail

### 2.1 venues Table

**Enum expansion:**
```sql
venue_type ENUM(
  'restroom', 'healthcare', 'emergency_asset',
  'clinic', 'pharmacy', 'hospital', 'dentist', 'laboratory'
)
```

**9 new columns:**

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| photos | JSON | — | Venue photo URLs |
| rating | DECIMAL(3,2) | — | Rating (0.00–5.00) |
| weather_risk | ENUM('low','medium','high') | 'low' | Weather risk level |
| language_tags | JSON | — | Supported languages |
| primary_language | VARCHAR(10) | — | Primary language |
| secondary_language | VARCHAR(10) | — | Secondary language |
| accessible_status | ENUM('full_access','partial','step_free_route_only','none') | 'none' | Accessibility status |
| accessibility_features | JSON | — | Accessibility feature details |
| active_warning | BOOLEAN | FALSE | Active warning flag |

### 2.2 user_reports Table — 7 New Columns

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| anonymous | BOOLEAN | FALSE | Anonymous report flag |
| description | TEXT | — | Issue description |
| photos | JSON | — | Photo URLs |
| reported_by | VARCHAR(50) | 'anonymous' | Reporter identifier |
| expires_in_minutes | INT | 120 | Expiry duration (minutes) |
| default_language | VARCHAR(10) | — | User default language |
| fallback_language | VARCHAR(10) | — | User fallback language |

### 2.3 report_confirmations Table — 1 New Column

| Column | Type | Purpose |
|--------|------|---------|
| language | VARCHAR(10) | Confirmation language |

### 2.4 busyness_scores Table — 3 New Columns

| Column | Type | Purpose |
|--------|------|---------|
| forecast_1h | INT | 1-hour forecast |
| forecast_4h | INT | 4-hour forecast |
| forecast_8h | INT | 8-hour forecast |

### 2.5 New Tables

| Table | PK | Purpose |
|-------|-----|---------|
| venue_accessibility | venue_id (FK) | Accessibility details (wheelchair_friendly, step_free_route, accessible_toilet, entrance_width_cm) |
| venue_language | venue_id (FK) | Multilingual support (language_tag, language_support_level, chatbot_enabled, chatbot_welcoming_message) |
| venue_warnings | venue_id (FK) | Warning info (active_warning, warning_detail, wait_alert, replacement_suggestion) |

---

## 3. ⚠️ API-Layer Residuals (No Schema Change Needed)

| Item | API Field | Schema Field | Resolution |
|------|-----------|-------------|------------|
| Enum mapping | busyness_status | level | API layer: map `unknown` → `'low'` or omit |
| Field rename | accuracy_m | accuracy_meters | API layer: serialize as `accuracy_m` |
| Field rename | source | source_confidence | Confirm if `source` maps to `venue_source_links.source_name` |
| Computed field | open_now | — | API layer: compare `opening_hours` with current time |
| Computed field | busyness_color | — | API layer: map score to color |
| Aggregate | confirmations.count | — | API layer: `COUNT(report_confirmations)` |
| Aggregate | confirmations.latest_action | — | API layer: JOIN `report_confirmations` |
| Aggregate | live_report_count | — | API layer: `COUNT(user_reports WHERE status='active')` |
| Derived field | badge_text | — | API layer: derive from confirmation count |

---

## 4. File Sync Status

| File | Path | Status |
|------|------|--------|
| Docker init | docker/mysql/init/001_clearpath_schema.sql | ✅ Updated |
| Test copy | Data+ML/test/6.2_DB/001_clearpath_schema.sql | ✅ Synced |
| Gap Analysis (EN) | Data+ML/test/6.2_DB/api_schema_gap_analysis_en.md | ✅ Verified |
| Gap Analysis (CN) | Data+ML/test/6.2_DB/[CN]api_schema_gap_analysis_cn.md | ✅ Verified |
| Fix Plan (CN) | Data+ML/test/6.2_DB/[CN]fix_plan.md | ✅ Reference doc |

---

## 5. Next Steps

1. **mock_data.py** — Generate mock data for new columns
2. **API serialization** — venues.py / reports.py response mapping
3. **Unit tests** — test_database_plan.py coverage for new tables and columns
4. **Docker rebuild** — `docker compose down -v && docker compose up -d` to recreate database
