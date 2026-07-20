-- Compatibility migration for databases created before the V2 label fields
-- were promoted into 001_clearpath_schema.sql.  The order is intentionally
-- identical to venues_export.sql generated on 2026-07-18 (commit ae63fbb).
USE clearpath;

ALTER TABLE venues ADD COLUMN IF NOT EXISTS serpapi_place_id VARCHAR(36) NULL;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS prediction_group_id VARCHAR(64) NULL;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS prediction_shared BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS serpapi_label_status VARCHAR(32) NULL;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS has_popular_times BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS ml_eligible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS serpapi_checked_at VARCHAR(32) NULL;
