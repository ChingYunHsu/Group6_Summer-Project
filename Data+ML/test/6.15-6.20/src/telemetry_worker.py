#!/usr/bin/env python3
"""Opt-in HTTP telemetry worker.

The worker deliberately has no mock-source mode. It only writes after an
operator supplies an enabled flag, authenticated source URL, and the existing
normalized event contract. Compose keeps this service behind the `telemetry`
profile so it cannot start during ordinary development or demo startup.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

import run_live_telemetry as runner


class TelemetryWorkerError(RuntimeError):
    """Configuration, provider, or ingestion failure that must fail the worker."""


@dataclass(frozen=True)
class WorkerConfig:
    source_url: str
    bearer_token: str
    source_name: str
    poll_interval_seconds: int
    request_timeout_seconds: int
    max_retries: int
    retry_backoff_seconds: int


def _positive_int(name: str, default: int, *, allow_zero: bool = False) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise TelemetryWorkerError(f"{name} must be an integer") from exc
    if value < 0 or (value == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise TelemetryWorkerError(f"{name} must be {qualifier}")
    return value


def load_config() -> WorkerConfig:
    """Read and validate the explicit production-ingestion configuration."""
    if os.environ.get("TELEMETRY_ENABLED", "false").lower() != "true":
        raise TelemetryWorkerError("TELEMETRY_ENABLED must be true; refusing to ingest")

    source_url = os.environ.get("TELEMETRY_SOURCE_URL", "").strip()
    bearer_token = os.environ.get("TELEMETRY_SOURCE_BEARER_TOKEN", "").strip()
    if not source_url:
        raise TelemetryWorkerError("TELEMETRY_SOURCE_URL is required")
    if not bearer_token:
        raise TelemetryWorkerError("TELEMETRY_SOURCE_BEARER_TOKEN is required")

    return WorkerConfig(
        source_url=source_url,
        bearer_token=bearer_token,
        source_name=os.environ.get("TELEMETRY_SOURCE_NAME", "live_capacity").strip() or "live_capacity",
        poll_interval_seconds=_positive_int("TELEMETRY_POLL_INTERVAL_SECONDS", 300),
        request_timeout_seconds=_positive_int("TELEMETRY_REQUEST_TIMEOUT_SECONDS", 10),
        max_retries=_positive_int("TELEMETRY_MAX_RETRIES", 3, allow_zero=True),
        retry_backoff_seconds=_positive_int("TELEMETRY_RETRY_BACKOFF_SECONDS", 5, allow_zero=True),
    )


def fetch_payloads(config: WorkerConfig) -> list[dict[str, Any]]:
    """Fetch either a JSON event array or an object with an ``events`` array."""
    request = Request(
        config.source_url,
        headers={"Authorization": f"Bearer {config.bearer_token}", "Accept": "application/json"},
    )
    with urlopen(request, timeout=config.request_timeout_seconds) as response:  # nosec B310: operator-configured HTTPS endpoint
        body = json.load(response)

    payloads = body.get("events") if isinstance(body, dict) else body
    if not isinstance(payloads, list):
        raise TelemetryWorkerError("source response must be a JSON array or an object with an events array")

    normalized_payloads: list[dict[str, Any]] = []
    for index, payload in enumerate(payloads):
        if not isinstance(payload, dict):
            raise TelemetryWorkerError(f"source event {index} must be a JSON object")
        normalized_payloads.append({"source_name": config.source_name, **payload})
    return normalized_payloads


def run_once(
    config: WorkerConfig,
    *,
    fetcher: Callable[[WorkerConfig], list[dict[str, Any]]] = fetch_payloads,
    execute_runner: Callable[[list[str]], int] = runner.main,
) -> None:
    """Fetch one batch and delegate all validation/audit/upsert work to the runner."""
    payloads = fetcher(config)
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as handle:
            path = Path(handle.name)
            for payload in payloads:
                handle.write(json.dumps(payload) + "\n")

        exit_code = execute_runner(["--payloads", str(path), "--execute"])
        if exit_code != 0:
            raise TelemetryWorkerError(f"ingestion runner exited {exit_code}")
        print(f"telemetry ingestion succeeded: received={len(payloads)} source={config.source_name}")
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def run_with_retries(
    config: WorkerConfig,
    *,
    sleep: Callable[[float], None] = time.sleep,
    run: Callable[[WorkerConfig], None] = run_once,
) -> None:
    for attempt in range(config.max_retries + 1):
        try:
            run(config)
            return
        except Exception as exc:
            if attempt == config.max_retries:
                raise TelemetryWorkerError(
                    f"telemetry ingestion failed after {attempt + 1} attempt(s): {exc}"
                ) from exc
            delay = config.retry_backoff_seconds * (attempt + 1)
            print(
                f"telemetry ingestion failed (attempt {attempt + 1}/{config.max_retries + 1}); "
                f"retrying in {delay}s: {exc}",
                file=sys.stderr,
            )
            sleep(delay)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run opt-in HTTP live telemetry ingestion.")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit.")
    args = parser.parse_args(argv)

    try:
        config = load_config()
        while True:
            run_with_retries(config)
            if args.once:
                return 0
            time.sleep(config.poll_interval_seconds)
    except TelemetryWorkerError as exc:
        print(f"telemetry worker failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
