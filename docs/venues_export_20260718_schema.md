# `venues_export.sql` schema contract

`venues_export.sql` is a data-only MySQL dump from 2026-07-18. Its legacy
`INSERT INTO venues VALUES` statement has **31 positional values**. Import it
only after converting it with `tools/convert_venues_export.py`; the generated
file names every column and is safe against future column-order changes.

The required order is the `venues` schema order in
`docker/mysql/init/001_clearpath_schema.sql`:

```text
venue_id, venue_type, name, latitude, longitude, borough, address, phone,
website, opening_hours, photos, rating, weather_risk, source_confidence,
language_tags, primary_language, secondary_language, accessible_status,
accessibility_features, active_warning, open_now, district, created_at,
updated_at, serpapi_place_id, prediction_group_id, prediction_shared,
serpapi_label_status, has_popular_times, ml_eligible, serpapi_checked_at
```

The conversion tool validates that at least one positional `venues` insert is
present and changes only each matching statement prefix; values, JSON, quoting,
and escaping are copied byte-for-byte.
