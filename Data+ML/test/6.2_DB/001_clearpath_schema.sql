CREATE DATABASE IF NOT EXISTS clearpath
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE clearpath;

CREATE TABLE `busyness_scores` (
  `score_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `venue_id` varchar(36) NOT NULL,
  `score` tinyint unsigned NOT NULL,
  `level` enum('low','medium','high','unknown') NOT NULL DEFAULT 'unknown',
  `estimated_wait_minutes` int unsigned DEFAULT NULL,
  `forecast_1h` json DEFAULT NULL COMMENT '12-hour forecast array [h0..h11]',
  `forecast_start_time` datetime NOT NULL,
  `forecast_end_time` datetime NOT NULL,
  `model_version` varchar(64) NOT NULL,
  `features_snapshot_id` varchar(128) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`score_id`),
  KEY `idx_busyness_venue_time` (`venue_id`,`forecast_start_time`,`forecast_end_time`),
  KEY `idx_busyness_created_at` (`created_at`),
  CONSTRAINT `fk_busyness_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE,
  CONSTRAINT `busyness_scores_chk_1` CHECK ((`score` <= 100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `emergency_assets` (
  `asset_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `venue_id` varchar(36) NOT NULL,
  `asset_type` enum('aed') NOT NULL DEFAULT 'aed',
  `floor` varchar(128) DEFAULT NULL,
  `location_type` varchar(128) DEFAULT NULL,
  `aed_count` int unsigned DEFAULT NULL,
  `trained_people_count` int unsigned DEFAULT NULL,
  `community_district` varchar(64) DEFAULT NULL,
  `council_district` varchar(64) DEFAULT NULL,
  `last_updated` date DEFAULT NULL,
  PRIMARY KEY (`asset_id`),
  KEY `idx_emergency_assets_venue` (`venue_id`),
  KEY `idx_emergency_assets_type` (`asset_type`),
  CONSTRAINT `fk_emergency_asset_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1776 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `external_context_cache` (
  `cache_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `context_type` enum('google_route','distance_matrix','weather_current','weather_forecast','urban_heat_static') NOT NULL,
  `venue_id` varchar(36) DEFAULT NULL,
  `request_key` varchar(255) NOT NULL,
  `payload_json` json NOT NULL,
  `valid_from` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`cache_id`),
  UNIQUE KEY `uq_context_request` (`context_type`,`request_key`),
  KEY `idx_external_context_venue` (`venue_id`),
  KEY `idx_external_context_expiry` (`context_type`,`expires_at`),
  CONSTRAINT `fk_external_context_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `healthcare_profiles` (
  `venue_id` varchar(36) NOT NULL,
  `facility_external_id` varchar(128) DEFAULT NULL,
  `facility_type` varchar(255) DEFAULT NULL,
  `healthcare_category` varchar(128) DEFAULT NULL,
  `healthcare_speciality` varchar(255) DEFAULT NULL,
  `operator_name` varchar(255) DEFAULT NULL,
  `ownership_type` varchar(128) DEFAULT NULL,
  `main_site_name` varchar(255) DEFAULT NULL,
  `official_source_priority` tinyint unsigned NOT NULL DEFAULT '2',
  PRIMARY KEY (`venue_id`),
  KEY `idx_healthcare_external_id` (`facility_external_id`),
  KEY `idx_healthcare_category` (`healthcare_category`),
  CONSTRAINT `fk_healthcare_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `pedestrian_ramps` (
  `ramp_id` varchar(128) NOT NULL,
  `corner_id` varchar(128) DEFAULT NULL,
  `latitude` decimal(10,7) NOT NULL,
  `longitude` decimal(10,7) NOT NULL,
  `borough` varchar(64) DEFAULT NULL,
  `on_street` varchar(255) DEFAULT NULL,
  `cross_street_1` varchar(255) DEFAULT NULL,
  `cross_street_2` varchar(255) DEFAULT NULL,
  `ramp_width` decimal(8,3) DEFAULT NULL,
  `ramp_slope` decimal(8,3) DEFAULT NULL,
  `dws_condition` varchar(128) DEFAULT NULL,
  `ponding` varchar(128) DEFAULT NULL,
  `obstacles_ramp` varchar(255) DEFAULT NULL,
  `obstacles_landing` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`ramp_id`),
  KEY `idx_pedestrian_ramps_location` (`latitude`,`longitude`),
  KEY `idx_pedestrian_ramps_borough` (`borough`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `report_confirmations` (
  `confirmation_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `report_id` varchar(36) NOT NULL,
  `action` enum('still_here','resolved','not_sure','still_out_of_order','open_now') NOT NULL,
  `language` varchar(10) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `client_context` json DEFAULT NULL,
  PRIMARY KEY (`confirmation_id`),
  KEY `idx_report_confirmations_report` (`report_id`),
  KEY `idx_report_confirmations_action` (`action`),
  CONSTRAINT `fk_report_confirmation_report` FOREIGN KEY (`report_id`) REFERENCES `user_reports` (`report_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `restroom_profiles` (
  `venue_id` varchar(36) NOT NULL,
  `restroom_type` varchar(128) DEFAULT NULL,
  `operator` varchar(255) DEFAULT NULL,
  `status` varchar(128) DEFAULT NULL,
  `open_seasonal` tinyint(1) DEFAULT NULL,
  `open_year_round` tinyint(1) DEFAULT NULL,
  `ada_accessible` tinyint(1) DEFAULT NULL,
  `handicap_accessible` tinyint(1) DEFAULT NULL,
  `changing_station` tinyint(1) DEFAULT NULL,
  `additional_notes` text,
  PRIMARY KEY (`venue_id`),
  CONSTRAINT `fk_restroom_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_reports` (
  `report_id` varchar(36) NOT NULL,
  `venue_id` varchar(36) DEFAULT NULL,
  `issue_type` enum('elevator_broken','wheelchair_lift_broken','toilet_out_of_order','large_crowd','protest_or_blockage','entrance_closed') NOT NULL,
  `latitude` decimal(10,7) NOT NULL,
  `longitude` decimal(10,7) NOT NULL,
  `accuracy_meters` decimal(8,2) DEFAULT NULL,
  `anonymous` tinyint(1) DEFAULT '0',
  `description` text,
  `photos` json DEFAULT NULL,
  `reported_by` varchar(50) DEFAULT 'anonymous',
  `status` enum('active','resolved','expired') NOT NULL DEFAULT 'active',
  `expires_in_minutes` int DEFAULT '120',
  `default_language` varchar(10) DEFAULT NULL,
  `fallback_language` varchar(10) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NOT NULL,
  `source_confidence` decimal(4,3) NOT NULL DEFAULT '0.500',
  PRIMARY KEY (`report_id`),
  KEY `idx_user_reports_venue_status` (`venue_id`,`status`),
  KEY `idx_user_reports_status_expiry` (`status`,`expires_at`),
  KEY `idx_user_reports_location` (`latitude`,`longitude`),
  CONSTRAINT `fk_user_report_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE SET NULL,
  CONSTRAINT `user_reports_chk_1` CHECK (((`source_confidence` >= 0) and (`source_confidence` <= 1)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `venue_accessibility` (
  `venue_id` varchar(36) NOT NULL,
  `wheelchair_friendly` tinyint(1) DEFAULT '0',
  `step_free_route` tinyint(1) DEFAULT '0',
  `accessible_toilet` tinyint(1) DEFAULT '0',
  `entrance_width_cm` int DEFAULT NULL,
  PRIMARY KEY (`venue_id`),
  CONSTRAINT `fk_accessibility_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `venue_language` (
  `venue_id` varchar(36) NOT NULL,
  `language_tag` json DEFAULT NULL,
  `language_support_level` enum('full','partial','none') DEFAULT 'none',
  `chatbot_enabled` tinyint(1) DEFAULT '0',
  `chatbot_welcoming_message` text,
  PRIMARY KEY (`venue_id`),
  CONSTRAINT `fk_language_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `venue_source_links` (
  `source_link_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `venue_id` varchar(36) NOT NULL,
  `source_name` varchar(128) NOT NULL,
  `source_record_id` varchar(128) DEFAULT NULL,
  `raw_name` varchar(255) DEFAULT NULL,
  `raw_location_text` varchar(512) DEFAULT NULL,
  `matched_method` enum('exact_source_id','name_coordinate','name_address','manual_review','single_source') NOT NULL,
  `match_confidence` decimal(4,3) NOT NULL DEFAULT '0.500',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`source_link_id`),
  UNIQUE KEY `uq_source_record` (`source_name`,`source_record_id`),
  KEY `idx_source_links_venue` (`venue_id`),
  KEY `idx_source_links_source` (`source_name`),
  CONSTRAINT `fk_source_link_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE,
  CONSTRAINT `venue_source_links_chk_1` CHECK (((`match_confidence` >= 0) and (`match_confidence` <= 1)))
) ENGINE=InnoDB AUTO_INCREMENT=3484 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `venue_warnings` (
  `venue_id` varchar(36) NOT NULL,
  `active_warning` tinyint(1) DEFAULT '0',
  `warning_detail` text,
  `wait_alert` tinyint(1) DEFAULT '0',
  `replacement_suggestion` json DEFAULT NULL,
  PRIMARY KEY (`venue_id`),
  CONSTRAINT `fk_warnings_venue` FOREIGN KEY (`venue_id`) REFERENCES `venues` (`venue_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `venues` (
  `venue_id` varchar(36) NOT NULL,
  `venue_type` enum('restroom','healthcare','emergency_asset','clinic','pharmacy','hospital','dentist','laboratory') NOT NULL,
  `name` varchar(255) NOT NULL,
  `latitude` decimal(10,7) NOT NULL,
  `longitude` decimal(10,7) NOT NULL,
  `borough` varchar(64) DEFAULT NULL,
  `language_tags` json DEFAULT NULL,
  `primary_language` varchar(10) DEFAULT NULL,
  `secondary_language` varchar(10) DEFAULT NULL,
  `accessible_status` enum('full_access','partial','step_free_route_only','none') DEFAULT 'none',
  `accessibility_features` json DEFAULT NULL,
  `active_warning` tinyint(1) DEFAULT '0',
  `open_now` tinyint(1) DEFAULT '1',
  `address` varchar(512) DEFAULT NULL,
  `phone` varchar(64) DEFAULT NULL,
  `website` varchar(512) DEFAULT NULL,
  `opening_hours` varchar(512) DEFAULT NULL,
  `photos` json DEFAULT NULL,
  `rating` decimal(3,2) DEFAULT NULL,
  `weather_risk` enum('low','medium','high') DEFAULT 'low',
  `source_confidence` decimal(4,3) NOT NULL DEFAULT '0.500',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`venue_id`),
  KEY `idx_venues_type` (`venue_type`),
  KEY `idx_venues_location` (`latitude`,`longitude`),
  KEY `idx_venues_borough` (`borough`),
  CONSTRAINT `venues_chk_1` CHECK (((`source_confidence` >= 0) and (`source_confidence` <= 1)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

