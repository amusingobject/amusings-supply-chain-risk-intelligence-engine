from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rock_supply_intelligence.tracking import (
    AISStreamConfig,
    BoundingBox,
    PortGeofence,
    ReplayTrackingProvider,
    TrackingObservationStore,
    evaluate_geofence,
    normalize_message,
    subscription_payload,
)

REPLAY = Path(__file__).parent / "fixtures" / "aisstream-replay.jsonl"


def payload(*, mmsi: int = 368207620, valid: bool = True, latitude: float = 33.74, longitude: float = -118.25) -> dict:
    return {
        "MessageType": "PositionReport",
        "MetaData": {"MMSI": mmsi, "ShipName": "TEST VESSEL", "Latitude": latitude, "Longitude": longitude},
        "Message": {
            "PositionReport": {
                "UserID": mmsi,
                "Valid": valid,
                "Sog": 4.1,
                "Cog": 44.0,
                "TrueHeading": 511,
                "NavigationalStatus": 0,
            }
        },
    }


class AISStreamNormalizationTests(unittest.TestCase):
    def test_position_report_is_observation_only(self) -> None:
        result = normalize_message(payload(), received_at="2026-09-09T18:05:00Z", synthetic=True)
        self.assertEqual(result.disposition, "accepted")
        self.assertEqual(result.observation.mmsi, "368207620")  # type: ignore[union-attr]
        self.assertIsNone(result.observation.true_heading_degrees)  # type: ignore[union-attr]
        self.assertTrue(result.observation.provenance.synthetic)  # type: ignore[union-attr]

    def test_conflicting_mmsi_is_quarantined(self) -> None:
        raw = payload()
        raw["Message"]["PositionReport"]["UserID"] = 211476060
        result = normalize_message(raw, received_at="2026-09-09T18:05:00Z")
        self.assertEqual((result.disposition, result.reason), ("quarantined", "mmsi_conflict"))
        self.assertIsNone(result.observation)

    def test_malformed_position_is_quarantined(self) -> None:
        result = normalize_message(payload(latitude=100.0), received_at="2026-09-09T18:05:00Z")
        self.assertEqual(result.disposition, "quarantined")
        self.assertIsNone(result.observation)

    def test_string_validity_flag_is_quarantined_instead_of_coerced(self) -> None:
        raw = payload()
        raw["Message"]["PositionReport"]["Valid"] = "false"
        result = normalize_message(raw, received_at="2026-09-09T18:05:00Z")
        self.assertEqual(result.disposition, "quarantined")

    def test_unrelated_message_is_ignored(self) -> None:
        result = normalize_message({"MessageType": "StaticDataReport"}, received_at="2026-09-09T18:05:00Z")
        self.assertEqual(result.disposition, "ignored")


class GeofenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.port = PortGeofence(
            locode="USLAX",
            name="Port of Los Angeles test bounds",
            bounds=BoundingBox(south=33.70, west=-118.30, north=33.80, east=-118.15),
        )

    def test_replay_yields_review_only_entry_signal(self) -> None:
        observations = [result.observation for result in ReplayTrackingProvider(REPLAY).results()]
        self.assertTrue(all(observations))
        signal = evaluate_geofence(observations[1], self.port, previous=observations[0])  # type: ignore[arg-type]
        self.assertEqual((signal.relation, signal.transition), ("inside", "entered"))
        self.assertEqual(signal.review_state, "review")
        self.assertFalse(signal.external_event_eligible)

    def test_provider_invalid_position_cannot_create_normal_signal(self) -> None:
        observation = normalize_message(
            payload(valid=False), received_at="2026-09-09T18:05:00Z", synthetic=True
        ).observation
        signal = evaluate_geofence(observation, self.port)  # type: ignore[arg-type]
        self.assertEqual((signal.relation, signal.transition), ("unknown", "unknown"))

    def test_out_of_order_sequence_fails_closed(self) -> None:
        current = normalize_message(payload(), received_at="2026-09-09T18:05:00Z", synthetic=True).observation
        signal = evaluate_geofence(current, self.port, previous=current)  # type: ignore[arg-type]
        self.assertEqual(signal.relation, "unknown")
        self.assertEqual(signal.reason, "invalid_observation_sequence")

    def test_stale_prior_position_cannot_create_transition(self) -> None:
        previous = normalize_message(
            payload(longitude=-118.31), received_at="2026-09-09T18:00:00Z", synthetic=True
        ).observation
        current = normalize_message(
            payload(), received_at="2026-09-09T18:20:00Z", synthetic=True
        ).observation
        signal = evaluate_geofence(current, self.port, previous=previous, max_age_seconds=900)  # type: ignore[arg-type]
        self.assertEqual((signal.relation, signal.transition), ("unknown", "unknown"))
        self.assertEqual(signal.reason, "prior_position_stale")


class TrackingPersistenceAndSecretTests(unittest.TestCase):
    def test_store_is_hash_bound_and_idempotent(self) -> None:
        raw = payload()
        result = normalize_message(raw, received_at="2026-09-09T18:05:00Z", synthetic=True)
        with tempfile.TemporaryDirectory() as folder:
            store = TrackingObservationStore(folder)
            self.assertTrue(store.append(result, raw))
            self.assertFalse(store.append(result, raw))
            with self.assertRaisesRegex(ValueError, "hash does not match"):
                store.append(result, payload(mmsi=211476060))
            self.assertEqual(len(store.records.read_text().splitlines()), 1)

    def test_live_subscription_requires_explicit_enable_and_secret(self) -> None:
        box = BoundingBox(south=33.70, west=-118.30, north=33.80, east=-118.15)
        disabled = AISStreamConfig(bounding_boxes=[box])
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            subscription_payload(disabled, {})
        enabled = disabled.model_copy(update={"enabled": True})
        with self.assertRaisesRegex(RuntimeError, "missing"):
            subscription_payload(enabled, {})
        subscription = subscription_payload(enabled, {"AISSTREAM_API_KEY": "test-secret"})
        self.assertEqual(subscription["APIKey"], "test-secret")
        self.assertNotIn("test-secret", enabled.model_dump_json())

    def test_store_recovers_when_raw_exists_without_record(self) -> None:
        raw = payload()
        result = normalize_message(raw, received_at="2026-09-09T18:05:00Z", synthetic=True)
        with tempfile.TemporaryDirectory() as folder:
            store = TrackingObservationStore(folder)
            store.raw_dir.mkdir(parents=True)
            raw_bytes = json.dumps(
                raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            (store.raw_dir / f"{result.raw_sha256}.json").write_bytes(raw_bytes)

            self.assertTrue(store.append(result, raw))
            self.assertEqual(len(store.records.read_text().splitlines()), 1)

    def test_subscription_rejects_duplicate_or_malformed_mmsi(self) -> None:
        box = BoundingBox(south=33.70, west=-118.30, north=33.80, east=-118.15)
        with self.assertRaises(ValueError):
            AISStreamConfig(bounding_boxes=[box], mmsi_filter=["bad"])
        with self.assertRaises(ValueError):
            AISStreamConfig(bounding_boxes=[box], mmsi_filter=["368207620", "368207620"])


if __name__ == "__main__":
    unittest.main()
