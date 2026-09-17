"""Recommendation drafts. Execution requires a separately recorded human act."""

from __future__ import annotations

from datetime import datetime, timezone

from rock_supply_intelligence.schemas.canonical import (
    Exposure,
    HumanApproval,
    Recommendation,
)
from rock_supply_intelligence.schemas.common import SCHEMA_VERSION, TENANT_POC

RULE_VERSION = "recommendation-v0.1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def draft_recommendation(exposures: list[Exposure], *, event_title: str = "") -> Recommendation:
    ts = _now()
    if not exposures:
        return Recommendation(
            id="REC-NONE",
            status="draft",
            created_at=ts,
            updated_at=ts,
            tenant_id=TENANT_POC,
            schema_version=SCHEMA_VERSION,
            evidence_ids=[],
            exposure_ids=[],
            action_type="no_action",
            recommendation_status="draft",
            rationale="No deterministic shipment linkage; do not infer operational impact.",
            assumptions=["Correlation used only explicit place/time/entity matches."],
            priority="low",
            confidence=0.9,
            human_approval=HumanApproval(state="not_requested"),
        )
    ids = [e.id for e in exposures]
    evidence = sorted({eid for e in exposures for eid in e.evidence_ids})
    stockout = any(e.inventory_risk == "stockout_expected" for e in exposures)
    action = "allocate_review" if stockout else "monitor"
    priority = "high" if stockout else "medium"
    rationale = (
        f"Deterministic linkage produced {len(exposures)} candidate exposure(s)"
        + (f" for {event_title}" if event_title else "")
        + ". Draft only; no booking, allocation, or customer communication is authorized."
    )
    return Recommendation(
        id=f"REC-{ids[0]}",
        status="draft",
        created_at=ts,
        updated_at=ts,
        tenant_id=TENANT_POC,
        schema_version=SCHEMA_VERSION,
        evidence_ids=evidence,
        exposure_ids=ids,
        action_type=action,
        recommendation_status="draft",
        rationale=rationale,
        assumptions=[
            "Delay ranges are ordinal estimates from severity mapping, not exact ETAs.",
            "Inventory identity is available = on_hand - allocated.",
        ],
        priority=priority,
        confidence=0.75,
        human_approval=HumanApproval(state="not_requested"),
    )


def apply_human_decision(
    recommendation: Recommendation,
    *,
    state: str,
    actor: str,
    at: str | None = None,
    notes: str | None = None,
) -> Recommendation:
    """The only legal path to approved/rejected. Never called by replay or bakeoff."""
    if state not in {"approved", "rejected"}:
        raise ValueError("human decision must be approved or rejected")
    if not actor:
        raise ValueError("actor is required")
    payload = recommendation.model_dump()
    payload["human_approval"] = {
        "state": state,
        "actor": actor,
        "at": at or _now(),
        "notes": notes,
    }
    payload["recommendation_status"] = "approved" if state == "approved" else "rejected"
    payload["updated_at"] = _now()
    return Recommendation.model_validate(payload)
