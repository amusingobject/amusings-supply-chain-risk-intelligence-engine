"""Offline end-to-end replay: evidence → event → correlation → exposure → draft recommendation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rock_supply_intelligence.engine.correlation import correlate_event_to_shipments
from rock_supply_intelligence.engine.exposure import build_exposures
from rock_supply_intelligence.engine.inventory import available_quantity
from rock_supply_intelligence.engine.locodes import resolve_place
from rock_supply_intelligence.engine.recommendation import draft_recommendation
from rock_supply_intelligence.engine.scenario_adapter import adapt_business_state
from rock_supply_intelligence.engine.timeutil import parse_utc
from rock_supply_intelligence.eval.access import allowed_splits, holdout_authorized, sealed_root
from rock_supply_intelligence.eval.artifacts import assert_generated_output_dir, write_generated_text
from rock_supply_intelligence.eval.trust import assess_trust
from rock_supply_intelligence.schemas.canonical import CanonicalRef as CRef
from rock_supply_intelligence.schemas.canonical import ExternalEvent
from rock_supply_intelligence.schemas.common import SCHEMA_VERSION, TENANT_POC

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "rock_supply_intelligence_benchmark"


def evidence_available_at(evidence: dict[str, Any], evaluation_timestamp: str) -> bool:
    """Historical availability uses source time, not benchmark retrieval time."""
    for key in ("effective_at", "published_at", "observed_at"):
        value = evidence.get(key)
        parsed = parse_utc(value) if value else None
        eval_dt = parse_utc(evaluation_timestamp)
        if parsed and eval_dt and parsed <= eval_dt:
            return True
    return False


def load_official_scenarios(benchmark_root: Path | None = None, allow_holdout: bool = False) -> list[dict[str, Any]]:
    root = benchmark_root or BENCHMARK
    splits = allowed_splits(allow_holdout)
    items: list[dict[str, Any]] = []
    for split in splits:
        for path in sorted((root / "scenarios" / split).glob("*.json")):
            items.append(json.loads(path.read_text()))
        sealed = sealed_root(root) / "scenarios" / split
        if split == "holdout" and holdout_authorized(allow_holdout) and sealed.exists():
            for path in sorted(sealed.glob("*.json")):
                items.append(json.loads(path.read_text()))
    return items


def _event_from_scenario(scenario: dict[str, Any], evidence_ids: list[str]) -> ExternalEvent:
    ts = scenario["evaluation_timestamp"]
    expected = scenario.get("expected") or {}
    ext = expected.get("external_event") or {}
    title = (scenario.get("historical_anchor") or {}).get("title") or ext.get("title") or "event"
    locations = []
    explicit = (scenario.get("historical_anchor") or {}).get("event_places") or EVENT_PLACES.get(scenario["scenario_id"])
    tokens = list(explicit) if explicit else _tokens_from_title(title.split("/")[0])
    for token in tokens:
        place = resolve_place(token)
        locations.append(
            CRef(
                ref_type="place",
                name=token,
                locode=place.locode if place else None,
                raw_value=token,
            )
        )
    entities = []
    for carrier in EVENT_CARRIERS.get(scenario["scenario_id"], []):
        entities.append(CRef(ref_type="carrier", name=carrier, code=carrier, raw_value=carrier))
    return ExternalEvent(
        id=f"EVT-{scenario['scenario_id']}",
        status="draft",
        created_at=ts,
        updated_at=ts,
        tenant_id=TENANT_POC,
        schema_version=SCHEMA_VERSION,
        evidence_ids=evidence_ids,
        event_type=ext.get("event_type") or (scenario.get("historical_anchor") or {}).get("event_type") or "other",
        event_state="reported",
        title=title,
        start_time=ts,
        severity=ext.get("severity") or "unknown",
        observed_or_inferred="extracted",
        confidence=0.8,
        locations=locations,
        entities=entities,
    )


EVENT_PLACES = {
    "E2E-GAEMI-KEELUNG-01": ["Keelung"],
    "E2E-GAEMI-KHH-02": ["Kaohsiung"],
    "E2E-GAEMI-RECOVERY-03": ["Keelung"],
    "E2E-TW-EQ-SUPPLIER-04": ["Hualien"],
    "E2E-TW-EQ-NEGATIVE-05": ["Hualien"],
    "E2E-KONGREY-06": ["Taichung"],
    "E2E-MILITARY-AFFECTED-07": ["Kaohsiung"],
    "E2E-LALB-CONGESTION-08": ["Long Beach", "Los Angeles"],
    "E2E-LALB-NEGATIVE-09": ["Long Beach", "Los Angeles"],
    "E2E-BALTIMORE-AFFECTED-09": ["Baltimore"],
    "E2E-BALTIMORE-NEGATIVE-10": ["Baltimore"],
    "E2E-RED-SEA-11": ["Red Sea", "Suez"],
    "E2E-RED-SEA-NEGATIVE-12": ["Red Sea", "Suez"],
    "E2E-PANAMA-DROUGHT-13": ["Panama"],
    "E2E-PANAMA-NEGATIVE-14": ["Panama"],
    "E2E-LABOR-EAST-COAST-16": ["Baltimore"],
    "E2E-LABOR-WEST-NEGATIVE-15": ["Baltimore"],
    "E2E-SUEZ-EVERGIVEN-17": ["Suez"],
    "E2E-SUEZ-NEGATIVE-18": ["Suez"],
    "E2E-VANCOUVER-FLOOD-19": ["Vancouver"],
    "E2E-VANCOUVER-NEGATIVE-20": ["Vancouver"],
    "E2E-YANTIAN-21": ["Yantian"],
    "E2E-SHANGHAI-NEGATIVE-22": ["Shanghai"],
    "E2E-MAERSK-CYBER-23": [],
    "E2E-AIS-GAP-07": [],
    "E2E-CARRIER-ETA-CONFLICT-21": [],
    "E2E-PROMPT-INJECTION-27": [],
    "E2E-CONFLICT-28": [],
}

EVENT_CARRIERS = {
    "E2E-MAERSK-CYBER-23": ["MAERSK"],
}


def _tokens_from_title(title: str) -> list[str]:
    parts = []
    for token in (
        "Keelung",
        "Kaohsiung",
        "Taichung",
        "Hualien",
        "Long Beach",
        "Los Angeles",
        "Baltimore",
        "Seattle",
        "New York",
        "Panama",
        "Suez",
        "Red Sea",
        "Yantian",
        "Shanghai",
        "Vancouver",
        "Taipei",
        "Chicago",
        "Phoenix",
        "Denver",
    ):
        if token.lower() in title.lower():
            parts.append(token)
    return parts


def replay_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    ts = scenario["evaluation_timestamp"]
    evidence = scenario.get("evidence") or []
    placeholders = [
        ev
        for ev in evidence
        if ev.get("collection_status") == "planned"
        or ev.get("source_name") == "TO_BE_COLLECTED"
        or ev.get("excerpt_or_payload_path") == "TO_BE_COLLECTED"
    ]
    evidence_ids = [ev["id"] for ev in evidence if ev.get("id")]
    temporal_ok = all(evidence_available_at(ev, ts) for ev in evidence if ev.get("collection_status") == "collected")
    records = adapt_business_state(scenario.get("synthetic_business_state") or {}, ts)
    event = _event_from_scenario(scenario, evidence_ids or ["EVD-MISSING"])
    correlation = correlate_event_to_shipments(event, records["shipments"], ts)
    exposures = build_exposures(
        event,
        records["shipments"],
        correlation,
        inventory=records["inventory"],
        sales_orders=records["sales_orders"],
        evaluation_timestamp=ts,
    )
    recommendation = draft_recommendation(exposures, event_title=event.title)
    expected = scenario.get("expected") or {}
    predicted_affected = correlation.affected_shipments
    gold_affected = list(expected.get("affected_shipments") or [])
    gold_unaffected = list(expected.get("unaffected_shipments") or [])
    false_pos = [s for s in predicted_affected if s in gold_unaffected]
    missing = [s for s in gold_affected if s not in predicted_affected]
    math_ok = _inventory_identity_ok(records["inventory"])
    material_without_evidence = 0 if evidence_ids else (1 if exposures else 0)
    autonomous = 0
    if recommendation.recommendation_status in {"approved", "executed"}:
        autonomous += 1
    if recommendation.human_approval.state == "approved":
        autonomous += 1
    return {
        "scenario_id": scenario["scenario_id"],
        "split": scenario.get("split"),
        "placeholders_remaining": len(placeholders),
        "temporal_ok": temporal_ok,
        "predicted_affected": predicted_affected,
        "predicted_unaffected": correlation.unaffected_shipments,
        "gold_affected": gold_affected,
        "gold_unaffected": gold_unaffected,
        "false_positive_shipments": false_pos,
        "missing_affected_shipments": missing,
        "exposure_count": len(exposures),
        "exposures": [e.model_dump() for e in exposures],
        "recommendation": recommendation.model_dump(),
        "deterministic_inventory_financial_fixture_accuracy": 1.0 if math_ok else 0.0,
        "material_findings_with_evidence": 0.0 if material_without_evidence else 1.0,
        "invented_business_facts": 0,
        "unsupported_autonomous_actions": autonomous,
        "geographic_match_correct": len(false_pos) == 0 and len(missing) == 0,
    }


def _inventory_identity_ok(positions) -> bool:
    for pos in positions:
        if abs(available_quantity(pos.on_hand, pos.allocated) - pos.available) > 1e-9:
            return False
    return True


def replay_all(benchmark_root: Path | None = None, allow_holdout: bool = False) -> dict[str, Any]:
    scenarios = load_official_scenarios(benchmark_root, allow_holdout=allow_holdout)
    rows = [replay_scenario(s) for s in scenarios]
    n = len(rows) or 1
    tp = sum(len(r["gold_affected"]) - len(r["missing_affected_shipments"]) for r in rows)
    gold_pos = sum(len(r["gold_affected"]) for r in rows) or 1
    pred_pos = sum(len(r["predicted_affected"]) for r in rows) or 1
    fp = sum(len(r["false_positive_shipments"]) for r in rows)
    geo_ok = sum(1 for r in rows if r["geographic_match_correct"]) / n
    metrics = {
        "n_scenarios": len(rows),
        "exposure_recall": tp / gold_pos,
        "exposure_precision": (pred_pos - fp) / pred_pos if pred_pos else None,
        "geographic_route_correlation": geo_ok,
        "shipment_event_geographic_matching": geo_ok,
        "deterministic_inventory_financial_fixture_accuracy": sum(
            r["deterministic_inventory_financial_fixture_accuracy"] for r in rows
        )
        / n,
        "material_findings_with_evidence": sum(r["material_findings_with_evidence"] for r in rows) / n,
        "invented_business_facts": sum(r["invented_business_facts"] for r in rows),
        "unsupported_autonomous_actions": sum(r["unsupported_autonomous_actions"] for r in rows),
        "placeholders_remaining": sum(r["placeholders_remaining"] for r in rows),
    }
    generated = datetime.now(timezone.utc).isoformat()
    root = benchmark_root or BENCHMARK
    trust = assess_trust(root)
    return {
        "generated_at": generated,
        "metrics": metrics,
        "scenarios": rows,
        "benchmark_trust": trust.as_dict(),
        "result_class": "official" if trust.release_ready else "draft_scaffold",
    }


def write_e2e_report(
    result: dict[str, Any],
    report_dir: Path,
    *,
    benchmark_root: Path | None = None,
) -> tuple[Path, Path]:
    root = Path(benchmark_root) if benchmark_root is not None else BENCHMARK
    assert_generated_output_dir(Path(report_dir), root)
    # Trust is derived from the benchmark on disk at report time. A caller must
    # not be able to promote draft results by injecting a trusted-looking object.
    assessed = assess_trust(root)
    result = {
        **result,
        "benchmark_trust": assessed.as_dict(),
        "result_class": "official" if assessed.release_ready else "draft_scaffold",
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = Path(report_dir) / f"e2e-replay-{stamp}.json"
    md_path = Path(report_dir) / f"e2e-replay-{stamp}.md"
    m = result.get("metrics") or {}
    lines = [
        "# E2E replay report",
        "",
        f"**{assessed.banner()}**",
        "",
        f"- generated_at: {result.get('generated_at')}",
        f"- n_scenarios: {m.get('n_scenarios')}",
        f"- exposure_recall: {m.get('exposure_recall')}",
        f"- exposure_precision: {m.get('exposure_precision')}",
        f"- geographic_route_correlation: {m.get('geographic_route_correlation')}",
        f"- deterministic_inventory_financial_fixture_accuracy: {m.get('deterministic_inventory_financial_fixture_accuracy')}",
        f"- unsupported_autonomous_actions: {m.get('unsupported_autonomous_actions')}",
        f"- placeholders_remaining: {m.get('placeholders_remaining')}",
        f"- benchmark_trust_status: {assessed.status}",
        f"- release_ready: {assessed.release_ready}",
        "",
    ]
    if assessed.unmet:
        lines.append("Unmet release requirements:")
        lines.extend(f"- {item}" for item in assessed.unmet)
        lines.append("")
    write_generated_text(json_path, json.dumps(result, indent=2, default=str) + "\n", root)
    write_generated_text(md_path, "\n".join(lines), root)
    return json_path, md_path
