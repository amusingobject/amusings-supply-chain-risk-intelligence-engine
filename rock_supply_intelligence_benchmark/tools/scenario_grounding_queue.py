#!/usr/bin/env python3
"""Write a review queue for scenario claims lacking operational evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPERATIONAL_WORDS = ("port", "terminal", "closure", "closed", "restriction", "reopen", "carrier")


def required_support(scenario: dict) -> set[str]:
    anchor = scenario.get("historical_anchor") or {}
    event = (scenario.get("expected") or {}).get("external_event") or {}
    event_type = str(event.get("event_type") or anchor.get("event_type") or "").lower()
    title = str(anchor.get("title") or "").lower()
    if event_type in {"port_disruption", "port_congestion", "carrier_exception"} or any(
        word in title for word in OPERATIONAL_WORDS
    ):
        return {"port_operations", "carrier_service", event_type}
    return set()


def scenarios() -> list[Path]:
    paths = list((ROOT / "scenarios").glob("*/*.json"))
    paths.extend((ROOT / "holdout_sealed" / "scenarios").glob("*/*.json"))
    return sorted(paths)


def queue() -> list[tuple[Path, dict, set[str]]]:
    result: list[tuple[Path, dict, set[str]]] = []
    for path in scenarios():
        data = json.loads(path.read_text())
        needed = required_support(data)
        if not needed:
            continue
        actual = {
            str(claim).lower()
            for evidence in data.get("evidence") or []
            if evidence.get("collection_status") == "collected"
            for claim in evidence.get("supported_claims") or []
        }
        if not actual & needed:
            result.append((path, data, needed))
    return result


def render(items: list[tuple[Path, dict, set[str]]]) -> str:
    lines = [
        "# Scenario Grounding Queue",
        "",
        "This is a collection/review queue. It does not modify scenario expectations, "
        "create evidence, or certify operational claims.",
        "",
        "| Scenario | Split | Missing support | Collection requirement |",
        "| --- | --- | --- | --- |",
    ]
    for path, scenario, needed in items:
        anchor = scenario.get("historical_anchor") or {}
        title = str(anchor.get("title") or scenario.get("scenario_id") or "unknown")
        split = str(scenario.get("split") or "unknown")
        support = ", ".join(f"`{item}`" for item in sorted(needed))
        requirement = "Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient."
        lines.append(f"| {title} | {split} | {support} | {requirement} |")
    lines.extend(["", f"Open items: {len(items)}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "scenario-grounding-queue.md")
    args = parser.parse_args()
    items = queue()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(items))
    print(f"wrote {args.output} ({len(items)} open items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
