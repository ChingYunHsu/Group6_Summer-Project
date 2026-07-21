-- NYS Health Facility General Information has no accessibility or language
-- service fields.  Mark unverified healthcare records as unknown, rather than
-- claiming they have no accessible provision, and surface existing LASS data
-- through the venue API fields.
USE clearpath;

ALTER TABLE venues
  MODIFY accessible_status ENUM('full_access', 'partial', 'step_free_route_only', 'none', 'unknown')
  NOT NULL DEFAULT 'unknown';

UPDATE venues AS venue
LEFT JOIN venue_accessibility AS accessibility ON accessibility.venue_id = venue.venue_id
SET venue.accessible_status = 'unknown'
WHERE venue.venue_type IN ('healthcare', 'hospital', 'clinic', 'pharmacy', 'dentist', 'laboratory')
  AND venue.accessible_status = 'none'
  AND accessibility.venue_id IS NULL;

UPDATE venues AS venue
JOIN venue_language AS language ON language.venue_id = venue.venue_id
SET venue.language_tags = language.language_tag,
    venue.primary_language = UPPER(JSON_UNQUOTE(JSON_EXTRACT(language.language_tag, '$[0]'))),
    venue.secondary_language = UPPER(JSON_UNQUOTE(JSON_EXTRACT(language.language_tag, '$[1]')))
WHERE language.language_tag IS NOT NULL
  AND JSON_LENGTH(language.language_tag) > 0;
