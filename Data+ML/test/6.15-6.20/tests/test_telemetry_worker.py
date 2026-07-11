"""Offline tests for the opt-in HTTP telemetry worker."""

import io
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import telemetry_worker as worker  # noqa: E402


def _env(monkeypatch, **overrides):
    values = {
        "TELEMETRY_ENABLED": "true",
        "TELEMETRY_SOURCE_URL": "https://provider.example.test/events",
        "TELEMETRY_SOURCE_BEARER_TOKEN": "test-token",
        "TELEMETRY_SOURCE_NAME": "live_capacity",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_worker_refuses_disabled_or_incomplete_configuration(monkeypatch):
    monkeypatch.setenv("TELEMETRY_ENABLED", "false")
    with pytest.raises(worker.TelemetryWorkerError, match="TELEMETRY_ENABLED"):
        worker.load_config()

    _env(monkeypatch, TELEMETRY_SOURCE_BEARER_TOKEN="")
    with pytest.raises(worker.TelemetryWorkerError, match="BEARER_TOKEN"):
        worker.load_config()


def test_fetch_payloads_accepts_event_envelope_and_preserves_provider_source_name(monkeypatch):
    _env(monkeypatch)
    config = worker.load_config()

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return Response(json.dumps({"events": [{"source_venue_id": "v_1001"}]}).encode())

    monkeypatch.setattr(worker, "urlopen", fake_urlopen)
    payloads = worker.fetch_payloads(config)

    assert payloads == [{"source_name": "live_capacity", "source_venue_id": "v_1001"}]
    assert captured == {"authorization": "Bearer test-token", "timeout": 10}


def test_run_once_writes_ephemeral_jsonl_and_delegates_to_existing_execute_runner(monkeypatch):
    _env(monkeypatch)
    config = worker.load_config()
    captured = {}

    def fake_runner(argv):
        payload_path = Path(argv[1])
        captured["argv"] = argv
        captured["payloads"] = [json.loads(line) for line in payload_path.read_text().splitlines()]
        return 0

    worker.run_once(config, fetcher=lambda _config: [{"source_venue_id": "v_1002"}], execute_runner=fake_runner)

    assert captured["argv"][::2] == ["--payloads", "--execute"]
    assert captured["payloads"] == [{"source_venue_id": "v_1002"}]
    assert not Path(captured["argv"][1]).exists()


def test_run_with_retries_fails_after_bounded_attempts():
    config = worker.WorkerConfig("https://x", "token", "live_capacity", 300, 10, 2, 0)
    attempts = []

    def fail(_config):
        attempts.append(1)
        raise RuntimeError("provider unavailable")

    with pytest.raises(worker.TelemetryWorkerError, match="3 attempt"):
        worker.run_with_retries(config, sleep=lambda _seconds: None, run=fail)
    assert len(attempts) == 3
