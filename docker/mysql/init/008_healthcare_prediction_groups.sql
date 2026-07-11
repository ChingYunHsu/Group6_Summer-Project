-- ============================================================
-- ClearPath Schema: healthcare prediction groups
-- Purpose: make the healthcare ML grouping artifacts reproducible
-- ============================================================

USE clearpath;

-- A prediction group shares one upstream popular-times identity.  When no
-- upstream identity exists, the Data pipeline creates a venue-id singleton.
CREATE TABLE IF NOT EXISTS healthcare_prediction_groups (
  prediction_group_id VARCHAR(255) PRIMARY KEY,
  source_place_id VARCHAR(255) NULL,
  primary_venue_id VARCHAR(36) NOT NULL,
  group_type ENUM('shared_place', 'fallback_singleton') NOT NULL,
  prediction_source ENUM('serpapi_place_id', 'venue_id_fallback') NOT NULL,
  group_member_count INT UNSIGNED NOT NULL,
  has_popular_times BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_prediction_group_primary_venue
    FOREIGN KEY (primary_venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  CHECK (group_member_count >= 1),
  UNIQUE KEY uq_prediction_group_source_place (source_place_id),
  INDEX idx_prediction_groups_primary_venue (primary_venue_id)
);

CREATE TABLE IF NOT EXISTS healthcare_prediction_group_members (
  prediction_group_id VARCHAR(255) NOT NULL,
  venue_id VARCHAR(36) NOT NULL,
  source_place_id VARCHAR(255) NULL,
  prediction_shared BOOLEAN NOT NULL DEFAULT FALSE,
  label_status VARCHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (prediction_group_id, venue_id),
  UNIQUE KEY uq_prediction_group_member_venue (venue_id),
  CONSTRAINT fk_prediction_group_member_group
    FOREIGN KEY (prediction_group_id) REFERENCES healthcare_prediction_groups (prediction_group_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_prediction_group_member_venue
    FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  INDEX idx_prediction_group_members_group (prediction_group_id)
);
