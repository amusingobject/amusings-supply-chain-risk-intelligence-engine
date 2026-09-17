from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rock_supply_intelligence_benchmark"
    / "tools"
    / "scenario_grounding.py"
)
TOOLS_PATH = MODULE_PATH.parent
if str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

import collect_osint

SPEC = importlib.util.spec_from_file_location("scenario_grounding", MODULE_PATH)
assert SPEC and SPEC.loader
scenario_grounding = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scenario_grounding)


def test_scenario_index_never_reads_sealed_holdout(tmp_path: Path) -> None:
    open_dir = tmp_path / "scenarios" / "selection"
    sealed_dir = tmp_path / "holdout_sealed" / "scenarios" / "holdout"
    open_dir.mkdir(parents=True)
    sealed_dir.mkdir(parents=True)
    (open_dir / "open.json").write_text(json.dumps({"scenario_id": "OPEN"}))
    (sealed_dir / "sealed.json").write_text(json.dumps({"scenario_id": "SEALED"}))

    indexed = scenario_grounding.scenario_index(tmp_path)

    assert set(indexed) == {"OPEN"}


def test_capture_keeps_open_scenario_evidence_provisional(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "benchmark"
    scenario_dir = root / "scenarios" / "dev"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "open.json").write_text(json.dumps({
        "scenario_id": "OPEN",
        "evaluation_timestamp": "2024-01-02T00:00:00Z",
        "expected": {"external_event": {"event_type": "infrastructure"}},
    }))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({
        "candidate_id": "GROUND-OPEN",
        "scenario_id": "OPEN",
        "publisher": "Primary authority",
        "locator": "https://example.gov/direct",
        "published_at": "2024-01-01T00:00:00Z",
        "supported_claims": ["infrastructure"],
        "excerpt": "booking slots reduced",
    }))
    monkeypatch.setattr(scenario_grounding, "ROOT", root)
    monkeypatch.setattr(scenario_grounding, "CAPTURE_RAW", root / "raw" / "scenario-grounding")
    monkeypatch.setattr(collect_osint, "fetch", lambda _: b"<html>booking slots reduced</html>" + b" " * 200)

    result = scenario_grounding.capture(plan, root / "reports" / "candidates.json")

    assert result["state"] == "captured"
    saved = json.loads((root / "reports" / "candidates.json").read_text())
    assert saved[0]["state"] == "captured"
    assert saved[0]["reviewer"] is None


def test_approved_route_remediations_are_explicit_and_narrow() -> None:
    root = Path(__file__).resolve().parents[1] / "rock_supply_intelligence_benchmark"
    scenarios = {
        name: json.loads((root / path).read_text())
        for name, path in {
            "panama_affected": "scenarios/selection/e2e-panama-drought-13.json",
            "panama_negative": "scenarios/selection/e2e-panama-negative-14.json",
            "lalb_affected": "scenarios/dev/e2e-lalb-congestion-08.json",
            "lalb_negative": "scenarios/selection/e2e-lalb-negative-09.json",
        }.items()
    }

    assert scenarios["panama_affected"]["grounding"]["route_assertions"][0]["value"] == "Panama Canal"
    assert scenarios["panama_negative"]["grounding"]["route_assertions"][0]["excludes"] == "Panama Canal"
    assert scenarios["panama_negative"]["expected"]["unaffected_shipments"] == ["SHP-SYN-014"]
    assert scenarios["lalb_affected"]["expected"]["external_event"] == {
        "event_type": "port_operations",
        "severity": "moderate",
        "disposition": "monitor",
        "evidence_required": True,
    }
    assert scenarios["lalb_affected"]["expected"]["affected_shipments"] == []
    assert scenarios["lalb_negative"]["grounding"]["route_assertions"][0]["excludes"] == "Long Beach"
    assert scenarios["lalb_negative"]["expected"]["unaffected_shipments"] == ["SHP-SYN-LALB-N"]


def test_weather_labelled_closure_requires_operational_evidence() -> None:
    scenario = {
        "historical_anchor": {"event_type": "weather", "title": "Typhoon / Keelung closure"},
        "expected": {"external_event": {"event_type": "weather"}},
    }

    assert scenario_grounding.required_claims(scenario) == {
        "port_operations",
        "carrier_service",
        "port_disruption",
        "carrier_exception",
    }


def test_approved_gaemi_weather_only_oracles_do_not_assert_shipment_impact() -> None:
    root = Path(__file__).resolve().parents[1] / "rock_supply_intelligence_benchmark"
    paths = [
        "scenarios/dev/e2e-gaemi-keelung-01.json",
        "scenarios/dev/e2e-gaemi-khh-02.json",
        "scenarios/dev/e2e-gaemi-recovery-03.json",
    ]

    for path in paths:
        scenario = json.loads((root / path).read_text())
        assert scenario["expected"]["external_event"]["event_type"] == "weather"
        assert scenario["expected"]["external_event"]["disposition"] == "monitor"
        assert scenario["expected"]["affected_shipments"] == []
        assert scenario["expected"]["exposures"][0]["linkage_method"] == "rule_based"
        assert scenario["expected"]["exposures"][0]["confidence_band"] == "provisional"
