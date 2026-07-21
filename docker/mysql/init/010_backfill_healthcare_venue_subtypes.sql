-- Hospital-sponsored school health programmes are not acute-care hospitals.
-- Keep their source facility_type, but exclude them from the Hospital filter.
USE clearpath;

UPDATE venues AS venue
JOIN healthcare_profiles AS profile ON profile.venue_id = venue.venue_id
SET venue.venue_type = 'healthcare',
    profile.healthcare_category = 'healthcare'
WHERE UPPER(COALESCE(profile.facility_type, '')) LIKE '%HOSP-SB%';

-- Keep venues.venue_type aligned with recognised medical categories. Unknown
-- categories intentionally remain healthcare, including HOSP-SB above.
UPDATE venues AS venue
JOIN healthcare_profiles AS profile ON profile.venue_id = venue.venue_id
SET venue.venue_type = profile.healthcare_category
WHERE venue.venue_type = 'healthcare'
  AND profile.healthcare_category IN (
    'hospital', 'clinic', 'pharmacy', 'dentist', 'laboratory'
  )
  AND UPPER(COALESCE(profile.facility_type, '')) NOT LIKE '%HOSP-SB%';
