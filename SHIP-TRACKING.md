# Ship-tracking integration

This integration treats AIS as append-only observation data. A position, speed change, missing update, or geofence transition is not proof of a port call, delay, disruption, or recovery.

## Safety boundary

- `VesselPosition` records provider observations with timestamps, hashes, source locator, and raw references.
- Malformed messages and conflicting MMSI values are quarantined.
- Unsupported AIS message types are ignored explicitly.
- `VesselGeofenceSignal` is deterministic and always remains in `review` state with `external_event_eligible=false`.
- Creating canonical `Evidence` or `ExternalEvent` records requires a separate corroboration and review workflow.
- Live AIS Stream access is disabled by default and requires an `AISSTREAM_API_KEY` environment variable.
- Tracking observations are separate from benchmark fixtures, expected labels, and sealed holdout inputs.

## Development replay

The replay provider reads JSON Lines envelopes containing `received_at` and `payload`. The bundled replay fixture is synthetic and exists only for deterministic tests.

```python
from rock_supply_intelligence.tracking import ReplayTrackingProvider

results = list(ReplayTrackingProvider("tests/fixtures/aisstream-replay.jsonl").results())
```

## Live transport boundary

`AISStreamConfig` and `subscription_payload` validate the subscription without opening a socket. A future live transport must consume messages continuously, reconnect with bounded exponential backoff and jitter, persist raw messages before downstream use, and never expose the API key to a browser or log.
