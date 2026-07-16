"""Capture and compare repeatable SerpAPI Google Maps Popular Times snapshots.

The runner deliberately accepts a fixed CSV of known Google ``place_id`` values.
It does not use category discovery, so a follow-up run compares the same places
and has a bounded, reviewable API-call budget.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import urlopen


SERPAPI_URL = "https://serpapi.com/search.json"
SNAPSHOT_COLUMNS = (
    "snapshot_id", "captured_at", "venue_id", "place_id", "title", "day",
    "hour", "busyness_score", "live_info", "has_popular_times",
)


@dataclass(frozen=True)
class PlaceTarget:
    place_id: str
    venue_id: str = ""


class SerpAPIRequestError(RuntimeError):
    def __init__(self, status_code: int, detail: str = "") -> None:
        super().__init__(f"SerpAPI request failed ({status_code}): {detail}".strip())
        self.status_code = status_code


def load_targets(path: Path, max_places: int | None = None, deduplicate_place_ids: bool = True) -> list[PlaceTarget]:
    """Load unique ``place_id`` rows from a CSV with optional ``venue_id``."""
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "place_id" not in reader.fieldnames:
            raise ValueError("places CSV must contain a place_id column")
        targets: list[PlaceTarget] = []
        seen: set[str] = set()
        for row in reader:
            place_id = (row.get("place_id") or "").strip()
            if not place_id or (deduplicate_place_ids and place_id in seen):
                continue
            seen.add(place_id)
            targets.append(PlaceTarget(place_id=place_id, venue_id=(row.get("venue_id") or "").strip()))
            if max_places is not None and len(targets) >= max_places:
                break
    return targets


def targets_from_label_view(path: Path, target_count: int = 163) -> list[PlaceTarget]:
    """Select a stable, high-priority cohort from the legacy coverage view.

    The selected list is persisted by the notebook before any live request, so
    later repeats use the saved CSV instead of re-selecting a different cohort.
    """
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    eligible = [
        row for row in rows
        if str(row.get("ml_eligible", "")).strip().lower() == "true"
        and (row.get("serpapi_place_id") or "").strip()
    ]
    eligible.sort(key=lambda row: (-float(row.get("priority_score") or 0), row.get("venue_id") or ""))
    targets: list[PlaceTarget] = []
    for row in eligible:
        place_id = row["serpapi_place_id"].strip()
        targets.append(PlaceTarget(place_id=place_id, venue_id=(row.get("venue_id") or "").strip()))
        if len(targets) >= target_count:
            break
    if len(targets) < target_count:
        raise ValueError(f"Only {len(targets)} unique eligible place IDs available; expected {target_count}")
    return targets


def resolve_api_key(api_key_file: Path | None = None) -> str:
    """Read the key without printing it; environment takes precedence."""
    key = os.getenv("SERPAPI_API_KEY", "").strip()
    if key:
        return key
    if api_key_file and api_key_file.exists():
        return api_key_file.read_text(encoding="utf-8").strip()
    raise RuntimeError("SERPAPI_API_KEY is not configured; set it or pass --api-key-file")


def fetch_place(place_id: str, api_key: str) -> dict[str, Any]:
    params = urlencode({
        "engine": "google_maps", "type": "place", "place_id": place_id,
        "hl": "en", "api_key": api_key,
    })
    try:
        with urlopen(f"{SERPAPI_URL}?{params}", timeout=30) as response:  # nosec B310: fixed HTTPS endpoint
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise SerpAPIRequestError(exc.code, detail) from exc


def snapshot_rows(target: PlaceTarget, payload: dict[str, Any], snapshot_id: str, captured_at: str) -> list[dict[str, Any]]:
    """Normalize the Popular Times graph into one comparable row per day/hour."""
    place = payload.get("place_results") or {}
    popular = place.get("popular_times") or {}
    graph = popular.get("graph_results") or {}
    live_info = ((popular.get("live_hash") or {}).get("info"))
    base = {
        "snapshot_id": snapshot_id, "captured_at": captured_at,
        "venue_id": target.venue_id, "place_id": target.place_id,
        "title": place.get("title", ""), "live_info": live_info or "",
        "has_popular_times": bool(graph),
    }
    rows: list[dict[str, Any]] = []
    for day, entries in graph.items():
        for entry in entries or []:
            score = entry.get("busyness_score")
            if score is None:
                continue
            rows.append({**base, "day": day, "hour": entry.get("time", ""), "busyness_score": float(score)})
    if not rows:
        rows.append({**base, "day": "", "hour": "", "busyness_score": ""})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], columns: tuple[str, ...] = SNAPSHOT_COLUMNS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def baseline_rows_from_raw_json(raw_dir: Path, targets: list[PlaceTarget], snapshot_id: str = "legacy") -> list[dict[str, Any]]:
    """Extract historical Popular Times rows from cached Place API JSON files.

    Search-result JSON has no full graph and is intentionally ignored. Only a
    response that records the requested ``place_id`` and a ``place_results``
    object can be used as a like-for-like baseline.
    """
    targets_by_place: dict[str, list[PlaceTarget]] = {}
    for target in targets:
        targets_by_place.setdefault(target.place_id, []).append(target)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in raw_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        place_id = str((payload.get("search_parameters") or {}).get("place_id") or "")
        if place_id not in targets_by_place or place_id in seen or not payload.get("place_results"):
            continue
        seen.add(place_id)
        captured_at = str((payload.get("search_metadata") or {}).get("created_at") or "")
        for target in targets_by_place[place_id]:
            rows.extend(snapshot_rows(target, payload, snapshot_id, captured_at))
    return rows


def compare_snapshots(previous: list[dict[str, str]], current: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compare matching place/day/hour points and report coverage separately."""
    key = lambda row: (row["place_id"], row.get("day", ""), row.get("hour", ""))
    previous_by_key = {key(row): row for row in previous if row.get("busyness_score", "") != ""}
    current_by_key = {key(row): row for row in current if row.get("busyness_score", "") != ""}
    rows: list[dict[str, Any]] = []
    for point in sorted(previous_by_key.keys() & current_by_key.keys()):
        before, after = previous_by_key[point], current_by_key[point]
        before_score, after_score = float(before["busyness_score"]), float(after["busyness_score"])
        rows.append({
            "place_id": point[0], "day": point[1], "hour": point[2],
            "previous_score": before_score, "current_score": after_score,
            "score_change": round(after_score - before_score, 2),
            "previous_live_info": before.get("live_info", ""),
            "current_live_info": after.get("live_info", ""),
            "live_info_changed": before.get("live_info", "") != after.get("live_info", ""),
        })
    previous_places = {row["place_id"] for row in previous}
    current_places = {row["place_id"] for row in current}
    matched = len(rows)
    summary = {
        "previous_place_count": len(previous_places), "current_place_count": len(current_places),
        "shared_place_count": len(previous_places & current_places), "matched_hour_count": matched,
        "mean_score_change": round(sum(row["score_change"] for row in rows) / matched, 2) if matched else None,
        "mean_absolute_score_change": round(sum(abs(row["score_change"]) for row in rows) / matched, 2) if matched else None,
        "live_status_changed_points": sum(row["live_info_changed"] for row in rows),
    }
    return rows, summary


def _raw_path(raw_dir: Path, place_id: str) -> Path:
    return raw_dir / f"{hashlib.sha256(place_id.encode()).hexdigest()[:16]}.json"


def run_snapshot(
    targets: list[PlaceTarget], output_dir: Path, snapshot_id: str, api_key: str,
    fetcher: Callable[[str, str], dict[str, Any]] = fetch_place, sleep_seconds: float = 1.0,
    progress: Callable[[str], None] | None = None,
) -> tuple[Path, dict[str, Any]]:
    captured_at = datetime.now(timezone.utc).isoformat()
    snapshot_dir = output_dir / snapshot_id
    raw_dir = snapshot_dir / "raw"
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    payload_by_place: dict[str, dict[str, Any]] = {}
    unique_place_count = len({target.place_id for target in targets})
    halted_reason = ""
    for index, target in enumerate(targets):
        try:
            payload = payload_by_place.get(target.place_id)
            made_live_call = False
            if payload is None:
                made_live_call = True
                if progress:
                    progress(f"SerpAPI request {len(payload_by_place) + 1}/{unique_place_count}: {target.place_id}")
                payload = fetcher(target.place_id, api_key)
                payload_by_place[target.place_id] = payload
                raw_dir.mkdir(parents=True, exist_ok=True)
                _raw_path(raw_dir, target.place_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            rows.extend(snapshot_rows(target, payload, snapshot_id, captured_at))
        except Exception as exc:  # record a failed target without losing the round
            failures.append({"place_id": target.place_id, "error": str(exc)})
            if progress:
                progress(f"SerpAPI request failed for {target.place_id}: {exc}")
            if isinstance(exc, SerpAPIRequestError) and exc.status_code in {401, 403, 429}:
                halted_reason = f"Stopped after SerpAPI HTTP {exc.status_code}; check credentials or quota."
                if progress:
                    progress(halted_reason)
                break
        if sleep_seconds and made_live_call and index < len(targets) - 1:
            time.sleep(sleep_seconds)
    snapshot_file = snapshot_dir / "popular_times_snapshot.csv"
    write_csv(snapshot_file, rows)
    metadata = {
        "snapshot_id": snapshot_id, "captured_at": captured_at, "target_count": len(targets),
        "successful_target_count": len({row["venue_id"] for row in rows}),
        "popular_times_target_count": len({row["venue_id"] for row in rows if row["has_popular_times"]}),
        "api_call_count": len(payload_by_place),
        "failure_count": len(failures), "failures": failures,
        "halted_reason": halted_reason,
    }
    (snapshot_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return snapshot_file, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--places-csv", type=Path, required=True, help="CSV with place_id and optional venue_id")
    parser.add_argument("--output-dir", type=Path, default=Path("output/serpapi_snapshots"))
    parser.add_argument("--snapshot-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--compare-to", type=Path, help="Earlier popular_times_snapshot.csv")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--max-places", type=int)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    targets = load_targets(args.places_csv, args.max_places)
    if not targets:
        raise SystemExit("No place_id values found")
    if args.dry_run:
        print(json.dumps({"target_count": len(targets), "output_dir": str(args.output_dir), "snapshot_id": args.snapshot_id}, indent=2))
        return 0
    snapshot_file, metadata = run_snapshot(
        targets, args.output_dir, args.snapshot_id, resolve_api_key(args.api_key_file), sleep_seconds=args.sleep_seconds,
    )
    print(json.dumps({"snapshot_file": str(snapshot_file), **metadata}, indent=2))
    if args.compare_to:
        comparison, summary = compare_snapshots(read_csv(args.compare_to), read_csv(snapshot_file))
        comparison_file = snapshot_file.parent / "comparison_to_previous.csv"
        columns = ("place_id", "day", "hour", "previous_score", "current_score", "score_change", "previous_live_info", "current_live_info", "live_info_changed")
        write_csv(comparison_file, comparison, columns)
        (snapshot_file.parent / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({"comparison_file": str(comparison_file), **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
