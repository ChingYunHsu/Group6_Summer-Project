#!/usr/bin/env python3
"""Restore verified healthcare and OSM accessibility data without Jupyter."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root", type=Path, required=True,
        help="Directory containing the versioned raw data_source files.",
    )
    args = parser.parse_args()
    data_root = args.data_root.expanduser().resolve()
    if not data_root.is_dir():
        parser.error(f"data root does not exist: {data_root}")

    # config.py resolves this environment variable during import.
    os.environ["CLEARPATH_DATA_ROOT"] = str(data_root)
    sys.path.insert(0, str(Path(__file__).parent))
    from clearpath_db import dedup_healthcare, etl_healthcare, get_conn, load_sources

    sources = load_sources()
    nys_deduped, osm_deduped, dedup_stats = dedup_healthcare(
        sources.osm_features, sources.nys
    )
    conn = get_conn()
    try:
        result = etl_healthcare(
            conn, nys_deduped, osm_deduped, sources.accessibility_features
        )
    finally:
        conn.close()

    print(json.dumps({
        "data_root": str(data_root),
        "dedup": dedup_stats,
        "healthcare_etl": result,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
