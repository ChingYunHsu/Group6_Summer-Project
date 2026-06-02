CREATE DATABASE IF NOT EXISTS clearpath
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE clearpath;

CREATE TABLE IF NOT EXISTS venues (
  venue_id VARCHAR(36) PRIMARY KEY,
  venue_type ENUM('restroom', 'healthcare', 'emergency_asset') NOT NULL,
  name VARCHAR(255) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  borough VARCHAR(64),
  address VARCHAR(512),
  phone VARCHAR(64),
  website VARCHAR(512),
  opening_hours VARCHAR(512),
  source_confidence DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CHECK (source_confidence >= 0 AND source_confidence <= 1),
  INDEX idx_venues_type (venue_type),
  INDEX idx_venues_location (latitude, longitude),
  INDEX idx_venues_borough (borough)
);

CREATE TABLE IF NOT EXISTS venue_source_links (
  source_link_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  source_name VARCHAR(128) NOT NULL,
  source_record_id VARCHAR(128),
  raw_name VARCHAR(255),
  raw_location_text VARCHAR(512),
  matched_method ENUM('exact_source_id', 'name_coordinate', 'name_address', 'manual_review', 'single_source') NOT NULL,
  match_confidence DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_source_link_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  CHECK (match_confidence >= 0 AND match_confidence <= 1),
  UNIQUE KEY uq_source_record (source_name, source_record_id),
  INDEX idx_source_links_venue (venue_id),
  INDEX idx_source_links_source (source_name)
);

CREATE TABLE IF NOT EXISTS restroom_profiles (
  venue_id VARCHAR(36) PRIMARY KEY,
  restroom_type VARCHAR(128),
  operator VARCHAR(255),
  status VARCHAR(128),
  open_seasonal BOOLEAN,
  open_year_round BOOLEAN,
  ada_accessible BOOLEAN,
  handicap_accessible BOOLEAN,
  changing_station BOOLEAN,
  additional_notes TEXT,
  CONSTRAINT fk_restroom_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS healthcare_profiles (
  venue_id VARCHAR(36) PRIMARY KEY,
  facility_external_id VARCHAR(128),
  facility_type VARCHAR(255),
  healthcare_category VARCHAR(128),
  healthcare_speciality VARCHAR(255),
  operator_name VARCHAR(255),
  ownership_type VARCHAR(128),
  main_site_name VARCHAR(255),
  official_source_priority TINYINT UNSIGNED NOT NULL DEFAULT 2,
  CONSTRAINT fk_healthcare_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  INDEX idx_healthcare_external_id (facility_external_id),
  INDEX idx_healthcare_category (healthcare_category)
);

CREATE TABLE IF NOT EXISTS emergency_assets (
  asset_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  asset_type ENUM('aed') NOT NULL DEFAULT 'aed',
  floor VARCHAR(128),
  location_type VARCHAR(128),
  aed_count INT UNSIGNED,
  trained_people_count INT UNSIGNED,
  community_district VARCHAR(64),
  council_district VARCHAR(64),
  last_updated DATE,
  CONSTRAINT fk_emergency_asset_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  INDEX idx_emergency_assets_venue (venue_id),
  INDEX idx_emergency_assets_type (asset_type)
);

CREATE TABLE IF NOT EXISTS pedestrian_ramps (
  ramp_id VARCHAR(128) PRIMARY KEY,
  corner_id VARCHAR(128),
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  borough VARCHAR(64),
  on_street VARCHAR(255),
  cross_street_1 VARCHAR(255),
  cross_street_2 VARCHAR(255),
  ramp_width DECIMAL(8, 3),
  ramp_slope DECIMAL(8, 3),
  dws_condition VARCHAR(128),
  ponding VARCHAR(128),
  obstacles_ramp VARCHAR(255),
  obstacles_landing VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_pedestrian_ramps_location (latitude, longitude),
  INDEX idx_pedestrian_ramps_borough (borough)
);

CREATE TABLE IF NOT EXISTS user_reports (
  report_id VARCHAR(36) PRIMARY KEY,
  venue_id VARCHAR(36),
  issue_type ENUM(
    'elevator_broken',
    'wheelchair_lift_broken',
    'toilet_out_of_order',
    'large_crowd',
    'protest_or_blockage',
    'entrance_closed'
  ) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  accuracy_meters DECIMAL(8, 2),
  status ENUM('active', 'resolved', 'expired') NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  source_confidence DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
  CONSTRAINT fk_user_report_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE SET NULL,
  CHECK (source_confidence >= 0 AND source_confidence <= 1),
  INDEX idx_user_reports_venue_status (venue_id, status),
  INDEX idx_user_reports_status_expiry (status, expires_at),
  INDEX idx_user_reports_location (latitude, longitude)
);

CREATE TABLE IF NOT EXISTS report_confirmations (
  confirmation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  report_id VARCHAR(36) NOT NULL,
  action ENUM('still_here', 'resolved', 'not_sure', 'still_out_of_order', 'open_now') NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  client_context JSON,
  CONSTRAINT fk_report_confirmation_report FOREIGN KEY (report_id) REFERENCES user_reports (report_id) ON DELETE CASCADE,
  INDEX idx_report_confirmations_report (report_id),
  INDEX idx_report_confirmations_action (action)
);

CREATE TABLE IF NOT EXISTS busyness_scores (
  score_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  score TINYINT UNSIGNED NOT NULL,
  level ENUM('low', 'medium', 'high', 'unknown') NOT NULL DEFAULT 'unknown',
  estimated_wait_minutes INT UNSIGNED,
  forecast_start_time DATETIME NOT NULL,
  forecast_end_time DATETIME NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  features_snapshot_id VARCHAR(128),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_busyness_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  CHECK (score <= 100),
  INDEX idx_busyness_venue_time (venue_id, forecast_start_time, forecast_end_time),
  INDEX idx_busyness_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS external_context_cache (
  cache_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  context_type ENUM('google_route', 'distance_matrix', 'weather_current', 'weather_forecast', 'urban_heat_static') NOT NULL,
  venue_id VARCHAR(36),
  request_key VARCHAR(255) NOT NULL,
  payload_json JSON NOT NULL,
  valid_from DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_external_context_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  UNIQUE KEY uq_context_request (context_type, request_key),
  INDEX idx_external_context_venue (venue_id),
  INDEX idx_external_context_expiry (context_type, expires_at)
);
