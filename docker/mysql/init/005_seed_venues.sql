-- ============================================================
-- ClearPath Local Test Seed: Venues
-- Date: 2026-06-29
-- Purpose: Baseline non-empty venue snapshot for local containers
--          and automated regression tests only.
--
-- This file is not an ETL source of truth. Production and staged
-- venue data must continue to come from the primary ETL pipeline.
-- Keep this snapshot small, static, deterministic, and insert-only.
-- ============================================================

USE clearpath;

-- -----------------------------------------------------------
-- venues: fixed local/regression rows for map and integration checks
-- -----------------------------------------------------------
INSERT IGNORE INTO venues (
  venue_id,
  venue_type,
  name,
  latitude,
  longitude,
  borough,
  address,
  phone,
  website,
  opening_hours,
  photos,
  rating,
  weather_risk,
  source_confidence,
  language_tags,
  primary_language,
  secondary_language,
  accessible_status,
  accessibility_features,
  active_warning,
  open_now,
  district
) VALUES
  (
    'seed-restroom-bryant-park-001',
    'restroom',
    'Bryant Park Public Restroom',
    40.7535970,
    -73.9832330,
    'Manhattan',
    'Bryant Park, New York, NY 10018',
    NULL,
    'https://bryantpark.org',
    'Daily 8:00-22:00',
    JSON_ARRAY(),
    4.60,
    'low',
    0.950,
    JSON_ARRAY('en', 'es'),
    'en',
    'es',
    'full_access',
    JSON_ARRAY('accessible_toilet', 'step_free_route'),
    FALSE,
    TRUE,
    'MN05'
  ),
  (
    'seed-healthcare-bellevue-001',
    'healthcare',
    'Bellevue Hospital Center',
    40.7391830,
    -73.9766990,
    'Manhattan',
    '462 1st Ave, New York, NY 10016',
    '+1-212-562-4141',
    'https://www.nychealthandhospitals.org/bellevue/',
    '24 hours',
    JSON_ARRAY(),
    4.10,
    'medium',
    0.950,
    JSON_ARRAY('en', 'es', 'zh'),
    'en',
    'es',
    'partial',
    JSON_ARRAY('wheelchair_friendly', 'step_free_route'),
    FALSE,
    TRUE,
    'MN06'
  ),
  (
    'seed-pharmacy-cvs-midtown-001',
    'pharmacy',
    'CVS Pharmacy Midtown',
    40.7564090,
    -73.9855880,
    'Manhattan',
    '1569 Broadway, New York, NY 10036',
    '+1-212-302-7234',
    'https://www.cvs.com',
    'Daily 7:00-23:00',
    JSON_ARRAY(),
    4.00,
    'low',
    0.900,
    JSON_ARRAY('en'),
    'en',
    NULL,
    'partial',
    JSON_ARRAY('wheelchair_friendly'),
    FALSE,
    TRUE,
    'MN05'
  ),
  (
    'seed-aed-grand-central-001',
    'emergencyasset',
    'Grand Central Terminal AED',
    40.7527260,
    -73.9772290,
    'Manhattan',
    '89 E 42nd St, New York, NY 10017',
    NULL,
    'https://www.grandcentralterminal.com',
    'Terminal hours',
    JSON_ARRAY(),
    NULL,
    'low',
    0.900,
    JSON_ARRAY('en'),
    'en',
    NULL,
    'full_access',
    JSON_ARRAY('step_free_route'),
    FALSE,
    TRUE,
    'MN06'
  ),
  (
    'seed-clinic-brooklyn-001',
    'clinic',
    'Brooklyn Community Clinic',
    40.6895310,
    -73.9817340,
    'Brooklyn',
    '300 Cadman Plaza W, Brooklyn, NY 11201',
    '+1-718-555-0100',
    NULL,
    'Mon-Fri 9:00-17:00',
    JSON_ARRAY(),
    4.20,
    'low',
    0.850,
    JSON_ARRAY('en', 'es'),
    'en',
    'es',
    'partial',
    JSON_ARRAY('wheelchair_friendly'),
    FALSE,
    TRUE,
    'BK02'
  );

-- -----------------------------------------------------------
-- venue_source_links: explicitly identify rows as local snapshots
-- -----------------------------------------------------------
INSERT IGNORE INTO venue_source_links (
  venue_id,
  source_name,
  source_record_id,
  raw_name,
  raw_location_text,
  matched_method,
  match_confidence
) VALUES
  (
    'seed-restroom-bryant-park-001',
    'local_test_snapshot',
    'venue-seed-001',
    'Bryant Park Public Restroom',
    'Bryant Park, New York, NY 10018',
    'manual_review',
    0.950
  ),
  (
    'seed-healthcare-bellevue-001',
    'local_test_snapshot',
    'venue-seed-002',
    'Bellevue Hospital Center',
    '462 1st Ave, New York, NY 10016',
    'manual_review',
    0.950
  ),
  (
    'seed-pharmacy-cvs-midtown-001',
    'local_test_snapshot',
    'venue-seed-003',
    'CVS Pharmacy Midtown',
    '1569 Broadway, New York, NY 10036',
    'manual_review',
    0.900
  ),
  (
    'seed-aed-grand-central-001',
    'local_test_snapshot',
    'venue-seed-004',
    'Grand Central Terminal AED',
    '89 E 42nd St, New York, NY 10017',
    'manual_review',
    0.900
  ),
  (
    'seed-clinic-brooklyn-001',
    'local_test_snapshot',
    'venue-seed-005',
    'Brooklyn Community Clinic',
    '300 Cadman Plaza W, Brooklyn, NY 11201',
    'manual_review',
    0.850
  );

-- -----------------------------------------------------------
-- live_capacity source links: wire run_live_telemetry.py --mock payloads
-- (source_name='live_capacity', source_venue_id v_1001/v_1002) to seed
-- venues so telemetry --execute smoke tests resolve instead of going unmatched.
-- -----------------------------------------------------------
INSERT IGNORE INTO venue_source_links (
  venue_id,
  source_name,
  source_record_id,
  raw_name,
  raw_location_text,
  matched_method,
  match_confidence
) VALUES
  (
    'seed-restroom-bryant-park-001',
    'live_capacity',
    'v_1001',
    'Bryant Park Public Restroom',
    'Bryant Park, New York, NY 10018',
    'single_source',
    0.900
  ),
  (
    'seed-healthcare-bellevue-001',
    'live_capacity',
    'v_1002',
    'Bellevue Hospital Center',
    '462 1st Ave, New York, NY 10016',
    'single_source',
    0.900
  );

-- -----------------------------------------------------------
-- domain profiles: enough relational shape for mapping verification
-- -----------------------------------------------------------
INSERT IGNORE INTO restroom_profiles (
  venue_id,
  restroom_type,
  operator,
  status,
  open_seasonal,
  open_year_round,
  ada_accessible,
  handicap_accessible,
  changing_station,
  additional_notes
) VALUES (
  'seed-restroom-bryant-park-001',
  'public',
  'Bryant Park Corporation',
  'open',
  FALSE,
  TRUE,
  TRUE,
  TRUE,
  TRUE,
  'Static local regression seed; not an ETL source.'
);

INSERT IGNORE INTO healthcare_profiles (
  venue_id,
  facility_external_id,
  facility_type,
  healthcare_category,
  healthcare_speciality,
  operator_name,
  ownership_type,
  main_site_name,
  official_source_priority
) VALUES
  (
    'seed-healthcare-bellevue-001',
    'LOCAL-SEED-HOSPITAL-001',
    'Hospital',
    'Emergency care',
    'General hospital',
    'NYC Health + Hospitals',
    'Public',
    'Bellevue Hospital Center',
    1
  ),
  (
    'seed-pharmacy-cvs-midtown-001',
    'LOCAL-SEED-PHARMACY-001',
    'Pharmacy',
    'Medication access',
    'Retail pharmacy',
    'CVS Pharmacy',
    'Private',
    'CVS Pharmacy Midtown',
    3
  ),
  (
    'seed-clinic-brooklyn-001',
    'LOCAL-SEED-CLINIC-001',
    'Clinic',
    'Primary care',
    'Community clinic',
    'Brooklyn Community Clinic',
    'Community',
    'Brooklyn Community Clinic',
    2
  );

INSERT IGNORE INTO emergency_assets (
  venue_id,
  asset_type,
  floor,
  location_type,
  aed_count,
  trained_people_count,
  community_district,
  council_district,
  last_updated
) VALUES (
  'seed-aed-grand-central-001',
  'aed',
  'Main Concourse',
  'transit_terminal',
  1,
  NULL,
  'MN06',
  '4',
  '2026-06-29'
);
