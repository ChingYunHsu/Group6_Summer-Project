# 6.22-6.27 SerpApi Label Coverage Pipeline

> Updated: 2026-06-28

## Table of Contents

1. [File Structure](#file-structure)
2. [Core Functions](#core-functions)
3. [Output Directory Structure](#output-directory-structure)
4. [Data Characteristics](#data-characteristics)
5. [Data Flow](#data-flow)

---

## File Structure

```
Data+ML/test/6.22-6.27/
├── src/                              # Python source code
│   ├── geo_utils.py                  # Shared spatial computation (Haversine distance)
│   ├── serpapi_client.py             # Shared SerpAPI HTTP client (cache + retry)
│   ├── api_usage_tracker.py          # API quota tracker
│   ├── healthcare_common.py          # Shared utilities (resolve_path, name matching, label updates)
│   ├── venue_serpapi.py              # Compatibility facade: import venue_serpapi as vs still works
│   ├── run_phased_search.py          # Main entry: stratified sampling + Phase A/B budget control
│   ├── validate_search_matched_places.py  # Place API validation
│   ├── dedupe_healthcare_discovery_matches.py # Dedupe discovery results
│   ├── build_healthcare_coverage_label_view.py # Merge coverage view
│   ├── build_healthcare_prediction_groups.py  # Offline prediction grouping
│   ├── write_healthcare_prediction_groups_to_db.py # Write back to MySQL
│   ├── populartimes_coverage_summary.py       # Offline coverage summary
│   └── run_phased.sh                 # Shell wrapper (reads .serpapi_key)
├── output/                           # Output artifacts
│   └── (see below)
└── serpapi_label_coverage.ipynb      # Notebook entry
```

---

## Core Functions

### geo_utils.py - Spatial Computation Utilities

| Function | Parameters | Return | Description |
|------|------|------|------|
| `haversine_distance_m(lat1, lng1, lat2, lng2)` | `float, float, float, float` | `float` | Haversine distance for a single coordinate pair (meters) |
| `haversine_distances_m(venues, lat, lng)` | `DataFrame, float, float` | `ndarray` | Vectorized: distance array from each row of venues DataFrame to (lat,lng) |

Constants: `EARTH_RADIUS_M = 6_371_008.8`

### serpapi_client.py - SerpAPI HTTP Client

| Function | Parameters | Return | Description |
|------|------|------|------|
| `serpapi_request(params, api_key, output_dir, cache_prefix)` | `dict, str, Path, str` | `dict \| None` | SerpAPI request with disk cache + retry |
| `get_cache_path(output_dir, prefix, params)` | `Path, str, dict` | `Path` | Returns cache file path |

Constants: `SERPAPI_BASE_URL`, `SERPAPI_TIMEOUT = (3, 10)`, `SERPAPI_MAX_RETRIES = 3`

### venue_serpapi.py - Compatibility Facade

All scripts and notebooks using `import venue_serpapi as vs` continue to work normally.
Internally migrated to `geo_utils` and `serpapi_client`; `_find_matching_venues()` uses `haversine_distances_m`.

**Module-level constants:**
- `EARTH_RADIUS_M = 6_371_008.8` - Earth mean radius (meters)
- `DISTRICT_CENTERS` - Coordinates of 4 Manhattan district centers
- `SERPAPI_SEARCH_CATEGORIES` - List of Search query templates `(search_query, google_type, clearpath_type)`
- `OUT_OF_SCOPE_CATEGORIES = {"emergencyasset"}` - Categories out of ML scope
- `CATEGORY_IMPORTANCE` - Importance weights per venue_type

**Data classes:**
- `SerpApiSearchResult` - Single Search discovery result
- `VenueLabelStatus` - ML label status for a single venue
- `CoverageAuditRow` - Coverage audit row

| Function | Parameters | Return | Description |
|------|------|------|------|
| `load_venues(csv_path)` | `str \| Path` | `tuple[DataFrame, int]` | Load deduplicated venues CSV, returns (df, dup_count) |
| `get_review_count(name)` | `str` | `int` | Estimate review count from venue name (deterministic hash placeholder) |
| `calculate_priority_score(...)` | `venue_type, district, review_count, rating, citibike_distance_m, district_label_coverage, is_duplicate` | `float` | SOP priority scoring formula |
| `audit_coverage_by_category(venues, label_status_df)` | `DataFrame, DataFrame?` | `DataFrame` | Coverage stats by venue_type |
| `audit_coverage_by_district(venues, label_status_df)` | `DataFrame, DataFrame?` | `DataFrame` | Coverage stats by district |
| `audit_citi_bike_proximity(venues, citibike_detail)` | `DataFrame, DataFrame?` | `DataFrame` | Coverage stats by Citi Bike distance bucket |
| `batch_search_discovery(venues, api_key, output_dir, ...)` | `DataFrame, str, Path, ...` | `list[SerpApiSearchResult]` | Batch Search API discovery (category×district) |
| `_find_matching_venues(venues, lat, lng, max_distance_m)` | `DataFrame, float, float, float` | `DataFrame` | Find matching venues within max_distance_m |
| `validate_candidates_with_place_api(candidates, api_key, output_dir, max_calls)` | `list, str, Path, int` | `list[SerpApiSearchResult]` | Validate popular_times via Place API |
| `generate_label_status(venues, search_results, citibike_detail)` | `DataFrame, list, DataFrame?` | `DataFrame` | Generate label status for all venues |
| `generate_candidate_list(label_status_df, output_path)` | `DataFrame, Path` | `DataFrame` | Generate ML candidate list (ml_eligible=True) |
| `generate_coverage_report(...)` | `category_audit, district_audit, citibike_audit, label_status_df, search_results, output_path` | `str` | Generate Markdown audit report |
| `save_run_metadata(...)` | `venues, search_results, label_status_df, output_dir, api_calls_search, api_calls_place` | `dict` | Save run metadata JSON |

### api_usage_tracker.py - API Quota Tracking

**Class `ApiUsageTracker`:**

| Method | Description |
|------|------|
| `__init__(output_dir, run_id?)` | Initialize tracker |
| `.search_calls` / `.place_calls` / `.total_calls` | Properties: call counts |
| `log_search_call(query, district, category, success, ...)` | Log a Search call |
| `log_place_call(place_id, venue_name, success, has_popular_times, ...)` | Log a Place call |
| `summary()` | Return stats dict |
| `print_summary(script_name)` | Print formatted summary |
| `save()` | Save JSON + append JSONL log |

### healthcare_common.py - Shared Utilities

| Function | Description |
|------|------|
| `resolve_path(path)` | CLI path resolution (relative to script directory) |
| `load_uncovered_healthcare(label_file, statuses)` | Load healthcare venues with the specified status |
| `normalize_name(value)` | Lowercase, strip spaces, `&` -> `and` |
| `name_similarity(left, right)` | SequenceMatcher name similarity (0–1) |
| `require_api_key(dry_run, confirm_live_api)` | API key guard: returns None in dry-run, otherwise validates |
| `apply_label_updates(labels, result_lookup, ...)` | Batch update label_status/ml_eligible/prediction_source and other columns |

### validate_search_matched_places.py - Place API Validation

| Function | Description |
|------|------|
| `load_validation_targets(coverage_view_file)` | Load healthcare rows with `search_matched_unvalidated` |
| `validate_place(place_id, api_key, output_dir)` | Call Place API to check popular_times |
| `run_validation(...)` | Main execution function |

### build_healthcare_coverage_label_view.py - Merge Coverage View

| Function | Description |
|------|------|
| `apply_batch_results(labels, batch_file)` | Sync batch results to labels |
| `apply_discovery_matches(labels, discovery_map_file)` | Sync discovery mappings (mark `search_matched_unvalidated`) |
| `rename_unmatched_healthcare(labels)` | Unmatched healthcare -> `search_not_matched` |
| `apply_restroom_audit(labels, restroom_audit_file)` | Sync restroom Popular Times audit |
| `build_label_view(...)` | Main function |

### build_healthcare_prediction_groups.py - Offline Prediction Grouping

| Function | Description |
|------|------|
| `build_group_id(row)` | Build group ID from place_id or venue_id |
| `build_prediction_groups(coverage_view_file)` | Main function, outputs 3 CSVs |

### populartimes_coverage_summary.py - Offline Coverage Summary

| Function | Description |
|------|------|
| `default_paths(project_root)` | Return default file paths dict |
| `build_type_summary(venues, label_scope)` | Coverage stats by venue_type |
| `build_status_breakdown(label_scope)` | label_status distribution |
| `build_district_summary(venues, label_scope)` | Stats by district |
| `build_summary_bundle(...)` | Return all presentation tables at once |

### write_healthcare_prediction_groups_to_db.py - Write Back to MySQL

| Function | Description |
|------|------|
| `write_healthcare_groups(grouped_view_file, live)` | Auto-add missing columns + UPDATE write to MySQL `venues` table |

---

## Output Directory Structure

```
output/
├── venue_label_status.csv                    # Baseline label status (full 4,838 rows)
├── venue_label_status_coverage_view.csv      # Merged coverage view (incl. discovery + batch + restroom)
├── venue_label_status_grouped_view.csv       # Grouped view (incl. prediction_group_id)
├── venue_ml_candidates.csv                   # ML candidate list (ml_eligible=True only)
├── healthcare_prediction_groups.csv          # Prediction group summary
├── healthcare_prediction_group_members.csv   # Prediction group member details
├── healthcare_uncovered_discovery_matches.csv # Discovery match results
├── restroom_popular_times_audit.csv          # Restroom Popular Times audit
├── run_metadata.json                         # Run metadata
├── api_usage_20260628T222906Z.json           # API quota consumption summary
├── api_usage_log.jsonl                       # API call-by-call log
├── coverage_audit_report_zh.md               # Chinese coverage audit report
└── serpapi_raw_responses/                    # SerpApi raw JSON response cache
    └── *.json (81 files)
```

---

## Data Characteristics

### venue_label_status.csv - Baseline Labels

| Metric | Value |
|------|-----|
| Total rows | 4,838 |
| Column count | 18 |
| venue_type distribution | emergencyasset=3,279 · healthcare=1,086 · restroom=473 |
| district distribution | downtown=1,467 · midtown_west=1,428 · midtown_east=1,182 · uptown=703 |
| label_status | api_not_checked=4,799 · has_popular_times=35 · no_popular_times=4 |
| ml_eligible | True=35 · False=4,803 |

> ⚠️ This file is DRY-RUN synthetic data; values will change after a LIVE run.

### venue_label_status_coverage_view.csv - Merged Coverage View

| Metric | Value |
|------|-----|
| Total rows | 4,838 |
| label_status | search_not_matched=4,254 · api_not_checked=471 · has_popular_times=71 · no_popular_times=42 |
| ml_eligible | True=71 · False=4,767 |

> Compared to the baseline file, more venues are evaluated (`api_not_checked` decreases, `search_not_matched` increases).

### venue_label_status_grouped_view.csv - Prediction Group View

| Metric | Value |
|------|-----|
| Total rows | 4,838 |
| Column count | 22 (base 18 + prediction_group_id, prediction_shared, group_match_source, group_member_count) |
| group_type | fallback_singleton=4,560 · shared_place=278 |
| prediction_shared | False=4,560 · True=278 |

> `shared_place` means multiple local venues share the same Google Place prediction.

### venue_ml_candidates.csv - ML Candidate List

| Metric | Value |
|------|-----|
| Total rows | 35 |
| All are | label_status=has_popular_times · ml_eligible=True · prediction_source=ml_model |
| venue_type | All healthcare |
| district distribution | midtown_west=17 · midtown_east=10 · uptown=5 · downtown=3 |
| display_level | All quiet |

### healthcare_prediction_groups.csv - Prediction Group Summary

| Metric | Value |
|------|-----|
| Total rows | 488 |
| group_type | shared_place=278 · fallback_singleton=210 |
| has_popular_times | 0=416 · 1=72 |

### healthcare_prediction_group_members.csv - Group Member Details

| Metric | Value |
|------|-----|
| Total rows | 1,426 |
| group_type | fallback_singleton=1,148 · shared_place=278 |
| prediction_source | venue_id_fallback=1,148 · serpapi_place_id=278 |

### healthcare_uncovered_discovery_matches.csv - Discovery Matches

| Metric | Value |
|------|-----|
| Total rows | 337 |
| Column count | 22 |
| label_status | All search_matched_unvalidated |
| name_similarity | Range 0.48–0.97 |
| place_checked | All False (pending Place API validation) |

### restroom_popular_times_audit.csv - Restroom Audit

| Metric | Value |
|------|-----|
| Total rows | 425 |
| has_popular_times | True=47 · False=378 |
| counts_as_restroom_coverage | True=47 · False=378 |
| exclude_reason | direct_restroom_without_popular_times=378 · (empty)=47 |

### run_metadata.json - Run Metadata

```json
{
  "run_id": "20260628T224231Z",
  "venue_input": { "total_rows": 4838 },
  "serpapi_usage": { "total_calls": 0, "monthly_quota_remaining": 250 },
  "results": { "total_discovered": 80, "with_popular_times": 30 },
  "label_status": { "has_popular_times": 35, "no_popular_times": 4 },
  "ml_eligible_count": 35
}
```

### serpapi_raw_responses/ - API Response Cache

- File count: 81 JSON files
- Naming convention: `{type}_{place_id_hash}.json` (e.g. `restroom_place_b8627331c38a.json`)
- Contents: Full SerpApi Search/Place API responses (incl. popular_times, reviews, photos, etc.)

---

## Data Flow

```
run_phased_search.py (main entry)
  │
  ├── Phase A: Stratified sampling DB-driven Search -> phase_a_search_results.csv
  │
  ├── Phase B: Place API on unique place_ids -> phase_b_place_results.csv
  │
  └── merge: Update venue_label_status_coverage_view.csv
                  │
validate_search_matched_places.py  ← Place API validation of discovery matches
                  │
build_healthcare_coverage_label_view.py  ← Merge batch + discovery + restroom
                  ↓ venue_label_status_coverage_view.csv
         build_healthcare_prediction_groups.py  ← Offline grouping
                  ↓ venue_label_status_grouped_view.csv
         write_healthcare_prediction_groups_to_db.py -> MySQL
```

**Coverage strategy (unified entry `run_phased_search.py`):**

| Phase | Description | API Consumption |
|-------|------|----------|
| **Phase A** | Stratified sampling DB-driven Search (budget allocated by subtype) | Low (1 Search per venue) |
| **Phase B** | Call Place API on unique place_ids deduped from Phase A | Medium (1 Place per unique place) |
