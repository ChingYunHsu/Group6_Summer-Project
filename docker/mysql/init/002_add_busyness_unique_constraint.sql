-- Migration: Add business unique key to busyness_scores for idempotent writes
-- Date: 2026-06-15
-- Issue: INSERT IGNORE without unique constraint causes duplicate rows on re-run

ALTER TABLE busyness_scores
  ADD UNIQUE KEY uq_busyness_venue_time (venue_id, forecast_start_time, model_version);
