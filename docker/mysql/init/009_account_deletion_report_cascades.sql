-- Make account deletion remove user-owned reports and confirmations.
-- This migration is safe to re-apply: it only changes an FK whose DELETE_RULE
-- is not already CASCADE, then adds it only when the cascade is absent.

SET @user_report_delete_rule := (
  SELECT DELETE_RULE
  FROM information_schema.REFERENTIAL_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'user_reports'
    AND CONSTRAINT_NAME = 'fk_user_report_user'
  LIMIT 1
);
SET @user_report_drop_sql := IF(
  @user_report_delete_rule IS NULL OR @user_report_delete_rule = 'CASCADE',
  'SELECT 1',
  'ALTER TABLE user_reports DROP FOREIGN KEY fk_user_report_user'
);
PREPARE user_report_drop FROM @user_report_drop_sql;
EXECUTE user_report_drop;
DEALLOCATE PREPARE user_report_drop;

SET @user_report_delete_rule := (
  SELECT DELETE_RULE
  FROM information_schema.REFERENTIAL_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'user_reports'
    AND CONSTRAINT_NAME = 'fk_user_report_user'
  LIMIT 1
);
SET @user_report_add_sql := IF(
  @user_report_delete_rule = 'CASCADE',
  'SELECT 1',
  'ALTER TABLE user_reports ADD CONSTRAINT fk_user_report_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE'
);
PREPARE user_report_add FROM @user_report_add_sql;
EXECUTE user_report_add;
DEALLOCATE PREPARE user_report_add;

SET @confirmation_delete_rule := (
  SELECT DELETE_RULE
  FROM information_schema.REFERENTIAL_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'report_confirmations'
    AND CONSTRAINT_NAME = 'fk_confirmation_user'
  LIMIT 1
);
SET @confirmation_drop_sql := IF(
  @confirmation_delete_rule IS NULL OR @confirmation_delete_rule = 'CASCADE',
  'SELECT 1',
  'ALTER TABLE report_confirmations DROP FOREIGN KEY fk_confirmation_user'
);
PREPARE confirmation_drop FROM @confirmation_drop_sql;
EXECUTE confirmation_drop;
DEALLOCATE PREPARE confirmation_drop;

SET @confirmation_delete_rule := (
  SELECT DELETE_RULE
  FROM information_schema.REFERENTIAL_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'report_confirmations'
    AND CONSTRAINT_NAME = 'fk_confirmation_user'
  LIMIT 1
);
SET @confirmation_add_sql := IF(
  @confirmation_delete_rule = 'CASCADE',
  'SELECT 1',
  'ALTER TABLE report_confirmations ADD CONSTRAINT fk_confirmation_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE'
);
PREPARE confirmation_add FROM @confirmation_add_sql;
EXECUTE confirmation_add;
DEALLOCATE PREPARE confirmation_add;
