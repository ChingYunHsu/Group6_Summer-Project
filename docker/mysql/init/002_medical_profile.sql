-- ============================================================
-- ClearPath Database Schema — Phase 7: Medical Profile
-- Date: 2026-06-23
-- Purpose: Encrypted storage for user Tier 2 medical data
-- ============================================================

USE clearpath;

-- -----------------------------------------------------------
-- user_medical_profiles — Encrypted medical information
-- ENCRYPTION='Y' requires MySQL keyring plugin (see docker-compose.yml)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_medical_profiles (
  user_id VARCHAR(36) PRIMARY KEY,
  blood_type VARCHAR(10),
  donor_status BOOLEAN DEFAULT FALSE,
  severe_allergies JSON,
  conditions JSON,
  medications JSON,
  emergency_contacts JSON,
  emergency_notes TEXT,
  medical_pass_title VARCHAR(128),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_medical_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENCRYPTION='Y';
