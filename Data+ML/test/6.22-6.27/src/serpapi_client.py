"""SerpAPI HTTP request client with caching, retry, and rate-limit handling.

All scripts that call SerpAPI should go through this module to guarantee
a single cache key format and consistent retry behaviour.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

# ── Constants ──────────────────────────────────────────────────

SERPAPI_BASE_URL = "https://serpapi.com/search.json"
SERPAPI_TIMEOUT = (3, 10)  # (connect, read)
SERPAPI_MAX_RETRIES = 3
SERPAPI_RETRY_DELAYS = [2, 4, 8]


def _cache_key(params: dict) -> str:
    """Deterministic MD5 cache key from the parameter dict."""
    cache_params = {k: v for k, v in params.items() if k != "api_key"}
    return hashlib.md5(
        json.dumps(cache_params, sort_keys=True).encode()
    ).hexdigest()[:12]


def get_cache_path(
    output_dir: Path,
    prefix: str,
    params: dict,
) -> Path:
    """Return the cache file path for *params* (including engine)."""
    merged = dict(params)
    merged.setdefault("engine", "google_maps")
    return (
        output_dir / "serpapi_raw_responses" / f"{prefix}_{_cache_key(merged)}.json"
    )


def serpapi_request(
    params: dict,
    api_key: str,
    output_dir: Path,
    cache_prefix: str = "search",
) -> dict | None:
    """Make a SerpAPI Google Maps request with disk caching and retries.

    Returns the parsed JSON response, or ``None`` on permanent failure.
    """
    params["api_key"] = api_key
    params["engine"] = "google_maps"

    cache_file = get_cache_path(output_dir, cache_prefix, params)

    # Return cached response if it exists
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    # Make request with retries
    for attempt in range(SERPAPI_MAX_RETRIES):
        try:
            resp = requests.get(
                SERPAPI_BASE_URL,
                params=params,
                timeout=SERPAPI_TIMEOUT,
            )
            if resp.status_code == 429:
                delay = SERPAPI_RETRY_DELAYS[min(attempt, len(SERPAPI_RETRY_DELAYS) - 1)]
                print(f"  [429] Rate limited, waiting {delay}s...")
                time.sleep(delay)
                continue
            if resp.status_code in {401, 403}:
                print(
                    f"  [{resp.status_code}] SerpAPI authentication failed; "
                    "check SERPAPI_API_KEY."
                )
                return None
            resp.raise_for_status()
            data = resp.json()

            # Cache to disk
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)

            return data

        except requests.RequestException as e:
            delay = SERPAPI_RETRY_DELAYS[min(attempt, len(SERPAPI_RETRY_DELAYS) - 1)]
            status = getattr(
                getattr(e, "response", None), "status_code", "request_error"
            )
            print(
                f"  [Error] SerpAPI request failed with status={status}, "
                f"retrying in {delay}s..."
            )
            time.sleep(delay)

    cache_params = {k: v for k, v in params.items() if k not in ("api_key", "engine")}
    print(f"  [Failed] All {SERPAPI_MAX_RETRIES} attempts failed for params: {cache_params}")
    return None
