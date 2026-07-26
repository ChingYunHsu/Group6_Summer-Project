-- Local-demo-only accessibility coverage.
--
-- This is intentionally a mock override approved for the demonstration: it
-- promotes only otherwise-unverified medical venues to the UI's
-- `full_access` status.  Existing OSM-derived full/partial/none evidence is
-- never overwritten.  `accessibility_features.source = mock` preserves the
-- provenance needed to exclude these values from real-data claims.
USE clearpath;

INSERT INTO venue_accessibility (venue_id, wheelchair_friendly)
SELECT venue_id, TRUE
FROM venues
WHERE venue_type IN ('healthcare', 'hospital', 'clinic', 'pharmacy', 'dentist', 'laboratory')
  AND accessible_status = 'unknown'
ON DUPLICATE KEY UPDATE wheelchair_friendly = VALUES(wheelchair_friendly);

UPDATE venues
SET accessible_status = 'full_access',
    accessibility_features = JSON_OBJECT(
      'mock_wheelchair_support', TRUE,
      'source', 'mock'
    )
WHERE venue_type IN ('healthcare', 'hospital', 'clinic', 'pharmacy', 'dentist', 'laboratory')
  AND accessible_status = 'unknown';
