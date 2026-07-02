-- ============================================================
-- Migration: Add user profile fields (phone, nationality, spoken_languages)
-- Date: 2026-06-29
-- Depends on: 001_clearpath_schema.sql (users table)
-- ============================================================

USE clearpath;

SET @has_users_phone := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'users'
    AND column_name = 'phone'
);

SET @add_users_phone := IF(
  @has_users_phone = 0,
  'ALTER TABLE users ADD COLUMN phone VARCHAR(64) NULL AFTER display_name',
  'SELECT ''users.phone already exists'' AS status'
);

PREPARE stmt FROM @add_users_phone;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_users_nationality := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'users'
    AND column_name = 'nationality'
);

SET @add_users_nationality := IF(
  @has_users_nationality = 0,
  'ALTER TABLE users ADD COLUMN nationality VARCHAR(128) NULL AFTER phone',
  'SELECT ''users.nationality already exists'' AS status'
);

PREPARE stmt FROM @add_users_nationality;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_users_spoken_languages := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'users'
    AND column_name = 'spoken_languages'
);

SET @add_users_spoken_languages := IF(
  @has_users_spoken_languages = 0,
  'ALTER TABLE users ADD COLUMN spoken_languages JSON NULL AFTER nationality',
  'SELECT ''users.spoken_languages already exists'' AS status'
);

PREPARE stmt FROM @add_users_spoken_languages;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
