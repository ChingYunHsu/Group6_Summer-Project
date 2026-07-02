-- ============================================================
-- Migration: Add user profile fields (phone, nationality, spoken_languages)
-- Date: 2026-06-29
-- Depends on: 001_clearpath_schema.sql (users table)
-- ============================================================

USE clearpath;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS phone VARCHAR(64) NULL AFTER display_name,
  ADD COLUMN IF NOT EXISTS nationality VARCHAR(128) NULL AFTER phone,
  ADD COLUMN IF NOT EXISTS spoken_languages JSON NULL AFTER nationality;
