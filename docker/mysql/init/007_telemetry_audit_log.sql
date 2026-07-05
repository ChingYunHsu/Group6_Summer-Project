-- ============================================================
-- ClearPath Schema: telemetry_audit_log (D3.1 audit trail)
-- Date: 2026-07-05
-- Purpose: Immutable audit log for live telemetry ingestion runs.
--   Each row = one batch execution of run_live_telemetry.py --execute.
-- ============================================================

USE clearpath;

CREATE TABLE IF NOT EXISTS telemetry_audit_log (
  audit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  run_at DATETIME NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  received INT UNSIGNED NOT NULL DEFAULT 0,
  rejected INT UNSIGNED NOT NULL DEFAULT 0,
  ingested INT UNSIGNED NOT NULL DEFAULT 0,
  unmatched INT UNSIGNED NOT NULL DEFAULT 0,
  unmatched_ids JSON,
  success BOOLEAN NOT NULL DEFAULT FALSE,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_run_at (run_at),
  INDEX idx_audit_model (model_version),
  INDEX idx_audit_success (success)
);
