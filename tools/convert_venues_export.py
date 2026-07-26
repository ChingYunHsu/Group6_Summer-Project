#!/usr/bin/env python3
"""Convert the legacy positional ``venues_export.sql`` dump safely.

The dump contains one or more positional INSERT statement chunks. This tool
deliberately does not parse their SQL values: it validates that all matching
chunks use the expected legacy form, then adds the schema's explicit 31-column
list to each INSERT prefix.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


VENUES_COLUMNS = (
    "venue_id", "venue_type", "name", "latitude", "longitude", "borough",
    "address", "phone", "website", "opening_hours", "photos", "rating",
    "weather_risk", "source_confidence", "language_tags", "primary_language",
    "secondary_language", "accessible_status", "accessibility_features",
    "active_warning", "open_now", "district", "created_at", "updated_at",
    "serpapi_place_id", "prediction_group_id", "prediction_shared",
    "serpapi_label_status", "has_popular_times", "ml_eligible",
    "serpapi_checked_at",
)

_VENUES_INSERT = re.compile(r"INSERT\s+INTO\s+`?venues`?\s+VALUES\s*", re.IGNORECASE)


def convert_dump(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    matches = list(_VENUES_INSERT.finditer(text))
    if not matches:
        raise ValueError(
            "Expected at least one positional INSERT INTO venues VALUES statement; "
            "found none. Refusing to rewrite the dump."
        )

    columns = ", ".join(f"`{column}`" for column in VENUES_COLUMNS)
    replacement = f"INSERT INTO `venues` ({columns}) VALUES "
    converted = _VENUES_INSERT.sub(replacement, text)
    destination.write_text(converted, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path("venues_export.sql"))
    parser.add_argument("destination", type=Path, nargs="?", default=Path("venues_export_converted.sql"))
    args = parser.parse_args()
    convert_dump(args.source, args.destination)
    print(f"Wrote {args.destination} with {len(VENUES_COLUMNS)} explicit venues columns.")


if __name__ == "__main__":
    main()
