-- Keep venues.venue_type aligned with the medical category already captured
-- in healthcare_profiles. Unknown categories intentionally remain healthcare.
USE clearpath;

UPDATE venues AS venue
JOIN healthcare_profiles AS profile ON profile.venue_id = venue.venue_id
SET venue.venue_type = profile.healthcare_category
WHERE venue.venue_type = 'healthcare'
  AND profile.healthcare_category IN (
    'hospital', 'clinic', 'pharmacy', 'dentist', 'laboratory'
  );
