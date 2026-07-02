"""API Usage Tracker — track SerpAPI call consumption across scripts.

Records every Search / Place API call and writes a JSON summary
at the end of each run for cost auditing.

Usage:
    tracker = ApiUsageTracker(output_dir)
    tracker.log_search_call(query="pharmacy", district="downtown", success=True)
    tracker.log_place_call(place_id="ChIJ...", success=True, has_popular_times=True)
    tracker.save()
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ApiUsageTracker:
    """Track SerpAPI call consumption per run."""

    def __init__(self, output_dir: Path, run_id: str | None = None):
        self.output_dir = Path(output_dir)
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._records: list[dict[str, Any]] = []
        self._search_calls = 0
        self._place_calls = 0
        self._search_success = 0
        self._search_fail = 0
        self._place_success = 0
        self._place_fail = 0
        self._rate_limited = 0
        self._new_popular_times = 0

    @property
    def search_calls(self) -> int:
        return self._search_calls

    @property
    def place_calls(self) -> int:
        return self._place_calls

    @property
    def total_calls(self) -> int:
        return self._search_calls + self._place_calls

    def log_search_call(
        self,
        query: str,
        district: str = "",
        category: str = "",
        success: bool = True,
        rate_limited: bool = False,
        matched_venues: int = 0,
        results_count: int = 0,
        batch_index: int | None = None,
    ) -> None:
        self._search_calls += 1
        if success:
            self._search_success += 1
        else:
            self._search_fail += 1
        if rate_limited:
            self._rate_limited += 1

        self._records.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api": "search",
            "query": query,
            "district": district,
            "category": category,
            "success": success,
            "rate_limited": rate_limited,
            "matched_venues": matched_venues,
            "results_count": results_count,
            "batch_index": batch_index,
        })

    def log_place_call(
        self,
        place_id: str,
        venue_name: str = "",
        success: bool = True,
        rate_limited: bool = False,
        has_popular_times: bool = False,
        venue_id: str = "",
        batch_index: int | None = None,
    ) -> None:
        self._place_calls += 1
        if success:
            self._place_success += 1
        else:
            self._place_fail += 1
        if rate_limited:
            self._rate_limited += 1
        if has_popular_times:
            self._new_popular_times += 1

        self._records.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api": "place",
            "place_id": place_id,
            "venue_name": venue_name,
            "venue_id": venue_id,
            "success": success,
            "rate_limited": rate_limited,
            "has_popular_times": has_popular_times,
            "batch_index": batch_index,
        })

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "search_calls": self._search_calls,
            "search_success": self._search_success,
            "search_fail": self._search_fail,
            "place_calls": self._place_calls,
            "place_success": self._place_success,
            "place_fail": self._place_fail,
            "total_calls": self.total_calls,
            "rate_limited_count": self._rate_limited,
            "new_popular_times_found": self._new_popular_times,
        }

    def print_summary(self, script_name: str = "") -> None:
        s = self.summary()
        header = f"=== API Usage Summary [{script_name}] ==="
        print(f"\n{header}")
        print(f"  Run ID:            {s['run_id']}")
        print(f"  Search API calls:  {s['search_calls']}  (success={s['search_success']}, fail={s['search_fail']})")
        print(f"  Place API calls:   {s['place_calls']}  (success={s['place_success']}, fail={s['place_fail']})")
        print(f"  Total API calls:   {s['total_calls']}")
        print(f"  Rate limited:      {s['rate_limited_count']}")
        print(f"  New popular_times: {s['new_popular_times_found']}")
        print(f"{'=' * len(header)}")

    def save(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save summary JSON
        summary_path = self.output_dir / f"api_usage_{self.run_id}.json"
        with open(summary_path, "w") as f:
            json.dump(self.summary(), f, indent=2)

        # Append call log to a cumulative file
        log_path = self.output_dir / "api_usage_log.jsonl"
        with open(log_path, "a") as f:
            for rec in self._records:
                f.write(json.dumps(rec) + "\n")

        print(f"  API usage saved: {summary_path}")
        print(f"  Call log appended: {log_path}")
        return summary_path
