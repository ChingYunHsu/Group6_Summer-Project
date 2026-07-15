# Forecast V2 execution record

## Purpose

This record separates reproducible offline evidence from real-data validation.
It must be updated only with command outputs and artifact paths; it must not
claim that bootstrap-label metrics measure actual foot traffic.

## Implementation log

| Item | Status | Evidence |
|---|---|---|
| Canonical model entry point | Complete | Top-level `forecast_v2_model.py`; `src/forecast_v2_model.py` is a compatibility import only. |
| Offline unit contracts | Complete | `tests/test_forecast_v2.py`; run with `pytest tests/test_forecast_v2.py test_external_feature_ingest.py -m "not integration"`. |
| CI coverage | Complete | `.github/workflows/data_ci.yml` runs the same offline V2 test command. |
| Append-only evidence | Complete | `run_v2_evidence.py --mode offline` writes timestamped outputs under `evidence/offline/`. |
| Real-data gate | Complete | `validate_v2_real_data.py` writes `READY` or `SKIPPED — environment unavailable`; it never substitutes synthetic rows. |
| Report figures | Complete | `generate_v2_report_visuals.py` generates a venue-by-time heatmap, test-MAE comparison, and actual-vs-predicted plot. |

## Required execution sequence

```bash
cd Data+ML/test/7.13-7.18
pytest tests/test_forecast_v2.py test_external_feature_ingest.py -v -m "not integration"
python run_v2_evidence.py --mode offline
python validate_v2_real_data.py --evidence-root evidence
```

For a real-data run, first ensure MySQL is reachable and the external context
cache is populated, then run `python run_v2_evidence.py --mode real`.

## Recorded execution — 2026-07-15

- Full V2 offline suite: `78 passed` using `.venv-1/bin/python -m pytest`.
- Canonical offline evidence: `evidence/offline/20260715T092634Z/`.
  - Provenance: `synthetic bootstrap`; 8 venues, 768 training rows, 96 forecast rows.
  - Best offline test model: `GradientBoostingRegressor`, MAE `2.732`.
  - Quality gate: `PARTIAL ROLLOUT`; it is not a claim of real-world accuracy.
  - Artifacts: CSV inputs/outputs, SHA-256 manifest, quality report, dry-run SQL log,
    and `figures/actual_vs_predicted.png`, `figures/model_test_mae.png`, and
    `figures/venue_busyness_heatmap.png`.
- Real-data validation: `SKIPPED — environment unavailable` because neither
  `DB_URL` nor `MYSQL_HOST` was configured. The validation record is under
  `evidence/real-data-validation/` and no synthetic fallback was used.

## Reporting language

- `synthetic bootstrap`: report MAE/R² as offline proxy-label validation only.
- `real observed`: report MAE/R² only when the real-data validation record is
  `READY` and the evidence manifest is from the corresponding real run.
- The heatmap shows predictions by venue and forecast hour; it is not a
  geographic Manhattan density map because the forecast output contract does
  not currently preserve latitude/longitude.

## Known limitations

- External feature cache and MySQL availability are environment dependencies.
- The production API must continue to distinguish `quiet` score zero from
  `no_data`; neither is inferred from an unavailable real-data run.
- Evidence artifacts are append-only. Do not cite legacy `output/` reports
  whose inputs and row counts cannot be matched to a manifest.
