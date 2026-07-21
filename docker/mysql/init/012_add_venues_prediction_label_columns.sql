-- Compatibility migration for databases created before the V2 label fields
-- were promoted into 001_clearpath_schema.sql.  MySQL 8.4 does not support
-- `ADD COLUMN IF NOT EXISTS`, so each column is guarded via information_schema
-- and a prepared no-op / ALTER statement instead.
--
-- The order is intentionally identical to venues_export.sql generated on
-- 2026-07-18 (commit ae63fbb). It is safe to re-run.
USE clearpath;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'serpapi_place_id');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN serpapi_place_id VARCHAR(36) NULL', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'prediction_group_id');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN prediction_group_id VARCHAR(64) NULL', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'prediction_shared');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN prediction_shared BOOLEAN NOT NULL DEFAULT FALSE', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'serpapi_label_status');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN serpapi_label_status VARCHAR(32) NULL', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'has_popular_times');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN has_popular_times BOOLEAN NOT NULL DEFAULT FALSE', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'ml_eligible');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN ml_eligible BOOLEAN NOT NULL DEFAULT FALSE', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;

SET @column_exists := (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'serpapi_checked_at');
SET @migration_sql := IF(@column_exists = 0, 'ALTER TABLE venues ADD COLUMN serpapi_checked_at VARCHAR(32) NULL', 'SELECT 1');
PREPARE add_venues_column FROM @migration_sql;
EXECUTE add_venues_column;
DEALLOCATE PREPARE add_venues_column;
