-- ============================================================
-- ClearPath Database Schema
-- Date: 2026-06-03
-- Synced from: [CN]fix_plan.md + [CN]api_schema_gap_analysis_cn.md
-- ============================================================

CREATE DATABASE IF NOT EXISTS clearpath
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE clearpath;

-- -----------------------------------------------------------
-- venues — Unified POI table (restrooms, healthcare, AED, etc.)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS venues (
  venue_id VARCHAR(36) PRIMARY KEY,
  venue_type ENUM(
    'restroom', 'healthcare', 'emergencyasset',
    'clinic', 'pharmacy', 'hospital', 'dentist', 'laboratory'
  ) NOT NULL,
  name VARCHAR(255) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  borough VARCHAR(64),
  address VARCHAR(512),
  phone VARCHAR(64),
  website VARCHAR(512),
  opening_hours VARCHAR(512),
  -- Gap-fix: photos, rating, weather_risk
  photos JSON,
  rating DECIMAL(3,2),
  weather_risk ENUM('low', 'medium', 'high') DEFAULT 'low',
  source_confidence DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
  -- Gap-fix: language support
  language_tags JSON,
  primary_language VARCHAR(10),
  secondary_language VARCHAR(10),
  -- Gap-fix: accessibility
  accessible_status ENUM('full_access', 'partial', 'step_free_route_only', 'none') DEFAULT 'none',
  accessibility_features JSON,
  -- Gap-fix: warnings
  active_warning BOOLEAN DEFAULT FALSE,
  open_now BOOLEAN DEFAULT TRUE,
  district VARCHAR(32),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CHECK (source_confidence >= 0 AND source_confidence <= 1),
  INDEX idx_venues_type (venue_type),
  INDEX idx_venues_location (latitude, longitude),
  INDEX idx_venues_borough (borough)
);

-- -----------------------------------------------------------
-- venue_source_links — Maps venues to original data sources
-- -----------------------------------------------------------
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

-- -----------------------------------------------------------
-- restroom_profiles — Extended restroom details
-- -----------------------------------------------------------
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

-- -----------------------------------------------------------
-- healthcare_profiles — Extended healthcare details
-- -----------------------------------------------------------
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

-- -----------------------------------------------------------
-- emergency_assets — AED-specific data
-- -----------------------------------------------------------
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
  UNIQUE KEY uq_emergency_asset_natural (venue_id, floor, location_type),
  CONSTRAINT fk_emergency_asset_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  INDEX idx_emergency_assets_venue (venue_id),
  INDEX idx_emergency_assets_type (asset_type)
);

-- -----------------------------------------------------------
-- pedestrian_ramps — Accessibility ramp data
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedestrian_ramps (
  ramp_id VARCHAR(128) PRIMARY KEY,
  corner_id VARCHAR(128),
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  borough VARCHAR(64),
  district VARCHAR(32),
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

-- -----------------------------------------------------------
-- users — Account base (D10: no medical data on server)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  user_id VARCHAR(36) PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  phone VARCHAR(64),
  nationality VARCHAR(128),
  spoken_languages JSON,
  email_verified BOOLEAN DEFAULT FALSE,
  preferred_language VARCHAR(10) DEFAULT 'en',
  account_status ENUM('active','suspended','deleted') DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  INDEX idx_users_email (email)
);

-- -----------------------------------------------------------
-- report_categories — Issue type dictionary (D8)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_categories (
  category_id VARCHAR(64) PRIMARY KEY,
  display_name VARCHAR(128) NOT NULL,
  applies_to_venue_types JSON NOT NULL,
  requires_floor_info BOOLEAN DEFAULT FALSE,
  icon_name VARCHAR(64),
  sort_order TINYINT UNSIGNED DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE
);

-- -----------------------------------------------------------
-- user_reports — Crowd-sourced incident reports
-- Phase 3: Added user_id FK (D3), issue_type → VARCHAR + FK
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_reports (
  report_id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  venue_id VARCHAR(36),
  issue_type VARCHAR(64) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  accuracy_meters DECIMAL(8, 2),
  anonymous BOOLEAN DEFAULT FALSE,
  description TEXT,
  photos JSON,
  reported_by VARCHAR(50) DEFAULT 'anonymous',
  status ENUM('active', 'resolved', 'expired') NOT NULL DEFAULT 'active',
  expires_in_minutes INT DEFAULT 120,
  default_language VARCHAR(10),
  fallback_language VARCHAR(10),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  source_confidence DECIMAL(4, 3) NOT NULL DEFAULT 0.500,
  CONSTRAINT fk_user_report_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_user_report_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE SET NULL,
  CONSTRAINT fk_report_category FOREIGN KEY (issue_type) REFERENCES report_categories(category_id),
  CHECK (source_confidence >= 0 AND source_confidence <= 1),
  INDEX idx_user_reports_venue_status (venue_id, status),
  INDEX idx_user_reports_status_expiry (status, expires_at),
  INDEX idx_user_reports_location (latitude, longitude)
);

-- -----------------------------------------------------------
-- report_confirmations — User votes on reports
-- Phase 3: Added user_id FK + UNIQUE constraint (D6)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_confirmations (
  confirmation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  report_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  action ENUM('still_here', 'resolved', 'not_sure', 'still_out_of_order', 'open_now') NOT NULL,
  language VARCHAR(10),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  client_context JSON,
  CONSTRAINT fk_report_confirmation_report FOREIGN KEY (report_id) REFERENCES user_reports (report_id) ON DELETE CASCADE,
  CONSTRAINT fk_confirmation_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  UNIQUE KEY uq_report_user (report_id, user_id),
  INDEX idx_report_confirmations_report (report_id),
  INDEX idx_report_confirmations_action (action)
);

-- -----------------------------------------------------------
-- busyness_scores — ML busyness predictions
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS busyness_scores (
  score_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  score TINYINT UNSIGNED NOT NULL,
  level ENUM('quiet','moderate','busy','no_data') DEFAULT NULL,
  estimated_wait_minutes INT UNSIGNED,
  -- Gap-fix: forecast columns
  forecast_1h JSON,
  forecast_start_time DATETIME NOT NULL,
  forecast_end_time DATETIME NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  features_snapshot_id VARCHAR(128),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_busyness_venue FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE,
  UNIQUE KEY uq_busyness_venue_time (venue_id, forecast_start_time, model_version),
  CHECK (score <= 100),
  INDEX idx_busyness_venue_time (venue_id, forecast_start_time, forecast_end_time),
  INDEX idx_busyness_created_at (created_at)
);

-- -----------------------------------------------------------
-- external_context_cache — Cached external API data
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS external_context_cache (
  cache_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  context_type ENUM('google_route', 'distance_matrix', 'weather_current', 'weather_forecast', 'urban_heat_static', 'public_holidays', 'gbfs_station_status', 'mta_realtime') NOT NULL,
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

-- -----------------------------------------------------------
-- NEW TABLES — Gap-fix additions (2026-06-03)
-- -----------------------------------------------------------

-- venue_accessibility — Detailed accessibility info per venue
CREATE TABLE IF NOT EXISTS venue_accessibility (
  venue_id VARCHAR(36) PRIMARY KEY,
  wheelchair_friendly BOOLEAN DEFAULT FALSE,
  step_free_route BOOLEAN DEFAULT FALSE,
  accessible_toilet BOOLEAN DEFAULT FALSE,
  entrance_width_cm INT,
  CONSTRAINT fk_accessibility_venue
    FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE
);

-- venue_language — Multilingual support per venue
CREATE TABLE IF NOT EXISTS venue_language (
  venue_id VARCHAR(36) PRIMARY KEY,
  language_tag JSON,
  language_support_level ENUM('full', 'partial', 'none') DEFAULT 'none',
  chatbot_enabled BOOLEAN DEFAULT FALSE,
  chatbot_welcoming_message TEXT,
  CONSTRAINT fk_language_venue
    FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE
);

-- venue_warnings — Active warnings and alerts per venue
CREATE TABLE IF NOT EXISTS venue_warnings (
  venue_id VARCHAR(36) PRIMARY KEY,
  active_warning BOOLEAN DEFAULT FALSE,
  warning_detail TEXT,
  wait_alert BOOLEAN DEFAULT FALSE,
  replacement_suggestion JSON,
  CONSTRAINT fk_warnings_venue
    FOREIGN KEY (venue_id) REFERENCES venues (venue_id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- NEW TABLES — Phase 2: User & Account System (2026-06-09)
-- D1: 邮箱+密码 (bcrypt), D2: Guest 无 token, D7: 邮箱即认证标识
-- -----------------------------------------------------------

-- user_favorite_venues — Cross-device venue bookmarks
CREATE TABLE IF NOT EXISTS user_favorite_venues (
  user_id VARCHAR(36) NOT NULL,
  venue_id VARCHAR(36) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, venue_id),
  CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_fav_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);

-- notification_preferences — Push subscriptions + quiet hours
CREATE TABLE IF NOT EXISTS notification_preferences (
  pref_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  venue_id VARCHAR(36),
  notification_type ENUM('crowd_alert','closure_alert','quiet_hours') NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  threshold TINYINT UNSIGNED,
  quiet_start TIME,
  quiet_end TIME,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_notif_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE,
  UNIQUE KEY uq_user_notif_type (user_id, venue_id, notification_type)
);

-- -----------------------------------------------------------
-- NEW TABLES — Phase 3: Report System (2026-06-09)
-- D5: OpenAPI 8 issue types, D8: 字典表按场馆类型过滤
-- -----------------------------------------------------------

-- -----------------------------------------------------------
-- NEW TABLES — Phase 4: Busyness Forecast (2026-06-09)
-- D4: 三级 quiet/moderate/busy, 12h time-series prediction
-- -----------------------------------------------------------

-- busyness_forecasts — Future 12h predictions (ML pipeline writes)
-- DB-3 write contract:
--   * unique key (venue_id, forecast_for, model_version) → idempotent upsert
--   * predicted_score bounded 0-100 (matches busyness_scores.score CHECK)
--   * predicted_level enum mirrors API level enum (quiet/moderate/busy/no_data)
--   * forecast_for = absolute future DATETIME (one row per future hour)
CREATE TABLE IF NOT EXISTS busyness_forecasts (
  forecast_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  forecast_for DATETIME NOT NULL,
  predicted_score TINYINT UNSIGNED NOT NULL,
  predicted_level ENUM('quiet','moderate','busy','no_data') NOT NULL,
  estimated_wait_minutes INT UNSIGNED,
  model_version VARCHAR(64) NOT NULL,
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_forecast (venue_id, forecast_for, model_version),
  INDEX idx_forecast_venue_time (venue_id, forecast_for),
  CONSTRAINT fk_forecast_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE,
  CHECK (predicted_score <= 100)
);

-- -----------------------------------------------------------
-- NEW TABLES — Phase 5: RAG Data Layer (2026-06-09)
-- D9: MySQL JSON/BLOB (~3500 venues)
-- -----------------------------------------------------------

-- venue_embeddings — Gemini embedding vectors for semantic search
CREATE TABLE IF NOT EXISTS venue_embeddings (
  venue_id VARCHAR(36) PRIMARY KEY,
  embedding JSON NOT NULL,
  text_snapshot TEXT NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_embedding_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- Phase 5: Additional indexes for RAG + search
-- -----------------------------------------------------------
CREATE INDEX idx_venues_district ON venues(district);
CREATE INDEX idx_venues_type_district ON venues(venue_type, district);
