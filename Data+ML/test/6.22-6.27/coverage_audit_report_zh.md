# Venue ML Coverage Audit Report

> Generated: 2026-06-23 15:05 UTC

## Summary

| Metric | Count | Percentage |
|------|-----:|-------:|
| Total venues | 4838 | 100% |
| In scope (medical + restroom) | 1559 | 32.2% |
| Out of scope (AED) | 3279 | 67.8% |
| Has popular times data | 55 | 3.5% of in scope |
| No popular times data | 3 | 0.2% of in scope |
| Not checked (API) | 1501 | 96.3% of in scope |
| **Available for ML** | **55** | **3.5% of in scope** |

## SerpApi Usage

- Search API calls: 0 category×region queries
- Place API calls: 0 verification queries
- Discovery results: 80
- Results with popular times data: 30

## Category Coverage

| Category | Total venues | Out of scope | Available for ML | No data | Has popular times | Checked | ML coverage | Verification success rate |
|------|--------:|-------:|----------:|-------:|-----------:|--------:|----------:|----------:|
| emergencyasset | 3279 | 3279 | 0 | 0 | 0 | 0 | 0.0 |  |
| healthcare | 1086 | 0 | 55 | 1031 | 55 | 58 | 5.1 | 94.8 |
| restroom | 473 | 0 | 0 | 473 | 0 | 0 | 0.0 |  |

## Region Coverage

| Region | Total venues | Out of scope | Available for ML | No data | Has popular times | Checked | ML coverage | Verification success rate |
|------|--------:|-------:|----------:|-------:|-----------:|--------:|----------:|----------:|
| downtown | 1467 | 901 | 14 | 552 | 14 | 14 | 2.5 | 100.0 |
| midtown_east | 1182 | 786 | 20 | 376 | 20 | 22 | 5.1 | 90.9 |
| midtown_west | 1428 | 1211 | 14 | 203 | 14 | 14 | 6.5 | 100.0 |
| unknown | 58 | 0 | 0 | 58 | 0 | 0 | 0.0 |  |
| uptown | 703 | 381 | 7 | 315 | 7 | 8 | 2.2 | 87.5 |

## Citi Bike Proximity Distribution

| Proximity range | Total venues | In-scope venues | % of total |
|-----------|--------:|------------:|------------:|
| Invalid coordinates | 58 | 58 | 1.2 |
| 0-100m | 2199 | 645 | 45.5 |
| 100-200m | 2239 | 702 | 46.3 |
| 200-300m | 303 | 127 | 6.3 |
| 300-500m | 26 | 25 | 0.5 |
| 500m+ | 13 | 2 | 0.3 |

## Label Status Distribution (in scope only)

| Label status | Count | % of total | % of in scope |
|---------|-----:|-------------:|---------------:|
| api_not_checked (not checked via API) | 1501 | 31.0% | 96.3% |
| has_popular_times (has popular times) | 55 | 1.1% | 3.5% |
| no_popular_times (no popular times) | 3 | 0.1% | 0.2% |

Out-of-scope venues are tracked by `venue_type` (venue type) rather than `label_status` (label status): 3279 venues (67.8% of total).

## SOP Compliance

- ✅ Batch discovery via search queries (not per-venue Place API calls)
- ✅ Place API used only for final label verification
- ✅ Raw response caching under the `serpapi_raw_responses/` directory (for live SerpApi runs)
- ✅ Every venue has an explicit `label_status` and `ml_eligible`
- ✅ Out-of-scope venues (AED/emergencyasset) excluded from ML training via `venue_type`
- ✅ Coverage audit includes category, region, and Citi Bike proximity dimensions
- ✅ `prediction_source` distinguishes `ml_model` (ML model) from `rule_fallback` (rule fallback)

## Out-of-Scope Notes

- AED/emergencyasset venues: not in supervised ML scope (no meaningful busyness data)
- Restrooms: sparse Google popular times coverage; rule fallback recommended
- Historical time series: not covered by SerpApi (requires BestTime or custom ETL)
