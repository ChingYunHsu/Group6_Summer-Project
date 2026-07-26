-- Deprecated local-demo migration.
--
-- Do not manufacture `full_access` records. Accessibility filters and reports
-- must reflect verified source data only.  This file remains as a no-op so an
-- existing migration sequence can be re-applied safely; 014 removes any mock
-- rows written by older revisions of this migration.
USE clearpath;

SELECT '013 mock wheelchair seed retired; verified accessibility only' AS migration_notice;
