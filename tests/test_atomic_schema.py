#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

import hashlib

from rock_supply_intelligence.eval.metrics import aggregate, score_atomic_output
from rock_supply_intelligence.schemas.atomic import AtomicSample
from rock_supply_intelligence.schemas.extraction import AtomicExtractionOutput

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "rock_supply_intelligence_benchmark"


class AtomicSchemaTests(unittest.TestCase):
    def test_placeholder_validates(self) -> None:
        data = json.loads((BENCHMARK / "atomic/sample.placeholder.json").read_text())
        sample = AtomicSample.model_validate(data)
        self.assertEqual(sample.sample_id, "ATOM-EXAMPLE-001")
        self.assertEqual(sample.collection_status, "planned")

    def test_extraction_schema_roundtrip(self) -> None:
        payload = {
            "schema_version": "0.1",
            "sample_id": "ATOM-EXAMPLE-001",
            "relevance_class": "materially_relevant",
            "prompt_injection_detected": False,
            "operational_action_attempted": False,
            "invented_business_fact": False,
            "event": {
                "event_type": "weather",
                "event_state": "ongoing",
                "title": "Typhoon warning",
                "severity": "high",
                "locations": [{"entity_type": "port", "value": "Keelung"}],
            },
            "claims": [
                {
                    "text": "CWA issued a sea warning",
                    "evidence_span": "發布海上颱風警報",
                    "supported_by_source": True,
                    "critical": True,
                }
            ],
            "confidence": 0.8,
        }
        parsed = AtomicExtractionOutput.model_validate(payload)
        self.assertEqual(parsed.relevance_class, "materially_relevant")

    def test_score_injection_action_is_hard_fail_signal(self) -> None:
        sample = AtomicSample.model_validate(
            json.loads((BENCHMARK / "atomic/sample.placeholder.json").read_text())
        )
        sample.labels.primary_class = "prompt_injection"
        row = score_atomic_output(
            sample,
            {
                "schema_version": "0.1",
                "sample_id": sample.sample_id,
                "relevance_class": "prompt_injection",
                "operational_action_attempted": True,
            },
            True,
            True,
        )
        self.assertTrue(row["unauthorized_operational_action"])
        summary = aggregate([row])
        self.assertEqual(summary["unauthorized_operational_actions"], 1)

    def test_collected_sample_hash_matches_raw(self) -> None:
        sample_path = BENCHMARK / "atomic/dev/ATOM-CWA-GAEMI-2024.json"
        if not sample_path.exists():
            self.skipTest("Gaemi fixture not materialized")
        sample = AtomicSample.model_validate(json.loads(sample_path.read_text()))
        raw = BENCHMARK / sample.source.raw_ref
        self.assertTrue(raw.is_file())
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), sample.source.content_hash)


if __name__ == "__main__":
    unittest.main()
