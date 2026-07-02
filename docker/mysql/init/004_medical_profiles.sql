-- ============================================================
-- ClearPath Database Schema — Phase 7: Medical Profile
-- Date: 2026-06-29
-- Purpose: Production storage for user Tier 2 medical data
-- ============================================================

USE clearpath;

-- -----------------------------------------------------------
-- medical_profiles — Encrypted medical information
-- One row per user; removing a user eradicates the profile through CASCADE.
-- ENCRYPTION='Y' requires MySQL keyring plugin (see docker-compose.yml)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS medical_profiles (
  user_id VARCHAR(36) PRIMARY KEY,
  date_of_birth DATE,
  gender VARCHAR(20),
  address TEXT,
  blood_type VARCHAR(10),
  severe_allergies JSON,
  conditions JSON,
  medications JSON,
  emergency_contacts JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_medical_profiles_user
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT chk_medical_profiles_severe_allergies_array
    CHECK (severe_allergies IS NULL OR JSON_TYPE(severe_allergies) = 'ARRAY'),
  CONSTRAINT chk_medical_profiles_conditions_array
    CHECK (conditions IS NULL OR JSON_TYPE(conditions) = 'ARRAY'),
  CONSTRAINT chk_medical_profiles_medications_array
    CHECK (medications IS NULL OR JSON_TYPE(medications) = 'ARRAY'),
  CONSTRAINT chk_medical_profiles_emergency_contacts_array
    CHECK (emergency_contacts IS NULL OR JSON_TYPE(emergency_contacts) = 'ARRAY')
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci
  ENCRYPTION='Y';
