#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from rock_supply_intelligence.eval.artifacts import ProtectedOutputError, assert_generated_output_dir
from rock_supply_intelligence.eval.e2e import write_e2e_report
from rock_supply_intelligence.eval.harness import run_bakeoff
from rock_supply_intelligence.eval.trust import (
    BakeoffNotReadyError,
    FrozenBenchmarkError,
    assert_benchmark_unlocked,
    assess_trust,
    assess_trust_from_records,
    freeze_allowed,
    freeze_tree_entries,
    require_official_bakeoff,
)
from rock_supply_intelligence.providers.base import CompletionRequest, CompletionResult
from rock_supply_intelligence.schemas.atomic import AtomicSample

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "rock_supply_intelligence_benchmark"

COMPLETE_COUNTS = {
    "split_counts": Counter({"dev": 120, "selection": 150, "holdout": 150}),
    "class_counts": Counter(
        {
            "materially_relevant": 150,
            "monitor": 50,
            "irrelevant": 130,
            "ambiguous_conflicting": 50,
            "prompt_injection": 40,
        }
    ),
    "lang_counts": Counter({"en": 250, "zh-TW": 120, "mixed": 50}),
    "cat_counts": Counter(
        {
            "weather_natural_disaster": 80,
            "port_vessel_carrier": 95,
            "labor_infrastructure_transportation": 70,
            "geopolitical_security": 60,
            "regulatory_trade_customs": 35,
            "irrelevant_general_world": 80,
        }
    ),
}


def _manifest(**kwargs) -> dict:
    base = {
        "benchmark_id": "rock-supply-intelligence",
        "benchmark_version": "0.1.1-draft",
        "status": "scaffold_unlocked",
        "completeness": {
            "atomic_samples_target": 420,
            "atomic_samples_collected": 420,
            "raw_bodies_retained": 420,
            "scenario_manifests": 28,
            "expected_atomic_labels_reviewed": 0,
        },
        "label_review": {
            "state": "not_complete",
            "reviewed_count": 0,
            "completed_at": None,
            "reviewer": None,
        },
        "freeze": {
            "hash_algorithm": "sha256",
            "tree_hash": None,
            "locked_at": None,
            "lock_policy": "new version",
        },
    }
    for key, value in kwargs.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merged = dict(base[key])
            merged.update(value)
            base[key] = merged
        else:
            base[key] = value
    return base


def _complete_reviewed_locked() -> dict:
    digest = "a" * 64
    return _manifest(
        status="locked",
        completeness={
            "atomic_samples_target": 420,
            "atomic_samples_collected": 420,
            "raw_bodies_retained": 420,
            "scenario_manifests": 28,
            "expected_atomic_labels_reviewed": 420,
        },
        label_review={
            "state": "complete",
            "reviewed_count": 420,
            "completed_at": "2026-09-08T00:00:00Z",
            "reviewer": "release-manager",
        },
        freeze={
            "hash_algorithm": "sha256",
            "tree_hash": digest,
            "locked_at": "2026-09-08T00:00:00Z",
            "lock_policy": "new version",
        },
    )


class FakeProvider:
    name = "fake"
    model = "none"

    def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(text="{}", parsed=None, schema_valid=False, provider=self.name, model=self.model)


class TrustStatusTests(unittest.TestCase):
    def test_current_benchmark_is_collected_but_unreviewed_and_untrusted(self) -> None:
        trust = assess_trust(BENCHMARK)
        self.assertFalse(trust.release_ready)
        self.assertFalse(trust.trusted)
        self.assertEqual(trust.status, "INCOMPLETE")
        # Valid human rejections can temporarily reopen collection slots; this
        # fixture test verifies the trust gate, not a mutable worktree count.
        self.assertGreater(trust.collected_samples, 0)
        self.assertLessEqual(trust.collected_samples, 420)
        self.assertTrue(any("review" in u for u in trust.unmet))
        self.assertTrue(any("tree_hash" in u for u in trust.unmet))
        self.assertIn("NOT RELEASE-READY", trust.banner())
        self.assertNotIn("official bakeoff output", trust.banner())

    def test_unlocked_hashless_manifest_is_untrusted_when_corpus_complete(self) -> None:
        trust = assess_trust_from_records(
            _manifest(
                completeness={
                    "atomic_samples_target": 420,
                    "atomic_samples_collected": 420,
                    "raw_bodies_retained": 420,
                    "scenario_manifests": 28,
                    "expected_atomic_labels_reviewed": 420,
                },
                label_review={
                    "state": "complete",
                    "reviewed_count": 420,
                    "completed_at": "2026-09-08T00:00:00Z",
                    "reviewer": "release-manager",
                },
            ),
            collected_count=420,
            current_tree_hash="b" * 64,
            **COMPLETE_COUNTS,
        )
        self.assertEqual(trust.status, "UNTRUSTED")
        self.assertFalse(trust.release_ready)
        self.assertTrue(any("tree_hash" in u for u in trust.unmet))
        self.assertTrue(any("locked" in u for u in trust.unmet))

    def test_complete_unreviewed_cannot_freeze(self) -> None:
        trust = assess_trust_from_records(
            _manifest(),
            collected_count=420,
            **COMPLETE_COUNTS,
        )
        blocking = freeze_allowed(trust)
        self.assertTrue(blocking)
        self.assertTrue(any("review" in item for item in blocking))

    def test_official_readiness_fails_on_unreviewed_unlocked_corpus(self) -> None:
        with self.assertRaises(BakeoffNotReadyError) as ctx:
            require_official_bakeoff(BENCHMARK)
        self.assertIn("not release-ready", str(ctx.exception))
        self.assertIn("expected-label review state", str(ctx.exception))
        self.assertIn("tree_hash is missing", str(ctx.exception))

    def test_official_readiness_passes_only_when_all_conditions_met(self) -> None:
        digest = "a" * 64
        trust = assess_trust_from_records(
            _complete_reviewed_locked(),
            collected_count=420,
            current_tree_hash=digest,
            **COMPLETE_COUNTS,
        )
        self.assertEqual(trust.status, "TRUSTED")
        self.assertTrue(trust.release_ready)
        self.assertTrue(trust.frozen)
        self.assertEqual(trust.unmet, [])
        self.assertIn("TRUSTED / FROZEN", trust.banner())

    def test_incomplete_quotas_block_trust_even_if_count_is_420(self) -> None:
        counts = dict(COMPLETE_COUNTS)
        counts["class_counts"] = Counter({"materially_relevant": 420})
        trust = assess_trust_from_records(
            _complete_reviewed_locked(),
            collected_count=420,
            current_tree_hash="a" * 64,
            **counts,
        )
        self.assertFalse(trust.release_ready)
        self.assertTrue(any("quota primary_class" in u for u in trust.unmet))


class ReportPathTests(unittest.TestCase):
    def test_rejects_every_protected_directory(self) -> None:
        payload = {"generated_at": "t", "metrics": {}}
        for name in ("expected", "holdout_sealed", "scenarios", "atomic", "raw", "scoring", "schemas"):
            dest = BENCHMARK / name
            with self.subTest(name):
                with self.assertRaises(ProtectedOutputError):
                    write_e2e_report(payload, dest)

    def test_assert_generated_output_dir_allows_runs_and_reports(self) -> None:
        assert_generated_output_dir(BENCHMARK / "runs", BENCHMARK)
        assert_generated_output_dir(BENCHMARK / "reports", BENCHMARK)

    def test_freeze_tree_excludes_runs_and_reports(self) -> None:
        entries = freeze_tree_entries(BENCHMARK)
        self.assertTrue(entries)
        self.assertFalse(any(path.startswith("runs/") for path in entries))
        self.assertFalse(any(path.startswith("reports/") for path in entries))
        self.assertNotIn("manifest.json", entries)


class LockedMutationTests(unittest.TestCase):
    def test_locked_benchmark_mutation_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps(_complete_reviewed_locked()) + "\n")
            with self.assertRaises(FrozenBenchmarkError):
                assert_benchmark_unlocked(root)

    def test_unlocked_allows_mutation_guard_to_pass(self) -> None:
        assert_benchmark_unlocked(BENCHMARK)


class DevelopmentBakeoffTests(unittest.TestCase):
    def _sample(self) -> AtomicSample:
        return AtomicSample.model_validate(
            json.loads((BENCHMARK / "atomic/sample.placeholder.json").read_text())
        )

    def test_development_only_is_untrusted_and_skips_holdout(self) -> None:
        sample = self._sample()
        sample.collection_status = "collected"
        report = run_bakeoff(
            FakeProvider(),
            samples=[sample],
            benchmark_root=BENCHMARK,
            report_dir=BENCHMARK / "runs",
            development_only=True,
        )
        self.assertEqual(report["result_class"], "development_untrusted")
        self.assertFalse(report["claims_benchmark_validity"])
        self.assertTrue(report["development_only"])
        self.assertFalse(report["allow_holdout"])
        self.assertFalse(report["benchmark_trust"]["release_ready"])
        self.assertIn("dev-untrusted-", Path(report["json_path"]).name)
        Path(report["json_path"]).unlink(missing_ok=True)
        Path(report["md_path"]).unlink(missing_ok=True)

    def test_development_only_cannot_combine_holdout(self) -> None:
        with self.assertRaises(BakeoffNotReadyError):
            run_bakeoff(
                FakeProvider(),
                samples=[],
                benchmark_root=BENCHMARK,
                development_only=True,
                allow_holdout=True,
            )

    def test_official_bakeoff_refuses_current_incomplete_corpus(self) -> None:
        with self.assertRaises(BakeoffNotReadyError):
            run_bakeoff(FakeProvider(), samples=[], benchmark_root=BENCHMARK, development_only=False)

    def test_official_bakeoff_has_no_trust_override(self) -> None:
        forged = assess_trust_from_records(
            _complete_reviewed_locked(),
            collected_count=420,
            current_tree_hash="a" * 64,
            **COMPLETE_COUNTS,
        )
        self.assertTrue(forged.release_ready)
        with self.assertRaises(TypeError):
            run_bakeoff(
                FakeProvider(),
                samples=[],
                benchmark_root=BENCHMARK,
                development_only=False,
                trust=forged,
            )


if __name__ == "__main__":
    unittest.main()
