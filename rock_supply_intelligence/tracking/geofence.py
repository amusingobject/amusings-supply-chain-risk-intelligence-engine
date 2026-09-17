"""Deterministic geofence evaluation with review-only outcomes."""

from __future__ import annotations

from datetime import datetime

from rock_supply_intelligence.tracking.models import PortGeofence, VesselGeofenceSignal, VesselPosition


def _age_seconds(position: VesselPosition) -> float:
    observed = datetime.fromisoformat(position.observed_at.replace("Z", "+00:00"))
    received = datetime.fromisoformat(position.provenance.received_at.replace("Z", "+00:00"))
    return (received - observed).total_seconds()


def _relation(position: VesselPosition, port: PortGeofence, max_age_seconds: int) -> tuple[str, str]:
    if not position.source_valid:
        return "unknown", "provider_marked_position_invalid"
    if _age_seconds(position) > max_age_seconds:
        return "unknown", "stale_position"
    inside = port.bounds.contains(position.latitude, position.longitude)
    return ("inside", "position_inside_bounds") if inside else ("outside", "position_outside_bounds")


def evaluate_geofence(
    current: VesselPosition,
    port: PortGeofence,
    *,
    previous: VesselPosition | None = None,
    max_age_seconds: int = 900,
) -> VesselGeofenceSignal:
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    relation, reason = _relation(current, port, max_age_seconds)
    transition = "unknown"
    if relation != "unknown" and previous is None:
        transition = "first_observation"
    elif relation != "unknown" and previous is not None:
        if previous.mmsi != current.mmsi or previous.observed_at >= current.observed_at:
            relation, reason = "unknown", "invalid_observation_sequence"
        else:
            current_time = datetime.fromisoformat(current.observed_at.replace("Z", "+00:00"))
            previous_time = datetime.fromisoformat(previous.observed_at.replace("Z", "+00:00"))
            if (current_time - previous_time).total_seconds() > max_age_seconds:
                relation, reason = "unknown", "prior_position_stale"
            else:
                prior_relation, _ = _relation(previous, port, max_age_seconds)
                transitions = {
                    ("outside", "inside"): "entered",
                    ("inside", "outside"): "exited",
                    ("inside", "inside"): "continued_inside",
                    ("outside", "outside"): "continued_outside",
                }
                transition = transitions.get((prior_relation, relation), "unknown")
                if transition == "unknown":
                    relation, reason = "unknown", "prior_position_not_usable"
    return VesselGeofenceSignal(
        signal_id=f"GEO-{port.locode}-{current.observation_id}",
        observation_id=current.observation_id,
        mmsi=current.mmsi,
        port_locode=port.locode,
        observed_at=current.observed_at,
        relation=relation,
        transition=transition,
        reason=reason,
    )
