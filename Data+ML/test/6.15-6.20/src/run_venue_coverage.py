#!/usr/bin/env python3
"""run_venue_coverage.py — CLI for venue spatial coverage testing.

Usage:
  cd Data+ML/test/6.8-6.12_DB
  python run_venue_coverage.py \
    --venue-file Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv \
    --radii 100,200,300,400,500 \
    --sources citibike,mta,traffic \
    --traffic-year 2025 \
    --output-dir Data+ML/test/6.8-6.12_DB/tests/output/venue_coverage
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Support both `python run_venue_coverage.py` and module import
sys.path.insert(0, str(Path(__file__).resolve().parent / "dqr"))

from venue_coverage import (
    SUPPORTED_SOURCES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    MAX_POINTS_PER_SOURCE,
    SourceResult,
    load_venues,
    fetch_citibike,
    fetch_mta,
    fetch_traffic,
    compute_nearest_distances,
    compute_radius_flags,
    compute_standalone_coverage,
    compute_cumulative_coverage,
    generate_markdown_report,
    generate_charts,
    write_artifacts,
)


# ── CLI Parsing & Validation ──────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Venue spatial coverage test"
    )
    parser.add_argument(
        "--venue-file", required=True,
        help="Path to venues_clean.csv",
    )
    parser.add_argument(
        "--radii", default="100,200,300,400,500",
        help="Comma-separated radii in metres (default: 100,200,300,400,500)",
    )
    parser.add_argument(
        "--sources", default="citibike,mta,traffic",
        help="Comma-separated source names (default: citibike,mta,traffic)",
    )
    parser.add_argument(
        "--traffic-year", type=int, default=2025,
        help="Traffic dataset year (default: 2025)",
    )
    parser.add_argument(
        "--page-size", type=int, default=DEFAULT_PAGE_SIZE,
        help=f"Max page size for SODA queries (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--connect-timeout", type=float, default=DEFAULT_TIMEOUT[0],
        help=f"Connection timeout in seconds (default: {DEFAULT_TIMEOUT[0]})",
    )
    parser.add_argument(
        "--read-timeout", type=float, default=DEFAULT_TIMEOUT[1],
        help=f"Read timeout in seconds (default: {DEFAULT_TIMEOUT[1]})",
    )
    parser.add_argument(
        "--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
        help=f"Max retries per request (default: {DEFAULT_MAX_RETRIES})",
    )
    parser.add_argument(
        "--output-dir",
        default="Data+ML/test/6.15-5.20/output",
        help="Output directory for artifacts",
    )

    args = parser.parse_args(argv)

    # ── Validation ──

    # Radii
    radii = [int(r.strip()) for r in args.radii.split(",") if r.strip()]
    if not radii:
        parser.error("Radius list must not be empty")
    if any(r <= 0 for r in radii):
        parser.error("All radii must be positive")
    if radii != sorted(radii):
        parser.error("Radii must be in increasing order")
    if len(radii) != len(set(radii)):
        parser.error("Radii must not contain duplicates")
    args.radii_list = radii

    # Sources
    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    if not sources:
        parser.error("Source list must not be empty")
    for s in sources:
        if s not in SUPPORTED_SOURCES:
            parser.error(f"Unsupported source '{s}'. Supported: {SUPPORTED_SOURCES}")
    args.sources_list = sources

    # Page size
    if args.page_size > 5000:
        parser.error("Page size must not exceed 5,000")
    if args.page_size <= 0:
        parser.error("Page size must be positive")

    # Venue file
    if not Path(args.venue_file).exists():
        parser.error(f"Venue file not found: {args.venue_file}")

    return args


# ── Orchestrator ───────────────────────────────────────────────


def run_coverage(args: argparse.Namespace) -> int:
    """Execute the full coverage test. Returns exit code."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    started_at = datetime.now(timezone.utc).isoformat()
    timeout = (args.connect_timeout, args.read_timeout)

    print("=== Venue Spatial Coverage Test ===")
    print(f"Run ID: {run_id}")
    print(f"Venue file: {args.venue_file}")
    print(f"Radii: {args.radii_list}")
    print(f"Sources: {args.sources_list}")
    print()

    # Step 1: Load venues
    print("[1/4] Loading venues...")
    venues_df, dup_count = load_venues(args.venue_file)
    venue_count = len(venues_df)
    print(f"  Loaded {venue_count} unique venues (removed {dup_count} duplicate venue_ids)")

    venue_lats = venues_df["latitude"].astype(float).values
    venue_lons = venues_df["longitude"].astype(float).values

    # Step 2: Fetch source data
    print("\n[2/4] Fetching source data...")
    source_results: dict[str, SourceResult] = {}

    fetchers = {
        "citibike": lambda: fetch_citibike(timeout=timeout, max_retries=args.max_retries),
        "mta": lambda: fetch_mta(timeout=timeout,
                                  max_retries=args.max_retries, page_size=args.page_size),
        "traffic": lambda: fetch_traffic(year=args.traffic_year, timeout=timeout,
                                          max_retries=args.max_retries, page_size=args.page_size),
    }

    successful_sources: list[str] = []
    for src in args.sources_list:
        print(f"  Fetching {src}...", end=" ", flush=True)
        result = fetchers[src]()
        source_results[src] = result
        if result.status == "ok":
            successful_sources.append(src)
            print(f"OK — {result.unique_coord_count} unique points "
                  f"({result.fetch_time_s:.1f}s)")
        else:
            print(f"FAILED — {result.error_type}: {result.error_message}")

    if not successful_sources:
        print("\nERROR: All sources failed. Cannot produce coverage results.")
        return 1

    # Step 3: Compute distances
    print("\n[3/4] Computing distances...")
    detail_records: list[dict] = []
    for idx in range(venue_count):
        row = {
            "venue_id": venues_df.iloc[idx]["venue_id"],
            "venue_type": venues_df.iloc[idx].get("venue_type", ""),
            "district": venues_df.iloc[idx].get("district", ""),
            "latitude": venue_lats[idx],
            "longitude": venue_lons[idx],
        }
        detail_records.append(row)

    detail_df = pd.DataFrame(detail_records)

    for src in successful_sources:
        sr = source_results[src]
        src_lats = np.array([p.latitude for p in sr.points])
        src_lons = np.array([p.longitude for p in sr.points])
        src_ids = np.array([p.source_id for p in sr.points])

        dist_m, nearest_ids = compute_nearest_distances(
            venue_lats, venue_lons, src_lats, src_lons, src_ids
        )

        detail_df[f"{src}_nearest_source_id"] = nearest_ids
        detail_df[f"{src}_nearest_distance_m"] = dist_m

        radius_flags = compute_radius_flags(dist_m, args.radii_list)
        for r in args.radii_list:
            detail_df[f"{src}_covered_{r}m"] = radius_flags[r]

        print(f"  {src}: median={np.median(dist_m):.0f}m, "
              f"p90={np.percentile(dist_m, 90):.0f}m")

    # Step 4: Aggregate and generate artifacts
    print("\n[4/4] Generating coverage metrics and artifacts...")

    # Standalone coverage
    standalone_dfs = []
    for src in successful_sources:
        standalone_dfs.append(compute_standalone_coverage(detail_df, src, args.radii_list))
    standalone_df = pd.concat(standalone_dfs, ignore_index=True) if standalone_dfs else pd.DataFrame()

    # Cumulative coverage — fixed prefix order over the FULL requested source
    # list; a combination is emitted only if every source in its prefix
    # succeeded. A failed source is NOT skipped over (SOP §7.3 / §10.2).
    cumulative_df = compute_cumulative_coverage(
        detail_df, args.sources_list, args.radii_list,
        successful_sources=set(successful_sources),
    )

    summary_df = pd.concat([standalone_df, cumulative_df], ignore_index=True)

    # Build metadata
    output_dir = Path(args.output_dir)
    completed_at = datetime.now(timezone.utc).isoformat()

    import sklearn
    metadata = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "timezone": "UTC",
        "venue_input": {
            "file_path": str(args.venue_file),
            "total_rows": venue_count + dup_count,
            "unique_venue_count": venue_count,
            "duplicate_venue_id_count": dup_count,
        },
        "parameters": {
            "radii": args.radii_list,
            "source_order": args.sources_list,
            "mta_dataset_id": "5f5g-n3cz",
            "traffic_year": args.traffic_year,
            "page_size": args.page_size,
            "connect_timeout": args.connect_timeout,
            "read_timeout": args.read_timeout,
            "max_retries": args.max_retries,
        },
        "sources": {
            src: {
                "status": sr.status,
                "api_url": sr.api_url,
                "dataset_id": sr.dataset_id,
                "query_text": sr.query_text,
                "fetch_time_s": round(sr.fetch_time_s, 2),
                "max_source_timestamp": sr.max_source_timestamp,
                "data_age_seconds": (
                    round(
                        (datetime.fromisoformat(completed_at) -
                         datetime.fromisoformat(sr.max_source_timestamp)).total_seconds()
                    )
                    if sr.max_source_timestamp
                    and sr.max_source_timestamp not in ("timestamp_unavailable", "")
                    and "T" in sr.max_source_timestamp
                    else None
                ),
                "raw_count": sr.raw_count,
                "valid_count": sr.valid_count,
                "unique_id_count": sr.unique_id_count,
                "unique_coord_count": sr.unique_coord_count,
                "rejected_count": sr.rejected_count,
                "retry_count": sr.retry_count,
                "error_type": sr.error_type,
                "error_message": sr.error_message,
            }
            for src, sr in source_results.items()
        },
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
        "artifacts": [],
    }

    # Generate report
    report_md = generate_markdown_report(
        metadata, summary_df, detail_df, source_results, args.radii_list
    )

    # Generate charts
    chart_filenames = generate_charts(
        output_dir, summary_df, detail_df, source_results, args.radii_list, run_id
    )
    metadata["artifacts"] = [
        "venue_coverage_detail.csv",
        "coverage_summary.csv",
        "run_metadata.json",
        "coverage_report.md",
    ] + chart_filenames

    # Traffic year profile diagnostic
    traffic_sr = source_results.get("traffic")
    if traffic_sr and traffic_sr.year_profile:
        profile_df = pd.DataFrame(traffic_sr.year_profile)
        profile_fname = "traffic_year_profile.csv"
        profile_df.to_csv(output_dir / profile_fname, index=False)
        metadata["artifacts"].append(profile_fname)

    # Write all artifacts
    write_artifacts(
        output_dir, detail_df, summary_df, metadata, report_md, chart_filenames
    )

    print(f"\nArtifacts written to: {output_dir}")
    print("\n=== Coverage Test Complete ===")
    return 0


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    return run_coverage(args)


if __name__ == "__main__":
    sys.exit(main())
