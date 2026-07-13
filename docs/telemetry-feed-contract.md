# Telemetry Feed Contract

> Version: `telemetry-event-v1`  
> Owner: Data + Ops  
> Status: provider-neutral contract; a provider has not yet been approved.

`telemetry_worker.py` may fetch only an authenticated provider response. Before
calling `run_live_telemetry.py --execute`, its adapter must emit one canonical
event per venue. The worker must fail the batch when a required source field
cannot be mapped; it must not invent values or substitute mock telemetry.

## Canonical event

```json
{
  "source_name": "approved_provider_name",
  "source_venue_id": "provider-stable-venue-id",
  "observed_at": "2026-07-11T09:30:00Z",
  "load_percent": 64,
  "avg_wait_minutes": 18,
  "forecast_1h": [{"offset_hours": 1, "percent": 68, "level": "moderate"}],
  "features_snapshot_id": "optional-provider-event-or-snapshot-id"
}
```

| Canonical field | Required | Validation | Provider mapping rule |
| --- | :---: | --- | --- |
| `source_name` | yes | non-empty stable provider key | Set from approved provider configuration, never from a mutable display name. |
| `source_venue_id` | yes | non-empty stable ID | Map to `venue_source_links(source_name, source_record_id)` before production enablement. |
| `observed_at` | yes | ISO-8601 timestamp | Use provider observation time, not fetch time. Reject absent or unparseable values. |
| `load_percent` | yes | numeric integer 0-100 | Convert provider occupancy ratio to percent once, rounding only at this boundary. |
| `avg_wait_minutes` | yes | numeric integer >= 0 | Convert seconds to minutes here if necessary. |
| `forecast_1h` | no | runner-compatible JSON | Omit when the provider has no forecast; never derive it from a fixed mock curve. |
| `features_snapshot_id` | no | non-empty string when supplied | Use provider event/version ID. The ingestion library hashes the canonical payload when absent. |

## Provider approval checklist

1. Record provider, endpoint owner, authentication method, polling interval, rate limit and retention policy in the release record.
2. Commit an adapter fixture with at least one valid event and one rejected event; fixture IDs must resolve through `venue_source_links` in the deployment environment.
3. Run the worker once in an isolated database, then verify audit log, idempotent replay and `/api/v1/realtime/map-updates` freshness.
4. Inject an HTTP and a database failure. Capture retry, alert and explicit API degradation evidence before enabling the Compose `telemetry` profile.

This document deliberately does not name a real provider or credential. Those are release configuration, not repository defaults.
