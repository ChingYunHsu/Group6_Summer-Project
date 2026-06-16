# Venue Spatial Coverage Report

**Run ID:** 20260615T194956Z  
**Generated:** 2026-06-15T19:50:02.005916+00:00  
**Venue count:** 4838  
**Radii:** 100m, 200m, 300m, 400m, 500m

## 1. Run Summary

- Started: 2026-06-15T19:49:56.977016+00:00
- Completed: 2026-06-15T19:50:02.005916+00:00
- Venue file: `Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv`
- Total rows: 4838
- Duplicate venue_id removed: 0
- Unique venues: 4838

## 2. Source Status and Freshness

| Source | Status | Fetch Time | Raw | Valid | Unique IDs | Unique Coords | Rejected | Timestamp |
|--------|--------|------------|-----|-------|------------|---------------|----------|-----------|
| citibike | ok | 1.6s | 2411 | 2328 | 2328 | 2328 | 83 | 2026-06-15T19:49:22+00:00 |
| mta | ok | 0.6s | 445 | 445 | 445 | 445 | 0 | timestamp_unavailable |
| traffic | ok | 2.6s | 28 | 28 | 28 | 28 | 0 | timestamp_unavailable |

## 3. Overall Standalone Coverage

| Source | Radius | Venue Count | Covered | Coverage Rate | Marginal (pp) |
|--------|--------|-------------|---------|---------------|---------------|
| citibike | 100m | 4838 | 2199 | 45.5% | +45.5% |
| citibike | 200m | 4838 | 4438 | 91.7% | +46.3% |
| citibike | 300m | 4838 | 4741 | 98.0% | +6.3% |
| citibike | 400m | 4838 | 4757 | 98.3% | +0.3% |
| citibike | 500m | 4838 | 4767 | 98.5% | +0.2% |
| mta | 100m | 4838 | 575 | 11.9% | +11.9% |
| mta | 200m | 4838 | 1914 | 39.6% | +27.7% |
| mta | 300m | 4838 | 3136 | 64.8% | +25.3% |
| mta | 400m | 4838 | 3892 | 80.4% | +15.6% |
| mta | 500m | 4838 | 4265 | 88.2% | +7.7% |
| traffic | 100m | 4838 | 56 | 1.2% | +1.2% |
| traffic | 200m | 4838 | 159 | 3.3% | +2.1% |
| traffic | 300m | 4838 | 323 | 6.7% | +3.4% |
| traffic | 400m | 4838 | 529 | 10.9% | +4.3% |
| traffic | 500m | 4838 | 713 | 14.7% | +3.8% |

## 4. Cumulative Coverage and Source Marginal Contribution

| Combination | Radius | Cumulative Covered | Cumulative Rate | Incremental | Gain (pp) |
|-------------|--------|--------------------|-----------------|-------------|-----------|
| citibike | 100m | 2199 | 45.5% | +2199 | +45.5% |
| citibike + mta | 100m | 2470 | 51.1% | +271 | +5.6% |
| citibike + mta + traffic | 100m | 2493 | 51.5% | +23 | +0.5% |
| citibike | 200m | 4438 | 91.7% | +4438 | +91.7% |
| citibike + mta | 200m | 4541 | 93.9% | +103 | +2.1% |
| citibike + mta + traffic | 200m | 4548 | 94.0% | +7 | +0.1% |
| citibike | 300m | 4741 | 98.0% | +4741 | +98.0% |
| citibike + mta | 300m | 4747 | 98.1% | +6 | +0.1% |
| citibike + mta + traffic | 300m | 4748 | 98.1% | +1 | +0.0% |
| citibike | 400m | 4757 | 98.3% | +4757 | +98.3% |
| citibike + mta | 400m | 4763 | 98.4% | +6 | +0.1% |
| citibike + mta + traffic | 400m | 4763 | 98.4% | +0 | +0.0% |
| citibike | 500m | 4767 | 98.5% | +4767 | +98.5% |
| citibike + mta | 500m | 4772 | 98.6% | +5 | +0.1% |
| citibike + mta + traffic | 500m | 4772 | 98.6% | +0 | +0.0% |

## 5. Coverage by Venue Type

### emergencyasset

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 1554/3279 | 47.4% |
| citibike | 200m | 3091/3279 | 94.3% |
| citibike | 300m | 3267/3279 | 99.6% |
| citibike | 400m | 3268/3279 | 99.7% |
| citibike | 500m | 3268/3279 | 99.7% |
| mta | 100m | 409/3279 | 12.5% |
| mta | 200m | 1442/3279 | 44.0% |
| mta | 300m | 2314/3279 | 70.6% |
| mta | 400m | 2816/3279 | 85.9% |
| mta | 500m | 3034/3279 | 92.5% |
| traffic | 100m | 38/3279 | 1.2% |
| traffic | 200m | 111/3279 | 3.4% |
| traffic | 300m | 212/3279 | 6.5% |
| traffic | 400m | 353/3279 | 10.8% |
| traffic | 500m | 466/3279 | 14.2% |

### healthcare

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 465/1086 | 42.8% |
| citibike | 200m | 1009/1086 | 92.9% |
| citibike | 300m | 1079/1086 | 99.4% |
| citibike | 400m | 1080/1086 | 99.4% |
| citibike | 500m | 1085/1086 | 99.9% |
| mta | 100m | 148/1086 | 13.6% |
| mta | 200m | 391/1086 | 36.0% |
| mta | 300m | 664/1086 | 61.1% |
| mta | 400m | 842/1086 | 77.5% |
| mta | 500m | 937/1086 | 86.3% |
| traffic | 100m | 18/1086 | 1.7% |
| traffic | 200m | 42/1086 | 3.9% |
| traffic | 300m | 88/1086 | 8.1% |
| traffic | 400m | 138/1086 | 12.7% |
| traffic | 500m | 192/1086 | 17.7% |

### restroom

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 180/473 | 38.1% |
| citibike | 200m | 338/473 | 71.5% |
| citibike | 300m | 395/473 | 83.5% |
| citibike | 400m | 409/473 | 86.5% |
| citibike | 500m | 414/473 | 87.5% |
| mta | 100m | 18/473 | 3.8% |
| mta | 200m | 81/473 | 17.1% |
| mta | 300m | 158/473 | 33.4% |
| mta | 400m | 234/473 | 49.5% |
| mta | 500m | 294/473 | 62.2% |
| traffic | 100m | 0/473 | 0.0% |
| traffic | 200m | 6/473 | 1.3% |
| traffic | 300m | 23/473 | 4.9% |
| traffic | 400m | 38/473 | 8.0% |
| traffic | 500m | 55/473 | 11.6% |

## 6. Coverage by District

### downtown

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 770/1467 | 52.5% |
| citibike | 200m | 1400/1467 | 95.4% |
| citibike | 300m | 1456/1467 | 99.3% |
| citibike | 400m | 1458/1467 | 99.4% |
| citibike | 500m | 1458/1467 | 99.4% |
| mta | 100m | 253/1467 | 17.2% |
| mta | 200m | 642/1467 | 43.8% |
| mta | 300m | 964/1467 | 65.7% |
| mta | 400m | 1171/1467 | 79.8% |
| mta | 500m | 1276/1467 | 87.0% |
| traffic | 100m | 11/1467 | 0.7% |
| traffic | 200m | 35/1467 | 2.4% |
| traffic | 300m | 64/1467 | 4.4% |
| traffic | 400m | 104/1467 | 7.1% |
| traffic | 500m | 164/1467 | 11.2% |

### midtown_east

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 431/1182 | 36.5% |
| citibike | 200m | 1047/1182 | 88.6% |
| citibike | 300m | 1162/1182 | 98.3% |
| citibike | 400m | 1171/1182 | 99.1% |
| citibike | 500m | 1180/1182 | 99.8% |
| mta | 100m | 100/1182 | 8.5% |
| mta | 200m | 344/1182 | 29.1% |
| mta | 300m | 628/1182 | 53.1% |
| mta | 400m | 854/1182 | 72.3% |
| mta | 500m | 1002/1182 | 84.8% |
| traffic | 100m | 22/1182 | 1.9% |
| traffic | 200m | 81/1182 | 6.9% |
| traffic | 300m | 173/1182 | 14.6% |
| traffic | 400m | 296/1182 | 25.0% |
| traffic | 500m | 372/1182 | 31.5% |

### midtown_west

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 722/1428 | 50.6% |
| citibike | 200m | 1348/1428 | 94.4% |
| citibike | 300m | 1426/1428 | 99.9% |
| citibike | 400m | 1428/1428 | 100.0% |
| citibike | 500m | 1428/1428 | 100.0% |
| mta | 100m | 166/1428 | 11.6% |
| mta | 200m | 730/1428 | 51.1% |
| mta | 300m | 1132/1428 | 79.3% |
| mta | 400m | 1260/1428 | 88.2% |
| mta | 500m | 1318/1428 | 92.3% |
| traffic | 100m | 12/1428 | 0.8% |
| traffic | 200m | 31/1428 | 2.2% |
| traffic | 300m | 72/1428 | 5.0% |
| traffic | 400m | 108/1428 | 7.6% |
| traffic | 500m | 142/1428 | 9.9% |

### uptown

| Source | Radius | Covered | Rate |
|--------|--------|---------|------|
| citibike | 100m | 276/703 | 39.3% |
| citibike | 200m | 643/703 | 91.5% |
| citibike | 300m | 697/703 | 99.1% |
| citibike | 400m | 700/703 | 99.6% |
| citibike | 500m | 701/703 | 99.7% |
| mta | 100m | 56/703 | 8.0% |
| mta | 200m | 198/703 | 28.2% |
| mta | 300m | 412/703 | 58.6% |
| mta | 400m | 607/703 | 86.3% |
| mta | 500m | 669/703 | 95.2% |
| traffic | 100m | 11/703 | 1.6% |
| traffic | 200m | 12/703 | 1.7% |
| traffic | 300m | 14/703 | 2.0% |
| traffic | 400m | 21/703 | 3.0% |
| traffic | 500m | 35/703 | 5.0% |

## 7. Nearest-Distance Distribution

| Source | Median (m) | P90 (m) |
|--------|------------|---------|
| citibike | 106.95 | 192.26 |
| mta | 241.28 | 524.25 |
| traffic | 1110.46 | 2231.34 |

## 8. Uncovered Venue Counts

- **citibike** at 500m: 71 uncovered venues
- **mta** at 500m: 573 uncovered venues
- **traffic** at 500m: 4125 uncovered venues

## 9. Data-Quality Warnings

- **citibike**: 83 rejected records
- No critical warnings.

## 10. Data Applicability Warning

- NYC Traffic segments represent road-level sensor coverage, not pedestrian volume.
- Low segment count for the requested year reflects official data sparsity,
  not a parsing error.
- Spatial coverage does NOT imply the source captures venue-level activity.

## 11. Traffic Year Profile

| Year | Record Count | Unique Segments |
|------|-------------|-----------------|
| 2000 | 766 | 766 |
| 2006 | 664 | 664 |
| 2007 | 218 | 218 |
| 2008 | 2988 | 2988 |
| 2009 | 20238 | 20238 |
| 2010 | 15086 | 15086 |
| 2011 | 16977 | 16977 |
| 2012 | 30847 | 30847 |
| 2013 | 41919 | 41919 |
| 2014 | 29169 | 29169 |
| 2015 | 13218 | 13218 |
| 2016 | 11569 | 11569 |
| 2017 | 29460 | 29460 |
| 2018 | 23705 | 23705 |
| 2019 | 13714 | 13714 |
| 2020 | 11040 | 11040 |
| 2021 | 14839 | 14839 |
| 2022 | 10272 | 10272 |
| 2023 | 16374 | 16374 |
| 2024 | 21772 | 21772 |
| 2025 | 18048 | 18048 |
| 2026 | 672 | 672 |

## 12. Interpretation Constraints

- Spatial coverage does NOT indicate prediction quality or pedestrian busyness.
- NYC Traffic segments are road-level, not venue-level; coverage ≠ correlation.
- No production radius is recommended; review marginal results per 100m increment.
- BestTime is excluded (paid venue-level source).
- Pedestrian sensors are excluded from primary coverage (sparse active coverage).
