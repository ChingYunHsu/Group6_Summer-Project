-- Remove accessibility data manufactured by the retired 013 demo seed.
--
-- This is idempotent. It removes only records whose venues retain the exact
-- mock provenance marker; verified OSM full/partial/none records are never
-- touched. Run the healthcare ETL afterwards when the raw source bundle is
-- available, to restore verified OSM annotations into this database.
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

COMMIT;
