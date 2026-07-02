-- Migration: Add business unique key to busyness_scores for idempotent writes
-- Date: 2026-06-15
-- Issue: INSERT IGNORE without unique constraint causes duplicate rows on re-run

USE clearpath;

SET @has_uq_busyness_venue_time := (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'busyness_scores'
    AND index_name = 'uq_busyness_venue_time'
);

SET @add_uq_busyness_venue_time := IF(
  @has_uq_busyness_venue_time = 0,
  'ALTER TABLE busyness_scores ADD UNIQUE KEY uq_busyness_venue_time (venue_id, forecast_start_time, model_version)',
  'SELECT ''uq_busyness_venue_time already exists'' AS status'
);

PREPARE stmt FROM @add_uq_busyness_venue_time;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
