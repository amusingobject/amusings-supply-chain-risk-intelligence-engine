#!/usr/bin/env python3
"""Validate and render candidate primary evidence for scenario grounding."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "reports" / "scenario-evidence-candidates.json"
SCHEMA = ROOT / "schemas" / "scenario-evidence-candidate.schema.json"
CAPTURE_RAW = ROOT / "raw" / "scenario-grounding"


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def scenario_index(root: Path | None = None) -> dict[str, tuple[Path, dict]]:
    """Index only open scenarios; sealed holdout inputs are never read here."""
    root = ROOT if root is None else root
    result = {}
    for path in (root / "scenarios").glob("*/*.json"):
        data = json.loads(path.read_text())
        result[str(data.get("scenario_id"))] = (path, data)
    return result


def required_claims(scenario: dict) -> set[str]:
    event = (scenario.get("expected") or {}).get("external_event") or {}
    anchor = scenario.get("historical_anchor") or {}
    event_type = str(event.get("event_type") or anchor.get("event_type") or "")
    title = str(anchor.get("title") or "").lower()
    operational_words = ("port", "terminal", "closure", "closed", "restriction", "reopen", "carrier")
    if event_type == "weather" and any(word in title for word in operational_words):
        # A weather-labelled scenario can still assert an operational outcome
        # such as a closure.  In that case weather evidence alone is not enough.
        return {"port_operations", "carrier_service", "port_disruption", "carrier_exception"}
    if event_type in {"port_disruption", "port_congestion"}:
        return {"port_operations", "carrier_service", event_type}
    if event_type == "carrier_exception":
        return {"carrier_exception", "carrier_service", "port_operations"}
    return {event_type} if event_type else set()


def verify(candidate: dict, scenarios: dict[str, tuple[Path, dict]]) -> list[str]:
    errors: list[str] = []
    for key in ("candidate_id", "scenario_id", "source", "supported_claims", "excerpt"):
        if not candidate.get(key): errors.append(f"missing {key}")
    entry = scenarios.get(str(candidate.get("scenario_id")))
    if not entry: return errors + ["unknown scenario_id"]
    _, scenario = entry; source = candidate.get("source") or {}
    raw_ref = source.get("raw_ref"); locator = str(source.get("locator") or "")
    if not raw_ref or not isinstance(raw_ref, str): errors.append("missing source.raw_ref")
    else:
        raw = ROOT / raw_ref
        if not raw.is_file(): errors.append("candidate raw file missing")
        else:
            digest = hashlib.sha256(raw.read_bytes()).hexdigest()
            if digest != source.get("content_hash"): errors.append("candidate raw hash mismatch")
            text = raw.read_text(errors="replace")
            if str(candidate.get("excerpt")) not in text: errors.append("candidate excerpt not found in raw body")
    if not locator or not urlparse(locator).scheme.startswith("http"): errors.append("source locator must be direct HTTP(S)")
    if "documents.json?conditions" in locator or "search" in locator.lower(): errors.append("search-result locator is not primary evidence")
    try:
        if parse_time(str(source.get("published_at"))) > parse_time(str(scenario.get("evaluation_timestamp"))): errors.append("candidate is future-dated for scenario")
    except Exception: errors.append("invalid candidate or scenario timestamp")
    support = set(candidate.get("supported_claims") or []); required = required_claims(scenario)
    if required and not (support & required): errors.append(f"unsupported operational claim; need one of {sorted(required)}")
    if required and support == {"weather"}: errors.append("weather-only evidence cannot ground an operational claim")
    return errors


def capture(plan_path: Path, registry_path: Path = DEFAULT_REGISTRY) -> dict:
    """Capture a reviewed-plan primary source without changing scenario truth.

    The plan is deliberately limited to open scenarios.  A captured source is
    only a human-review candidate; it cannot attach itself to a scenario or
    alter expected outcomes, timestamps, or sealed holdout material.
    """
    from collect_osint import fetch

    plan = json.loads(plan_path.read_text())
    if not isinstance(plan, dict):
        raise ValueError("capture plan must be an object")
    required = {"candidate_id", "scenario_id", "publisher", "locator", "published_at", "supported_claims", "excerpt"}
    if required - plan.keys():
        raise ValueError("capture plan missing required fields")
    scenarios = scenario_index()
    entry = scenarios.get(str(plan["scenario_id"]))
    if entry is None:
        raise ValueError("unknown or sealed scenario_id")
    locator = str(plan["locator"])
    parsed = urlparse(locator)
    if parsed.scheme != "https" or "search" in locator.lower() or "documents.json?conditions" in locator:
        raise ValueError("capture locator must be a direct HTTPS non-search URL")
    published_at = str(plan["published_at"])
    if parse_time(published_at) > parse_time(str(entry[1].get("evaluation_timestamp"))):
        raise ValueError("capture source is future-dated for scenario")
    body = fetch(locator)
    if len(body) < 200:
        raise ValueError("capture payload too small")
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", body.decode("utf-8", errors="replace")))
    excerpt = str(plan["excerpt"])
    if excerpt not in text:
        raise ValueError("capture excerpt not found in source")
    digest = hashlib.sha256(body).hexdigest()
    CAPTURE_RAW.mkdir(parents=True, exist_ok=True)
    suffix = ".pdf" if body.startswith(b"%PDF") else ".html"
    raw = CAPTURE_RAW / f"{plan['candidate_id']}{suffix}"
    raw.write_bytes(body)
    candidate = {
        "candidate_id": plan["candidate_id"],
        "scenario_id": plan["scenario_id"],
        "state": "captured",
        "source": {
            "publisher": plan["publisher"],
            "locator": locator,
            "published_at": published_at,
            "raw_ref": raw.relative_to(ROOT).as_posix(),
            "content_hash": digest,
        },
        "supported_claims": plan["supported_claims"],
        "excerpt": excerpt,
        "reviewer": None,
    }
    errors = verify(candidate, scenarios)
    if errors:
        raw.unlink(missing_ok=True)
        raise ValueError("captured candidate failed verification: " + "; ".join(errors))
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else []
    if not isinstance(registry, list):
        raise ValueError("scenario evidence registry must be an array")
    if any(row.get("candidate_id") == candidate["candidate_id"] for row in registry):
        raise ValueError("duplicate candidate_id")
    registry.append(candidate)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    return {"candidate_id": candidate["candidate_id"], "raw_ref": candidate["source"]["raw_ref"], "state": "captured"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY); parser.add_argument("--json-out", type=Path); parser.add_argument("--capture-plan", type=Path)
    args = parser.parse_args(); candidates = json.loads(args.registry.read_text()) if args.registry.exists() else []
    if args.capture_plan:
        print(json.dumps(capture(args.capture_plan, args.registry), indent=2))
        return 0
    if not isinstance(candidates, list): raise SystemExit("registry must be a JSON array")
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    schema_validator = Draft202012Validator(schema)
    scenarios = scenario_index(); result = []
    for candidate in candidates:
        errors = [
            "schema: " + error.message
            for error in sorted(schema_validator.iter_errors(candidate), key=lambda item: list(item.path))
        ]
        errors.extend(verify(candidate, scenarios))
        result.append({"candidate_id": candidate.get("candidate_id"), "scenario_id": candidate.get("scenario_id"), "valid": not errors, "errors": errors})
    payload = {"candidates": result, "valid": sum(1 for x in result if x["valid"]), "invalid": sum(1 for x in result if not x["valid"])}
    if args.json_out: args.json_out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2)); return 0 if payload["invalid"] == 0 else 2

if __name__ == "__main__": raise SystemExit(main())
