# Venue ML Coverage Audit Report

> Generated: 2026-06-23 17:29 UTC

## Summary

| Metric | Count | Pct |
|--------|------:|----:|
| Total venues | 4838 | 100% |
| In-scope (healthcare + restroom) | 1559 | 32.2% |
| Out-of-scope (AED) | 3279 | 67.8% |
| Has popular_times | 54 | 3.5% of in-scope |
| No popular_times | 283 | 18.2% of in-scope |
| Not checked (API) | 1222 | 78.4% of in-scope |
| **ML eligible** | **54** | **3.5% of in-scope** |

## SerpApi Usage

- Search API calls: 1 category×district queries
- Results discovered: 314
- Results with popular_times: 31

## Category Coverage

| category       |   total_venues |   out_of_scope |   ml_eligible |   no_data |   has_popular_times |   checked_count |   ml_coverage_pct |   validation_success_pct |
|:---------------|---------------:|---------------:|--------------:|----------:|--------------------:|----------------:|------------------:|-------------------------:|
| emergencyasset |           3279 |           3279 |             0 |         0 |                   0 |               0 |                 0 |                      nan |
| healthcare     |           1086 |              0 |            54 |      1032 |                  54 |             337 |                 5 |                       16 |
| restroom       |            473 |              0 |             0 |       473 |                   0 |               0 |                 0 |                      nan |

## District Coverage

| district     |   total_venues |   out_of_scope |   ml_eligible |   no_data |   has_popular_times |   checked_count |   ml_coverage_pct |   validation_success_pct |
|:-------------|---------------:|---------------:|--------------:|----------:|--------------------:|----------------:|------------------:|-------------------------:|
| downtown     |           1467 |            901 |            21 |       545 |                  21 |             117 |               3.7 |                     17.9 |
| midtown_east |           1182 |            786 |             9 |       387 |                   9 |              88 |               2.3 |                     10.2 |
| midtown_west |           1428 |           1211 |            19 |       198 |                  19 |              83 |               8.8 |                     22.9 |
| uptown       |            703 |            381 |             5 |       317 |                   5 |              49 |               1.6 |                     10.2 |

## Citi Bike Proximity Distribution

| proximity_bucket    |   total_venues |   in_scope_venues |   pct_of_total |
|:--------------------|---------------:|------------------:|---------------:|
| 0-100m              |           2199 |               645 |           45.5 |
| 100-200m            |           2239 |               702 |           46.3 |
| 200-300m            |            303 |               127 |            6.3 |
| 300-500m            |             26 |                25 |            0.5 |
| 500m+               |             13 |                 2 |            0.3 |
| invalid_coordinates |             58 |                58 |            1.2 |

## Label Status Distribution

| Label Status | Count | Pct of Total | Pct of In-Scope |
|-------------|------:|----:|----:|
| api_not_checked | 1222 | 25.3% | 78.4% |
| has_popular_times | 54 | 1.1% | 3.5% |
| no_popular_times | 283 | 5.8% | 18.2% |

Out-of-scope venues are tracked by `venue_type`, not `label_status`: 3279 venues (67.8% of total).

## SOP Compliance

- ✅ Search queries used for batch discovery (not per-venue Place API calls)
- ✅ Place API only for final label validation
- ✅ Raw response caching implemented at `serpapi_raw_responses/` for live SerpApi runs
- ✅ Each venue has explicit `label_status` and `ml_eligible`
- ✅ Out-of-scope venues (AED/emergencyasset) excluded from ML training
- ✅ Coverage audit includes category, district, and Citi Bike proximity dimensions
- ✅ `prediction_source` distinguishes `ml_model` from `rule_fallback`

## Non-Range

- AED/emergencyasset venues: out of scope for supervised ML (no meaningful busyness)
- Restrooms: sparse Google Popular Times coverage; rule_fallback recommended
- Historical time series: not covered by SerpApi (requires BestTime or custom ETL)
