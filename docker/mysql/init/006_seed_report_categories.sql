-- ============================================================
-- ClearPath Seed: report_categories (DB-2 / D8 issue-type dictionary)
-- Date: 2026-07-04
-- Purpose: Seed the report_categories dictionary so DB-backed report
--          inserts satisfy the fk_report_category FK constraint.
--          Aligns category_id values with the OpenAPI `ReportSubmission`
--          issue_type enum (9 entries) and the backend ALLOWED_REPORT_TYPES.
--
-- Source of truth for the id<->label mapping is openapi.yaml
-- (ReportSubmission / Report.issue_type_label). Keep this file in sync.
-- ============================================================

USE clearpath;

INSERT INTO report_categories
  (category_id, display_name, applies_to_venue_types, requires_floor_info, icon_name, sort_order, is_active)
VALUES
  ('elevator_broken',        'Lift Broken',            JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'elevator',         1, TRUE),
  ('wheelchair_lift_broken', 'Wheelchair Lift Broken', JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'wheelchair_lift',  2, TRUE),
  ('toilet_out_of_order',    'Toilet out of service',  JSON_ARRAY('restroom'),                                              FALSE, 'toilet',           3, TRUE),
  ('large_crowd',            'Too Crowded',            JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'crowd',            4, TRUE),
  ('long_waiting_time',      'Long Waiting Time',      JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'clock',            5, TRUE),
  ('protest_or_blockage',    'Protest / Blockage',     JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'protest',          6, TRUE),
  ('entrance_closed',        'Entrance Blocked',       JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'entrance',         7, TRUE),
  ('ramp_blocked',           'Ramp Blocked',           JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'ramp',             8, TRUE),
  ('closed_early',           'Closed Early',           JSON_ARRAY('healthcare','clinic','hospital','pharmacy','restroom'), FALSE, 'closed',           9, TRUE)
ON DUPLICATE KEY UPDATE
  display_name        = VALUES(display_name),
  applies_to_venue_types = VALUES(applies_to_venue_types),
  requires_floor_info = VALUES(requires_floor_info),
  icon_name           = VALUES(icon_name),
  sort_order          = VALUES(sort_order),
  is_active           = TRUE;
