# Busyness & Venue Coverage - File Index

> Organized date: 2026-06-15  
> Source directory: `Data+ML/test/6.8-6.12_DB/`

## Directory Structure

```text
6.15-5.20/
├── src/                          # Source code
│   ├── busyness_ingestion.py     # Busyness ETL pipeline (440 lines)
│   ├── venue_coverage.py         # Spatial coverage testing core (1,190 lines)
│   └── run_venue_coverage.py     # CLI entry point (350 lines)
├── tests/                        # Test files
│   ├── conftest.py               # Pytest shared fixtures
│   ├── test_busyness_ingestion.py  # Busyness tests (44 tests)
│   └── test_venue_coverage.py      # Coverage tests (65 tests)
├── output/                       # Run output
│   └── venue_coverage/           # Latest coverage run results
│       ├── venue_coverage_detail.csv
│       ├── coverage_summary.csv
│       ├── coverage_report.md
│       ├── run_metadata.json
│       ├── coverage_by_radius.png
│       ├── incremental_coverage.png
│       ├── venue_type_coverage_heatmap.png
│       └── uncovered_venue_distribution.png
└── docs/                         # Documentation and review
    ├── venue_coverage_sop_zh.md  # Spatial coverage SOP (Chinese)
    ├── busynessreview.md         # Busyness code review notes
    └── venue-coverage-review.md  # Coverage testing execution gap analysis
```

> **Dependencies**: Source files under `src/` reference shared modules in `Data+ML/test/6.8-6.12_DB/dqr/` via `sys.path`, and are not duplicated.

## File Descriptions

### Source Code

| File | Lines | Function |
|------|------|------|
| `busyness_ingestion.py` | 440 | ETL pipeline: NYC transit data -> venue busyness score |
| `venue_coverage.py` | 1,190 | Core of Citi Bike / MTA / Traffic spatial coverage testing |
| `run_venue_coverage.py` | 350 | Coverage testing CLI entry point, supports `--radii`, `--sources` and other parameters |

### Tests

| File | Test Count | Coverage Scope |
|------|--------|---------|
| `test_busyness_ingestion.py` | 44 (44 pass) | Classification, GPS conversion, distance, aggregation, venue matching, forecasting, DB writes, API fetching, pipeline |
| `test_venue_coverage.py` | 65 (62 pass, 3 skip) | CLI, HTTP retry, data source adapters, BallTree, coverage aggregation, artifact contracts, charts, MTA station complexes, Traffic annual diagnostics |

### Output (latest run: 20260615T150606Z)

| Data Source | Status | Dataset | 100m Coverage | 500m Coverage |
|--------|------|--------|------------|------------|
| Citi Bike | ✅ ok | GBFS | 45.3% | 98.5% |
| MTA | ✅ Fixed | `5f5g-n3cz` (station complexes) | Pending run | Pending run |
| Traffic | ✅ ok | `7ym2-wayt` | 1.2% | 14.7% |

### Documentation

| File | Content |
|------|------|
| `venue_coverage_sop_zh.md` | Standard operating procedure for spatial coverage testing |
| `busynessreview.md` | Code review and test explanation for busyness_ingestion.py |
| `venue-coverage-review.md` | Feature overview and execution gap analysis (P0-P3) |

## Run Commands

```bash
# Busyness tests
.venv-1/bin/python -m pytest -q Data+ML/test/6.15-5.20/tests/test_busyness_ingestion.py

# Coverage tests
.venv-1/bin/python -m pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py

# Coverage tests (live smoke)
python Data+ML/test/6.15-5.20/src/run_venue_coverage.py \
  --venue-file Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv \
  --radii 100,200,300,400,500 \
  --sources citibike,mta,traffic \
  --output-dir Data+ML/test/6.15-5.20/output/venue_coverage
```
