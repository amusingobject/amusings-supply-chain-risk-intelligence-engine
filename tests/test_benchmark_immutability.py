#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from rock_supply_intelligence.eval.e2e import write_e2e_report

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "rock_supply_intelligence_benchmark"
EXPECTED = BENCHMARK / "expected"


def _tree_hash(path: Path) -> str:
    entries = {}
    for file in sorted(path.rglob("*")):
        if file.is_file():
            rel = file.relative_to(path).as_posix()
            entries[rel] = hashlib.sha256(file.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


class ExpectedImmutabilityTests(unittest.TestCase):
    def test_write_e2e_report_refuses_expected(self) -> None:
        before = _tree_hash(EXPECTED)
        with self.assertRaises(ValueError):
            write_e2e_report({"generated_at": "t", "metrics": {}}, EXPECTED)
        self.assertEqual(_tree_hash(EXPECTED), before)

    def test_write_e2e_report_uses_runs(self) -> None:
        before = _tree_hash(EXPECTED)
        runs = BENCHMARK / "runs"
        json_path, md_path = write_e2e_report(
            {
                "generated_at": "2024-01-01T00:00:00Z",
                "metrics": {
                    "n_scenarios": 0,
                    "exposure_recall": 0,
                    "exposure_precision": 0,
                    "geographic_route_correlation": 0,
                    "deterministic_inventory_financial_fixture_accuracy": 1,
                    "unsupported_autonomous_actions": 0,
                    "placeholders_remaining": 0,
                },
            },
            runs,
        )
        self.assertTrue(str(json_path).startswith(str(runs)))
        self.assertNotIn("/expected/", json_path.as_posix())
        self.assertEqual(_tree_hash(EXPECTED), before)
        json_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)

    def test_freeze_hash_excludes_runs(self) -> None:
        source = (BENCHMARK / "tools" / "freeze_hash.py").read_text()
        self.assertIn('"runs"', source)
        self.assertIn('"reports"', source)

    def test_validate_corpus_does_not_write_expected(self) -> None:
        before = _tree_hash(EXPECTED)
        source = (BENCHMARK / "tools" / "validate_corpus.py").read_text()
        self.assertNotIn('expected").write', source)
        self.assertEqual(_tree_hash(EXPECTED), before)

    def test_t02_oracle_file_is_under_expected(self) -> None:
        path = EXPECTED / "identity" / "T02.json"
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text())
        self.assertEqual(data["task_id"], "T02")
        ids = {c["case_id"] for c in data["cases"]}
        self.assertIn("T02-POS-001", ids)
        self.assertIn("T02-NEG-001", ids)


if __name__ == "__main__":
    unittest.main()
