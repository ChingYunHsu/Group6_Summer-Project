-- Reproducible local-demo accessibility fixture.
--
-- This deliberately supplies 200 *mock* medical wheelchair-support labels.
-- Hospitals are selected first, so every hospital in the current standard
-- snapshot is covered; remaining places are filled by other medical types.
-- It replaces only prior records explicitly
-- marked source=mock, leaving any verified OSM/NYS record untouched.
-- The deterministic ordering makes every standard venue snapshot reproduce
-- the same fixture cohort without requiring data_source or Jupyter.
USE clearpath;

START TRANSACTION;

DELETE accessibility
FROM venue_accessibility AS accessibility
JOIN venues AS venue ON venue.venue_id = accessibility.venue_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(venue.accessibility_features, '$.source')) = 'mock'
  AND JSON_EXTRACT(venue.accessibility_features, '$.mock_wheelchair_support') = TRUE;

UPDATE venues
SET accessible_status = 'unknown',
    accessibility_features = NULL
WHERE JSON_UNQUOTE(JSON_EXTRACT(accessibility_features, '$.source')) = 'mock'
  AND JSON_EXTRACT(accessibility_features, '$.mock_wheelchair_support') = TRUE;

DROP TEMPORARY TABLE IF EXISTS mock_medical_accessibility_seed;
CREATE TEMPORARY TABLE mock_medical_accessibility_seed AS
SELECT venue_id,
       'full_access' AS accessible_status,
       TRUE AS wheelchair_friendly
FROM (
    SELECT venue_id,
           ROW_NUMBER() OVER (
               ORDER BY CASE WHEN venue_type = 'hospital' THEN 0 ELSE 1 END, venue_id
           ) AS ordinal
    FROM venues
    WHERE venue_type IN ('healthcare', 'hospital', 'clinic', 'pharmacy', 'dentist', 'laboratory')
) AS ranked
WHERE ordinal <= 200;

INSERT INTO venue_accessibility (venue_id, wheelchair_friendly)
SELECT venue_id, wheelchair_friendly
FROM mock_medical_accessibility_seed
ON DUPLICATE KEY UPDATE wheelchair_friendly = VALUES(wheelchair_friendly);

UPDATE venues AS venue
JOIN mock_medical_accessibility_seed AS seed ON seed.venue_id = venue.venue_id
SET venue.accessible_status = seed.accessible_status,
    venue.accessibility_features = JSON_OBJECT(
        'mock_wheelchair_support', TRUE,
        'source', 'mock',
        'fixture', 'medical_accessibility_200_hospitals_first'
    );

DROP TEMPORARY TABLE mock_medical_accessibility_seed;
COMMIT;

SELECT accessible_status, COUNT(*) AS venue_count
FROM venues
WHERE JSON_UNQUOTE(JSON_EXTRACT(accessibility_features, '$.source')) = 'mock'
  AND JSON_EXTRACT(accessibility_features, '$.mock_wheelchair_support') = TRUE
GROUP BY accessible_status
ORDER BY accessible_status;
