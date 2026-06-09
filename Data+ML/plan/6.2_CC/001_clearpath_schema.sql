-- ============================================================
-- ClearPath Database Schema
-- Generated: 2026-06-02
-- MySQL 8.0+ / InnoDB / utf8mb4
-- ============================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================
-- Layer 1: POI 数据层
-- ============================================================

-- -----------------------------------------------------------
-- venues: Healthcare + AED 合并表
-- 数据来源: OSM Healthcare, NYS Health Facility, AED Inventory
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS venues (
    venue_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    venue_type      ENUM('clinic','hospital','pharmacy','urgent_care','dentist','lab','physiotherapy','aed') NOT NULL,
    lat             DECIMAL(10,7) NOT NULL,
    lng             DECIMAL(10,7) NOT NULL,
    address         VARCHAR(500),
    borough         VARCHAR(50),
    city            VARCHAR(100) DEFAULT 'Manhattan',
    zip_code        VARCHAR(10),
    phone           VARCHAR(30),
    website         VARCHAR(500),
    opening_hours   JSON,
    description     TEXT,

    -- 来源追踪
    source          ENUM('osm','nys_health','aed_inventory') NOT NULL,
    source_id       VARCHAR(100),
    data_confidence DECIMAL(3,2) DEFAULT 0.50,
    last_updated    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_payload_hash VARCHAR(64),

    -- NYS Health 特有
    facility_type   VARCHAR(100),
    operator_name   VARCHAR(255),
    ownership_type  VARCHAR(50),

    -- 索引
    INDEX idx_venue_type (venue_type),
    INDEX idx_borough (borough),
    INDEX idx_lat_lng (lat, lng),
    UNIQUE KEY uk_source (source, source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- toilets: NYC Public Restrooms + Parks Toilets 合并表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS toilets (
    toilet_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    lat             DECIMAL(10,7) NOT NULL,
    lng             DECIMAL(10,7) NOT NULL,
    address         VARCHAR(500),
    borough         VARCHAR(50),

    -- 设施信息
    restroom_type   VARCHAR(100),
    is_operational  BOOLEAN DEFAULT TRUE,
    accessibility   ENUM('accessible','partially_accessible','not_accessible','unknown') DEFAULT 'unknown',
    has_changing_station BOOLEAN DEFAULT FALSE,
    open_year_round BOOLEAN DEFAULT TRUE,
    hours_of_operation VARCHAR(255),
    operator        VARCHAR(100),
    additional_notes TEXT,
    website         VARCHAR(500),

    -- 来源追踪
    source          ENUM('nyc_restrooms','parks_toilets') NOT NULL,
    source_id       VARCHAR(100),
    data_confidence DECIMAL(3,2) DEFAULT 0.50,
    last_updated    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_payload_hash VARCHAR(64),

    -- 索引
    INDEX idx_borough (borough),
    INDEX idx_operational (is_operational),
    INDEX idx_accessibility (accessibility),
    INDEX idx_lat_lng (lat, lng),
    UNIQUE KEY uk_source (source, source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- accessibility_infrastructure: 无障碍设施表
-- 数据来源: Pedestrian Ramp Locations
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS accessibility_infrastructure (
    infra_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    infra_type      ENUM('pedestrian_ramp','elevator','escalator') DEFAULT 'pedestrian_ramp',
    lat             DECIMAL(10,7) NOT NULL,
    lng             DECIMAL(10,7) NOT NULL,
    borough         VARCHAR(50),
    street_name     VARCHAR(255),
    cross_street    VARCHAR(255),
    corner_id       VARCHAR(50),

    -- Ramp 质量
    condition       VARCHAR(50),
    ramp_slope      DECIMAL(5,2),
    cross_slope     DECIMAL(5,2),
    landing_width   DECIMAL(5,1),
    landing_length  DECIMAL(5,1),
    has_obstacles   BOOLEAN DEFAULT FALSE,
    has_ponding     BOOLEAN DEFAULT FALSE,

    -- 来源
    source          VARCHAR(50) DEFAULT 'nyc_ramps',
    source_id       VARCHAR(100),
    last_updated    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 索引
    INDEX idx_borough (borough),
    INDEX idx_condition (condition),
    INDEX idx_lat_lng (lat, lng),
    UNIQUE KEY uk_source (source, source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Layer 2: 实时交互层
-- ============================================================

-- -----------------------------------------------------------
-- reports: 用户报告表（P0 实时数据，2小时过期）
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    report_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_type     ENUM('elevator_broken','toilet_oos','crowding','protest','hazard','other') NOT NULL,
    venue_id        BIGINT,
    toilet_id       BIGINT,
    lat             DECIMAL(10,7) NOT NULL,
    lng             DECIMAL(10,7) NOT NULL,
    status          ENUM('active','confirmed','resolved','expired') DEFAULT 'active',
    reported_by     BIGINT,
    anonymous_flag  BOOLEAN DEFAULT FALSE,
    confirmation_count INT DEFAULT 0,
    expires_at      DATETIME NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_status (status),
    INDEX idx_type (report_type),
    INDEX idx_venue (venue_id),
    INDEX idx_toilet (toilet_id),
    INDEX idx_expires (expires_at),
    INDEX idx_lat_lng (lat, lng)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- busyness_predictions: ML 拥挤度预测表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS busyness_predictions (
    prediction_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    venue_id        BIGINT NOT NULL,

    -- 时间窗口
    prediction_date DATE NOT NULL,
    day_of_week     TINYINT NOT NULL COMMENT '0=Sun, 6=Sat',
    hour            TINYINT NOT NULL COMMENT '0-23',

    -- 预测值
    busyness_score  DECIMAL(5,2) COMMENT '0-100',
    estimated_wait_minutes INT,
    confidence      DECIMAL(3,2) COMMENT '0.00-1.00',

    -- 模型信息
    model_version   VARCHAR(50),
    feature_sources JSON COMMENT '["taxi","weather","reports"]',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_venue_time (venue_id, prediction_date, hour),
    INDEX idx_date_hour (prediction_date, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Layer 3: 用户层
-- ============================================================

-- -----------------------------------------------------------
-- users: 用户账户表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100),
    password_hash   VARCHAR(255) NOT NULL,
    language_preference VARCHAR(10) DEFAULT 'en',
    cloud_sync_consent BOOLEAN DEFAULT FALSE,
    notification_preferences JSON,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login      DATETIME,

    UNIQUE KEY uk_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- saved_venues: 用户收藏表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_venues (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    venue_id        BIGINT,
    toilet_id       BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    notification_enabled BOOLEAN DEFAULT TRUE,

    UNIQUE KEY uk_user_venue (user_id, venue_id),
    UNIQUE KEY uk_user_toilet (user_id, toilet_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Layer 4: 缓存层
-- ============================================================

-- -----------------------------------------------------------
-- traffic_cache: Google Maps 交通数据缓存
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS traffic_cache (
    cache_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    origin_lat      DECIMAL(10,7),
    origin_lng      DECIMAL(10,7),
    dest_lat        DECIMAL(10,7),
    dest_lng        DECIMAL(10,7),
    travel_mode     ENUM('driving','walking','transit','bicycling'),
    duration_seconds INT,
    distance_meters INT,
    traffic_level   ENUM('low','moderate','high','severe'),
    raw_response    JSON,
    fetched_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME,

    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- weather_cache: 天气数据缓存
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_cache (
    cache_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    location        VARCHAR(100) DEFAULT 'Manhattan',
    observation_time DATETIME NOT NULL,
    temperature_f   DECIMAL(5,1),
    humidity        DECIMAL(5,1),
    heat_index_f    DECIMAL(5,1),
    uv_index        DECIMAL(4,1),
    conditions      VARCHAR(100),
    raw_response    JSON,
    fetched_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME,

    INDEX idx_time (observation_time),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 外键约束（单独添加，便于数据导入时临时禁用）
-- ============================================================

-- reports → venues/toilets
ALTER TABLE reports
    ADD CONSTRAINT fk_report_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_report_toilet FOREIGN KEY (toilet_id) REFERENCES toilets(toilet_id) ON DELETE SET NULL;

-- busyness_predictions → venues
ALTER TABLE busyness_predictions
    ADD CONSTRAINT fk_busyness_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE;

-- saved_venues → users/venues/toilets
ALTER TABLE saved_venues
    ADD CONSTRAINT fk_saved_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_saved_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_saved_toilet FOREIGN KEY (toilet_id) REFERENCES toilets(toilet_id) ON DELETE CASCADE;
