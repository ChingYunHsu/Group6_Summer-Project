-- Manhattan district seed data for the venues table (backing Week 2 map
-- integration tests). Coordinates are approximate real-world locations used
-- for lookup/filter testing, not verified clinical listings.
INSERT INTO venues (
    venue_id, name, venue_type, latitude, longitude, borough, address, phone,
    opening_hours, rating, primary_language, secondary_language, language_tags,
    chatbot_enabled, wheelchair_friendly, step_free_route, accessible_toilet,
    entrance_width_cm, accessible_status, accessibility_features,
    supported_services, open_now, data_confidence
) VALUES
(
    'venue_nyu_langone', 'NYU Langone Health', 'hospital', 40.742050, -73.974400,
    'Manhattan', '550 1st Ave, New York, NY 10016', '212-263-7300',
    '24/7', 4.3, 'EN', 'ES', JSON_ARRAY('EN', 'ES'),
    1, 1, 1, 1, 120, 'full_access',
    JSON_ARRAY('wheelchair_accessible_entrance', 'accessible_restroom'),
    JSON_ARRAY('Spanish Help Available', 'Bilingual Staff (Spanish)'),
    1, 'high'
),
(
    'venue_bellevue', 'Bellevue Hospital Center', 'hospital', 40.739250, -73.976020,
    'Manhattan', '462 1st Ave, New York, NY 10016', '212-562-4141',
    '24/7', 4.0, 'EN', 'ZH', JSON_ARRAY('EN', 'ZH', 'ES'),
    1, 1, 1, 1, 110, 'full_access',
    JSON_ARRAY('wheelchair_accessible_entrance', 'accessible_restroom', 'step_free_route'),
    JSON_ARRAY('Mandarin Help Available', 'Spanish Help Available'),
    1, 'high'
),
(
    'venue_cvs_23rd', 'CVS Pharmacy - 23rd St', 'pharmacy', 40.742900, -73.992200,
    'Manhattan', '253 W 23rd St, New York, NY 10011', '212-627-2222',
    '08:00-22:00', 3.8, 'EN', NULL, JSON_ARRAY('EN'),
    0, 0, 0, 0, NULL, 'no_access',
    JSON_ARRAY(),
    JSON_ARRAY(),
    1, 'medium'
),
(
    'venue_walgreens_union_sq', 'Walgreens - Union Square', 'pharmacy', 40.735980, -73.990730,
    'Manhattan', '883 Broadway, New York, NY 10003', '212-677-0054',
    '07:00-23:00', 4.1, 'EN', 'FR', JSON_ARRAY('EN', 'FR'),
    0, 1, 0, 0, 95, 'partial_access',
    JSON_ARRAY('wheelchair_accessible_entrance'),
    JSON_ARRAY('French Help Available'),
    1, 'medium'
),
(
    'venue_mount_sinai_urgent', 'Mount Sinai Urgent Care - Chelsea', 'urgent_care', 40.744500, -74.001900,
    'Manhattan', '325 W 15th St, New York, NY 10011', '212-604-8000',
    '08:00-20:00', 4.4, 'EN', 'FR', JSON_ARRAY('EN', 'FR', 'ES'),
    1, 1, 1, 1, 100, 'full_access',
    JSON_ARRAY('wheelchair_accessible_entrance', 'accessible_restroom'),
    JSON_ARRAY('French Help Available', 'Spanish Help Available'),
    0, 'high'
),
(
    'venue_ny_presbyterian_lower', 'NewYork-Presbyterian Lower Manhattan', 'hospital', 40.711000, -74.006500,
    'Manhattan', '170 William St, New York, NY 10038', '212-312-5000',
    '24/7', 4.2, 'EN', 'ZH', JSON_ARRAY('EN', 'ZH'),
    1, 1, 1, 1, 130, 'full_access',
    JSON_ARRAY('wheelchair_accessible_entrance', 'accessible_restroom', 'step_free_route'),
    JSON_ARRAY('Mandarin Help Available'),
    1, 'high'
),
(
    'venue_community_mh_eastside', 'East Side Community Mental Health Clinic', 'mental_health', 40.774100, -73.951500,
    'Manhattan', '1435 York Ave, New York, NY 10021', '212-746-0800',
    '09:00-18:00', 3.9, 'EN', 'ES', JSON_ARRAY('EN', 'ES'),
    1, 0, 0, 0, NULL, 'no_access',
    JSON_ARRAY(),
    JSON_ARRAY('Spanish Help Available'),
    0, 'medium'
),
(
    'venue_bowery_shelter', 'Bowery Mission Shelter', 'shelter', 40.719900, -73.993600,
    'Manhattan', '227 Bowery, New York, NY 10002', '212-674-3456',
    '24/7', 3.5, 'EN', NULL, JSON_ARRAY('EN'),
    0, 1, 1, 1, 90, 'full_access',
    JSON_ARRAY('wheelchair_accessible_entrance', 'accessible_restroom'),
    JSON_ARRAY(),
    1, 'low'
);
