-- Venues table: 24 columns backing GET /api/v1/venues and /api/v1/venues/<id>.
-- Bilingual service badges live in `supported_services` (JSON array of free-text
-- strings such as "French Help Available") so the frontend can render them
-- without inferring language support from `language_tags` alone.
CREATE TABLE IF NOT EXISTS venues (
    venue_id                VARCHAR(64)   NOT NULL PRIMARY KEY,
    name                     VARCHAR(255)  NOT NULL,
    venue_type               ENUM('hospital', 'clinic', 'pharmacy', 'urgent_care', 'mental_health', 'shelter')
                                           NOT NULL,
    latitude                 DECIMAL(9,6)  NOT NULL,
    longitude                DECIMAL(9,6)  NOT NULL,
    borough                  VARCHAR(64)   NOT NULL DEFAULT 'Manhattan',
    address                  VARCHAR(255)  NOT NULL,
    phone                    VARCHAR(32),
    opening_hours            VARCHAR(255),
    opening_hours_structured JSON,
    rating                   DECIMAL(2,1),
    weather_risk             VARCHAR(32)   DEFAULT 'none',
    primary_language         VARCHAR(8)    NOT NULL DEFAULT 'EN',
    secondary_language       VARCHAR(8),
    language_tags            JSON          NOT NULL,
    chatbot_enabled          TINYINT(1)    NOT NULL DEFAULT 0,
    wheelchair_friendly      TINYINT(1)    NOT NULL DEFAULT 0,
    step_free_route          TINYINT(1)    NOT NULL DEFAULT 0,
    accessible_toilet        TINYINT(1)    NOT NULL DEFAULT 0,
    entrance_width_cm        INT,
    accessible_status        ENUM('full_access', 'partial_access', 'no_access')
                                           NOT NULL DEFAULT 'no_access',
    accessibility_features   JSON,
    supported_services       JSON          NOT NULL,
    open_now                 TINYINT(1)    NOT NULL DEFAULT 1,
    data_confidence          VARCHAR(16)   DEFAULT 'high',
    created_at               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_venues_venue_type ON venues (venue_type);
CREATE INDEX idx_venues_accessible_status ON venues (accessible_status);
