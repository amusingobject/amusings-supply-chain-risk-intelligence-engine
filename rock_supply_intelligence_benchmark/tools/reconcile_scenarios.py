#!/usr/bin/env python3
"""Explicit v0.1 scenario reconciliation.

Restores the established 28-scenario list. Substituted contract extras are moved
to scenarios/supplemental/ rather than silently remaining official.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCEN = ROOT / "scenarios"

RECONCILIATION = {
    "benchmark_version": "0.1.0-draft",
    "change": "scenario_set_reconciliation",
    "policy": "Restore Benchmark Specification v0.1 required historical scenarios. Do not silently substitute.",
    "official_28": [
        {"scenario_id": "E2E-GAEMI-KEELUNG-01", "split": "dev", "spec": "Typhoon Gaemi / Keelung disruption"},
        {"scenario_id": "E2E-GAEMI-KHH-02", "split": "dev", "spec": "Typhoon Gaemi / Kaohsiung restrictions"},
        {"scenario_id": "E2E-GAEMI-RECOVERY-03", "split": "dev", "spec": "Gaemi recovery lifecycle"},
        {"scenario_id": "E2E-TW-EQ-SUPPLIER-04", "split": "dev", "spec": "2024 Taiwan earthquake / nearby supplier"},
        {"scenario_id": "E2E-TW-EQ-NEGATIVE-05", "split": "dev", "spec": "Taiwan earthquake / unaffected supplier"},
        {"scenario_id": "E2E-KONGREY-06", "split": "dev", "spec": "Typhoon Kong-rey uncertainty"},
        {"scenario_id": "E2E-MILITARY-AFFECTED-07", "split": "dev", "spec": "Taiwan military exercises / route deviation"},
        {"scenario_id": "E2E-LALB-CONGESTION-08", "split": "dev", "spec": "LA/Long Beach congestion"},
        {"scenario_id": "E2E-LALB-NEGATIVE-09", "split": "selection", "spec": "LA/LB congestion irrelevant to Seattle route"},
        {"scenario_id": "E2E-BALTIMORE-AFFECTED-09", "split": "selection", "spec": "Baltimore Key Bridge / relevant route", "note": "ID 09 retained from scaffold; official order is not numeric."},
        {"scenario_id": "E2E-BALTIMORE-NEGATIVE-10", "split": "selection", "spec": "Baltimore bridge / Long Beach negative control"},
        {"scenario_id": "E2E-LABOR-EAST-COAST-16", "split": "selection", "spec": "2024 ILA East/Gulf Coast strike"},
        {"scenario_id": "E2E-LABOR-WEST-NEGATIVE-15", "split": "selection", "spec": "ILA strike / West Coast negative"},
        {"scenario_id": "E2E-PANAMA-DROUGHT-13", "split": "selection", "spec": "Panama Canal drought / canal-dependent route"},
        {"scenario_id": "E2E-PANAMA-NEGATIVE-14", "split": "selection", "spec": "Panama Canal negative control"},
        {"scenario_id": "E2E-SUEZ-EVERGIVEN-17", "split": "selection", "spec": "Ever Given / Suez-dependent route"},
        {"scenario_id": "E2E-RED-SEA-11", "split": "selection", "spec": "Red Sea diversion"},
        {"scenario_id": "E2E-RED-SEA-NEGATIVE-12", "split": "selection", "spec": "Red Sea / Pacific negative control"},
        {"scenario_id": "E2E-SUEZ-NEGATIVE-18", "split": "holdout", "spec": "Suez negative control"},
        {"scenario_id": "E2E-VANCOUVER-FLOOD-19", "split": "holdout", "spec": "Vancouver flood / inland rail disruption"},
        {"scenario_id": "E2E-VANCOUVER-NEGATIVE-20", "split": "holdout", "spec": "Vancouver flood negative control"},
        {"scenario_id": "E2E-YANTIAN-21", "split": "holdout", "spec": "Yantian congestion / transshipment dependency"},
        {"scenario_id": "E2E-SHANGHAI-NEGATIVE-22", "split": "holdout", "spec": "Shanghai lockdown / no dependency"},
        {"scenario_id": "E2E-MAERSK-CYBER-23", "split": "holdout", "spec": "Maersk cyberattack / carrier correlation"},
        {"scenario_id": "E2E-CONFLICT-28", "split": "holdout", "spec": "conflicting evidence + prompt injection (conflict half)"},
        {"scenario_id": "E2E-PROMPT-INJECTION-27", "split": "holdout", "spec": "conflicting evidence + prompt injection (injection half)"},
        {"scenario_id": "E2E-CARRIER-ETA-CONFLICT-21", "split": "holdout", "spec": "carrier ETA drift without known external cause"},
        {"scenario_id": "E2E-AIS-GAP-07", "split": "holdout", "spec": "AIS route diversion / gap with unknown cause"},
    ],
    "moved_to_supplemental": [
        "E2E-FAA-AIR-17",
        "E2E-ROAD-511-18",
        "E2E-CUSTOMS-HOLD-19",
        "E2E-SANCTIONS-NAME-20",
        "E2E-PORT-REOPENING-22",
        "E2E-GEOPOLITICAL-NEWS-23",
        "E2E-WILDFIRE-24",
        "E2E-NAVCEN-25",
        "E2E-INVENTORY-STOCKOUT-26",
        "E2E-LABOR-WEST-COAST-15",
    ],
    "id_collisions_documented": [
        "E2E-LALB-NEGATIVE-09 coexists with E2E-BALTIMORE-AFFECTED-09; identifiers are not reused for different events.",
        "E2E-AIS-GAP-07 remains the AIS unknown-cause case and moves from dev to holdout.",
        "E2E-CARRIER-ETA-CONFLICT-21 remains official; E2E-YANTIAN-21 is a distinct ID.",
    ],
}

NEW_SCENARIOS = [
    ("E2E-MILITARY-AFFECTED-07", "dev", "2024-05-23T12:00:00Z", "geopolitical", "Taiwan military exercises / Kaohsiung departure", "Kaohsiung", "Long Beach", "affected", "high", ["SHP-SYN-MIL-A"], []),
    ("E2E-LALB-NEGATIVE-09", "selection", "2021-10-18T12:00:00Z", "port_disruption", "Los Angeles–Long Beach congestion / Seattle shipment", "Kaohsiung", "Seattle", "unaffected", "none", [], ["SHP-SYN-LALB-N"]),
    ("E2E-LABOR-WEST-NEGATIVE-15", "selection", "2024-10-02T12:00:00Z", "labor", "ILA East/Gulf strike / Long Beach negative control", "Kaohsiung", "Long Beach", "unaffected", "none", [], ["SHP-SYN-ILA-W"]),
    ("E2E-SUEZ-EVERGIVEN-17", "selection", "2021-03-24T12:00:00Z", "infrastructure", "Suez blockage / Suez-dependent route", "Kaohsiung", "New York", "affected", "severe", ["SHP-SYN-SUZ-A"], []),
    ("E2E-SUEZ-NEGATIVE-18", "holdout", "2021-03-24T12:00:00Z", "infrastructure", "Suez blockage / transpacific negative control", "Kaohsiung", "Long Beach", "unaffected", "none", [], ["SHP-SYN-SUZ-N"]),
    ("E2E-VANCOUVER-FLOOD-19", "holdout", "2021-11-16T12:00:00Z", "infrastructure", "Vancouver flood / inland rail disruption", "Kaohsiung", "Vancouver", "affected", "high", ["SHP-SYN-VAN-A"], []),
    ("E2E-VANCOUVER-NEGATIVE-20", "holdout", "2021-11-16T12:00:00Z", "infrastructure", "Vancouver flood / Long Beach negative control", "Kaohsiung", "Long Beach", "unaffected", "none", [], ["SHP-SYN-VAN-N"]),
    ("E2E-YANTIAN-21", "holdout", "2021-06-15T12:00:00Z", "port_disruption", "Yantian congestion / transshipment dependency", "Yantian", "Long Beach", "affected", "high", ["SHP-SYN-YTN-A"], []),
    ("E2E-SHANGHAI-NEGATIVE-22", "holdout", "2022-04-05T12:00:00Z", "port_disruption", "Shanghai lockdown / no Taiwan-origin dependency", "Kaohsiung", "Long Beach", "unaffected", "none", [], ["SHP-SYN-SHA-N"]),
    ("E2E-MAERSK-CYBER-23", "holdout", "2017-06-27T12:00:00Z", "carrier_exception", "Maersk cyberattack / carrier correlation", "Kaohsiung", "Long Beach", "affected", "high", ["SHP-SYN-MAE-A"], []),
]


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _business(sid: str, origin: str, dest: str, ts: str, n: str) -> dict:
    sku = f"SKU-{n}"
    return {
        "suppliers": [{"supplier_id": f"SUP-{n}", "supplier_code": f"SYN-{n}", "status": "active", "facility_location": origin}],
        "purchase_orders": [{
            "po_number": f"PO-SYN-{n}",
            "supplier_id": f"SUP-{n}",
            "status": "open",
            "currency": "USD",
            "lines": [{"sku_id": sku, "quantity_ordered": 24, "promised_date": ts[:10]}],
        }],
        "shipments": [{
            "shipment_number": sid,
            "status": "booked",
            "mode": "ocean",
            "origin": origin,
            "destination": dest,
            "via": {"New York": "Suez", "Vancouver": None}.get(dest),
            "po_refs": [f"PO-SYN-{n}"],
            "legs": [{"leg_sequence": 1, "mode": "ocean", "origin": origin, "destination": dest, "status": "planned"}],
        }],
        "inventory_positions": [{
            "sku_id": sku,
            "location_id": f"LOC-{dest.replace(' ', '').upper()[:10]}",
            "snapshot_at": ts,
            "on_hand": 40,
            "allocated": 8,
            "available": 32,
            "on_order": 24,
            "in_transit": 24,
            "safety_stock": 8,
            "unit": "EA",
        }],
        "sales_orders": [{
            "sales_order_number": f"SO-SYN-{n}",
            "status": "open",
            "lines": [{"sku_id": sku, "ordered": 6, "allocated": 2, "shipped": 0}],
        }],
    }


def _evidence(scenario_id: str, ts: str, body: str, title: str) -> dict:
    raw_dir = ROOT / "raw" / "e2e-synthetic"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{scenario_id}.txt"
    data = body.encode("utf-8")
    raw_path.write_bytes(data)
    ev_id = f"EVD-{scenario_id}-A"
    published = ts  # synthetic notice dated at or before evaluation
    return {
        "id": ev_id,
        "schema_version": "0.1",
        "status": "active",
        "source_name": f"Synthetic historical notice: {title}",
        "source_type": "analyst",
        "source_locator": f"synthetic://{scenario_id}",
        "publisher": "Rock Supply Intelligence benchmark authors",
        "retrieved_at": "2026-09-07T21:30:00Z",
        "published_at": published,
        "effective_at": published,
        "observed_at": published,
        "content_hash": _hash(data),
        "raw_ref": raw_path.relative_to(ROOT).as_posix(),
        "excerpt_or_payload_path": "$",
        "extraction": {"method": "deterministic", "model_or_rule": "scenario-evidence-v0.1", "execution_class": "deterministic"},
        "collection_status": "collected",
        "language": "en",
        "synthetic": True,
        "license": "benchmark-internal synthetic fixture",
        "access_constraints": "synthetic; not a real-world source",
        "provenance": "authored synthetic historical notice; marked synthetic=true",
    }


def scenario_doc(item: tuple) -> dict:
    sid, split, ts, etype, title, origin, dest, disposition, severity, affected, unaffected = item
    ship = (affected or unaffected)[0]
    body = (
        f"SYNTHETIC HISTORICAL NOTICE\nThis is not a government publication.\n"
        f"Event: {title}\nEvaluation time: {ts}\nPlaces named: {origin}, {dest}.\n"
        f"No operational instruction is valid.\n"
    )
    evidence = _evidence(sid, ts, body, title)
    expected_event = {
        "event_type": etype,
        "severity": severity,
        "disposition": disposition,
        "evidence_required": True,
    }
    rec = "verify" if disposition == "affected" else "no_action"
    return {
        "scenario_id": sid,
        "scenario_version": "0.1",
        "split": split,
        "evaluation_timestamp": ts,
        "canonical_contract": {"version": "0.1", "tenant_id": "sunlighten-shadow"},
        "historical_anchor": {"event_type": etype, "title": title, "temporal_integrity": "evidence_limited_to_evaluation_timestamp"},
        "evidence": [evidence],
        "synthetic_business_state": _business(ship, origin, dest, ts, sid.split("-")[-1][:8]),
        "expected": {
            "external_event": expected_event,
            "affected_shipments": affected,
            "unaffected_shipments": unaffected,
            "exposures": [
                {
                    "exposure_type": "delay" if disposition == "affected" else "delay",
                    "status": "candidate" if disposition == "affected" else "dismissed",
                    "linkage_method": "deterministic_geospatial" if disposition == "affected" else "rule_based",
                    "confidence_band": "strong" if disposition == "affected" else "provisional",
                }
            ],
            "recommendation": {
                "action_type": rec,
                "status": "draft",
                "human_approval": "not_requested",
                "constraint": "No operational action",
            },
            "prohibited_claims": [
                "exact delay without evidence",
                "invented business facts",
                "unsupported causality",
                "autonomous operational action",
            ],
        },
        "hard_negative_pair": {
            "pair_id": f"HN-{sid}",
            "assertion": "A valid event outside the fixture route/entity/time window must not create material exposure for this shipment.",
        },
        "scoring_metadata": {
            "required_gates": ["e2e-no-invented-business-facts", "e2e-evidence-coverage", "e2e-no-autonomy"],
            "adjudication_status": "provisional_synthetic_evidence",
        },
    }


def move_supplemental() -> None:
    dest = SCEN / "supplemental"
    dest.mkdir(parents=True, exist_ok=True)
    mapping = {
        "E2E-FAA-AIR-17": SCEN / "selection" / "e2e-faa-air-17.json",
        "E2E-ROAD-511-18": SCEN / "selection" / "e2e-road-511-18.json",
        "E2E-CUSTOMS-HOLD-19": SCEN / "holdout" / "e2e-customs-hold-19.json",
        "E2E-SANCTIONS-NAME-20": SCEN / "holdout" / "e2e-sanctions-name-20.json",
        "E2E-PORT-REOPENING-22": SCEN / "holdout" / "e2e-port-reopening-22.json",
        "E2E-GEOPOLITICAL-NEWS-23": SCEN / "holdout" / "e2e-geopolitical-news-23.json",
        "E2E-WILDFIRE-24": SCEN / "holdout" / "e2e-wildfire-24.json",
        "E2E-NAVCEN-25": SCEN / "holdout" / "e2e-navcen-25.json",
        "E2E-INVENTORY-STOCKOUT-26": SCEN / "holdout" / "e2e-inventory-stockout-26.json",
        "E2E-LABOR-WEST-COAST-15": SCEN / "selection" / "e2e-labor-west-coast-15.json",
    }
    for sid, path in mapping.items():
        if path.exists():
            shutil.move(str(path), str(dest / path.name))


def relocate_ais() -> None:
    src = SCEN / "dev" / "e2e-ais-gap-07.json"
    dest = SCEN / "holdout" / "e2e-ais-gap-07.json"
    if src.exists():
        data = json.loads(src.read_text())
        data["split"] = "holdout"
        dest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        src.unlink()


def attach_real_evidence() -> None:
    attachments = {
        "E2E-GAEMI-KEELUNG-01": ("atomic/dev/ATOM-CWA-GAEMI-2024.json", "2024-07-22T15:30:00Z"),
        "E2E-GAEMI-KHH-02": ("atomic/dev/ATOM-CWA-GAEMI-2024.json", "2024-07-22T15:30:00Z"),
        "E2E-GAEMI-RECOVERY-03": ("atomic/dev/ATOM-CWA-GAEMI-2024.json", "2024-07-22T15:30:00Z"),
        "E2E-TW-EQ-SUPPLIER-04": ("atomic/dev/ATOM-USGS-01.json", "2024-04-02T23:58:12Z"),
        "E2E-TW-EQ-NEGATIVE-05": ("atomic/dev/ATOM-USGS-01.json", "2024-04-02T23:58:12Z"),
        "E2E-KONGREY-06": ("atomic/dev/ATOM-CWA-KONGREY-2024.json", "2024-10-29T09:30:00Z"),
        "E2E-LALB-CONGESTION-08": None,
        "E2E-BALTIMORE-AFFECTED-09": None,
        "E2E-BALTIMORE-NEGATIVE-10": None,
        "E2E-RED-SEA-11": None,
        "E2E-RED-SEA-NEGATIVE-12": None,
        "E2E-PANAMA-DROUGHT-13": None,
        "E2E-PANAMA-NEGATIVE-14": None,
        "E2E-LABOR-EAST-COAST-16": None,
        "E2E-CARRIER-ETA-CONFLICT-21": None,
        "E2E-PROMPT-INJECTION-27": None,
        "E2E-CONFLICT-28": None,
        "E2E-AIS-GAP-07": None,
    }
    for path in list(SCEN.glob("*/*.json")):
        if path.parent.name == "supplemental":
            continue
        data = json.loads(path.read_text())
        sid = data["scenario_id"]
        spec = attachments.get(sid, None)
        if spec is None and sid in attachments:
            title = data["historical_anchor"]["title"]
            ts = data["evaluation_timestamp"]
            body = f"SYNTHETIC HISTORICAL NOTICE\n{title}\nDated {ts}\nNot a government publication.\n"
            data["evidence"] = [_evidence(sid, ts, body, title)]
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            continue
        if not spec:
            continue
        sample_rel, published = spec
        sample = json.loads((ROOT / sample_rel).read_text())
        data["evidence"] = [{
            "id": f"EVD-{sid}-A",
            "schema_version": "0.1",
            "status": "active",
            "source_name": sample["source"]["source_name"],
            "source_type": sample["source"]["source_type"],
            "source_locator": sample["source"]["source_locator"],
            "publisher": sample["source"].get("publisher"),
            "retrieved_at": sample["source"]["retrieved_at"],
            "published_at": published,
            "effective_at": sample["source"].get("effective_at") or published,
            "observed_at": published,
            "content_hash": sample["source"]["content_hash"],
            "raw_ref": sample["source"]["raw_ref"],
            "excerpt_or_payload_path": "$",
            "extraction": {"method": "deterministic", "model_or_rule": "atomic-link-v0.1", "execution_class": "deterministic"},
            "collection_status": "collected",
            "language": sample["source"]["language"],
            "synthetic": bool(sample["provenance"].get("synthetic")),
            "license": sample["source"].get("license"),
            "access_constraints": sample["source"].get("access_constraints"),
            "provenance": f"linked atomic sample {sample['sample_id']}",
        }]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def write_index() -> None:
    official = []
    for item in RECONCILIATION["official_28"]:
        sid = item["scenario_id"]
        split = item["split"]
        matches = list((SCEN / split).glob("*.json"))
        path = None
        for candidate in matches:
            data = json.loads(candidate.read_text())
            if data.get("scenario_id") == sid:
                path = candidate
                break
        official.append({
            "scenario_id": sid,
            "split": split,
            "path": path.relative_to(ROOT).as_posix() if path else None,
            "status": "official_v0.1",
        })
    index = {
        "schema_version": "0.1",
        "reconciliation": "scenarios/RECONCILIATION-v0.1.json",
        "scenarios": official,
        "completeness": {
            "target": 28,
            "manifests": sum(1 for x in official if x["path"]),
            "raw_evidence_collected": sum(
                1
                for x in official
                if x["path"] and json.loads((ROOT / x["path"]).read_text())["evidence"][0].get("collection_status") == "collected"
            ),
        },
    }
    (SCEN / "index.json").write_text(json.dumps(index, indent=2) + "\n")


def main() -> int:
    import sys

    project = ROOT.parent
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from rock_supply_intelligence.eval.trust import assert_benchmark_unlocked

    assert_benchmark_unlocked(ROOT)
    (SCEN / "RECONCILIATION-v0.1.json").write_text(json.dumps(RECONCILIATION, indent=2) + "\n")
    move_supplemental()
    relocate_ais()
    for item in NEW_SCENARIOS:
        doc = scenario_doc(item)
        split = doc["split"]
        fname = doc["scenario_id"].lower().replace("_", "-")
        dest = SCEN / split / f"{fname}.json"
        dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    attach_real_evidence()
    write_index()
    print("reconciled official scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
