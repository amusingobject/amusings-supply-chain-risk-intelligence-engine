from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "rock_supply_intelligence_benchmark/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import registry_collect as registry
import registry_discovery as discovery


class RegistryCollectionTests(unittest.TestCase):
    def test_registry_is_schema_valid_and_ids_unique(self) -> None:
        data = registry.load_registry()
        ids = [c["sample_id"] for source in data["sources"] for c in source["candidates"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(source["source_id"] == "cbp-csms" for source in data["sources"]))
        # Monitor is a first-class benchmark quota, so the registry schema must
        # permit a direct-source monitor candidate rather than forcing a relabel.
        self.assertTrue(any(
            candidate["primary_class"] == "monitor"
            for source in data["sources"]
            for candidate in source["candidates"]
        ))

    def test_url_must_be_direct_https_on_approved_domain(self) -> None:
        candidate = registry.discover(write=False)["all_candidates"][0]
        bad = copy.deepcopy(candidate); bad["url"] = "https://attacker.example/source"
        self.assertEqual(registry.validate_url(bad), "url_domain_not_approved")
        bad = copy.deepcopy(candidate); bad["url"] = f"https://{candidate['domain']}/search?q=port"
        self.assertEqual(registry.validate_url(bad), "search_result_url_forbidden")

    def test_payload_acceptance_is_term_and_hash_bound(self) -> None:
        candidate = {"url": "https://example.com/direct", "accept_terms": ["cargo operations", "resume"]}
        body = b"<html>Official notice: cargo operations will resume tomorrow." + (b" " * 200) + b"</html>"
        reason, digest = registry.validate_payload(candidate, body, set())
        self.assertIsNone(reason)
        duplicate_reason, _ = registry.validate_payload(candidate, body, {digest})
        self.assertEqual(duplicate_reason, "duplicate_content_hash")

    def test_pdf_is_detected_by_signature_without_filename_suffix(self) -> None:
        self.assertTrue(registry.is_pdf(b"%PDF-1.7\n", "https://example.com/attachment?id=1"))
        self.assertFalse(registry.is_pdf(b"<html></html>", "https://example.com/page"))

    def test_plan_excludes_existing_ids_and_reports_only_unmet_classes(self) -> None:
        plan = registry.discover(write=False)
        ready_ids = {candidate["sample_id"] for candidate in plan["ready"]}
        self.assertNotIn("ATOM-POLA-TRUCK-OPS-2024", ready_ids)
        self.assertNotIn("ATOM-OFAC-SOVCOMFLOT-2024", ready_ids)
        self.assertTrue(all(candidate["primary_class"] in {"materially_relevant", "irrelevant"} for candidate in plan["ready"]))

    def test_existing_auto_split_reports_materialized_split(self) -> None:
        plan = registry.discover(write=False)
        actual = {sample.sample_id: sample.split for sample in registry.active_samples()}
        for candidate in plan["all_candidates"]:
            if candidate["sample_id"] in actual:
                self.assertEqual(candidate["split"], actual[candidate["sample_id"]])

    def test_failure_state_is_fail_closed_and_has_backoff(self) -> None:
        state = {"candidates": {}, "sources": {}}
        candidate = {"sample_id": "ATOM-TEST-FAILURE", "source_id": "test-source"}
        registry._record_failure(state, candidate, "accept_terms_missing")
        recorded = state["candidates"][candidate["sample_id"]]
        self.assertEqual(recorded["status"], "failed")
        self.assertEqual(recorded["attempts"], 1)
        self.assertEqual(recorded["last_error"], "accept_terms_missing")
        self.assertTrue(recorded["retry_after"].endswith("Z"))

    def test_review_packet_explains_decision_and_evidence_cues(self) -> None:
        candidate = {
            "sample_id": "ATOM-TEST-REVIEW",
            "primary_class": "materially_relevant",
            "event_category": "port_vessel_carrier",
            "title": "Official operations notice",
            "accept_terms": ["cargo operations", "resume"],
            "url": "https://example.com/direct-notice",
        }
        with tempfile.TemporaryDirectory() as folder, patch.object(registry, "ROOT", Path(folder)):
            output = registry.write_review_packet([{"candidate": candidate}], "test")
            self.assertIsNotNone(output)
            text = Path(output).read_text()
            self.assertIn("What to review", text)
            self.assertIn("Keep", text)
            self.assertIn("cargo operations; resume", text)

    def test_second_collector_fails_before_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(registry, "LOCK", Path(folder) / "collector.lock"), \
             patch.object(registry.fcntl, "flock", side_effect=BlockingIOError), \
             patch.object(registry, "_run_locked") as run_locked:
            with self.assertRaisesRegex(RuntimeError, "collector already running"):
                registry.run(1)
            run_locked.assert_not_called()

    def test_explicit_sample_selection_is_exact_and_fail_closed(self) -> None:
        plan = {"ready": [
            {"sample_id": "ATOM-READY-A"},
            {"sample_id": "ATOM-READY-B"},
        ]}
        selected = registry.select_ready(plan, 1, ["ATOM-READY-B"])
        self.assertEqual([candidate["sample_id"] for candidate in selected], ["ATOM-READY-B"])
        with self.assertRaisesRegex(ValueError, "not ready"):
            registry.select_ready(plan, 1, ["ATOM-COOLING"])
        with self.assertRaisesRegex(ValueError, "must be unique"):
            registry.select_ready(plan, 2, ["ATOM-READY-A", "ATOM-READY-A"])
        with self.assertRaisesRegex(ValueError, "exceeds --limit"):
            registry.select_ready(plan, 1, ["ATOM-READY-A", "ATOM-READY-B"])

    def test_source_index_discovery_requires_direct_page_terms_and_date(self) -> None:
        source = {"source_id": "test-source", "domain": "example.gov"}
        profile = {
            "profile_id": "test-profile",
            "path_prefixes": ["/news/"],
            "include_terms": ["Russia"],
            "candidate_template": {
                "language": "en",
                "primary_class": "materially_relevant",
                "event_category": "geopolitical_security",
                "event_type": "export_control",
                "expected_disposition": "normalize",
                "accept_terms": ["export control"],
            },
        }
        body = b"""<html><title>Official export control notice</title>
        <p>Published: 2025-01-02</p><p>Russia export control action.</p></html>"""
        deficits = {"primary_class": {"materially_relevant": 3}, "language": {"en": 1}, "event_category": {"geopolitical_security": 2}}
        proposal = discovery.proposal_for_page(source, profile, "https://example.gov/news/1", body, deficits)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["status"], "requires_registry_approval")
        self.assertEqual(proposal["published_at"], "2025-01-02T00:00:00Z")
        self.assertEqual(proposal["quota_score"], 6)
        self.assertIsNone(discovery.proposal_for_page(source, profile, "https://example.gov/search?q=Russia", body, deficits))
        no_date = body.replace(b"Published: 2025-01-02", b"Published soon")
        self.assertIsNone(discovery.proposal_for_page(source, profile, "https://example.gov/news/2", no_date, deficits))
        recent_profile = copy.deepcopy(profile)
        recent_profile["not_before"] = "2025-01-03T00:00:00Z"
        self.assertIsNone(discovery.proposal_for_page(source, recent_profile, "https://example.gov/news/3", body, deficits))
        excluded_profile = copy.deepcopy(profile)
        excluded_profile["exclude_path_prefixes"] = ["/news/history/"]
        self.assertIsNone(discovery.proposal_for_page(source, excluded_profile, "https://example.gov/news/history/4", body, deficits))
        deep_profile = copy.deepcopy(profile)
        deep_profile["min_path_segments"] = 3
        self.assertIsNone(discovery.proposal_for_page(source, deep_profile, "https://example.gov/news/5", body, deficits))
        dated_profile = copy.deepcopy(profile)
        dated_profile["require_url_date_match"] = True
        self.assertIsNone(discovery.proposal_for_page(source, dated_profile, "https://example.gov/2025/june/news/6", body, deficits))

    def test_source_index_links_are_resolved_without_becoming_evidence(self) -> None:
        links = discovery.extract_links("https://example.gov/list", b'<a href="/news/one">One</a><a href="https://example.gov/news/two">Two</a>')
        self.assertEqual(links, [("https://example.gov/news/one", "One"), ("https://example.gov/news/two", "Two")])

    def test_source_index_discovery_accepts_html_datetime_metadata(self) -> None:
        title, published_at, _ = discovery.metadata(
            b'<html><title>Official notice</title><article><time datetime="2025-01-02T08:00:00Z">January 2</time></article></html>'
        )
        self.assertEqual(title, "Official notice")
        self.assertEqual(published_at, "2025-01-02T00:00:00Z")

    def test_source_index_discovery_prefers_article_heading_over_generic_site_title(self) -> None:
        title, _, _ = discovery.metadata(
            b'<meta property="og:title" content="Generic agency site"><h3 class="title print-content">Specific navigation notice</h3>'
        )
        self.assertEqual(title, "Specific navigation notice")

    def test_source_index_discovery_reads_natural_date_inside_article_only(self) -> None:
        _, published_at, _ = discovery.metadata(
            b'<article><p>June 18, 2026</p></article><time datetime="2026-09-09T12:00:00Z">latest</time>'
        )
        self.assertEqual(published_at, "2026-06-18T00:00:00Z")

    def test_source_index_discovery_rejects_unknown_source_filter(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown discovery source_id"):
            discovery.discover(limit=1, source_ids={"not-an-approved-source"})


if __name__ == "__main__":
    unittest.main()
