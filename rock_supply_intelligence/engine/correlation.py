"""Deterministic event-to-shipment correlation.

AI may not confirm exposure. This module is the only allowed linkage source
besides explicit analyst confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rock_supply_intelligence.engine.locodes import locode_of, same_place
from rock_supply_intelligence.engine.timeutil import parse_utc, windows_overlap
from rock_supply_intelligence.schemas.canonical import ExternalEvent, Shipment

RULE_VERSION = "correlation-v0.1"


@dataclass(frozen=True)
class CorrelationHit:
    shipment_number: str
    affected: bool
    linkage_method: str
    reasons: tuple[str, ...]
    matched_locodes: tuple[str, ...] = ()


@dataclass
class CorrelationResult:
    event_id: str
    hits: list[CorrelationHit] = field(default_factory=list)

    @property
    def affected_shipments(self) -> list[str]:
        return [h.shipment_number for h in self.hits if h.affected]

    @property
    def unaffected_shipments(self) -> list[str]:
        return [h.shipment_number for h in self.hits if not h.affected]


def _event_place_tokens(event: ExternalEvent) -> list[str]:
    tokens: list[str] = []
    for loc in event.locations:
        for candidate in (loc.locode, loc.code, loc.name, loc.id, loc.raw_value):
            if candidate:
                tokens.append(candidate)
    return tokens


def _carrier_hits(event: ExternalEvent, shipment: Shipment) -> list[str]:
    if not shipment.carrier_id:
        return []
    wanted = {shipment.carrier_id.strip().lower()}
    hits = []
    for ent in event.entities:
        for candidate in (ent.id, ent.code, ent.name, ent.raw_value):
            if candidate and candidate.strip().lower() in wanted:
                hits.append(candidate)
    return hits


def _shipment_places(shipment: Shipment) -> list[str]:
    values = [shipment.origin, shipment.destination, shipment.origin_locode or "", shipment.destination_locode or ""]
    for leg in shipment.legs:
        values.extend([leg.origin, leg.destination, leg.origin_locode or "", leg.destination_locode or ""])
    return [v for v in values if v]


def _time_compatible(event: ExternalEvent, shipment: Shipment, evaluation_timestamp: str) -> bool:
    eval_dt = parse_utc(evaluation_timestamp)
    start = parse_utc(event.start_time)
    if eval_dt and start and start > eval_dt:
        return False
    if event.end_time and shipment.planned_departure:
        return windows_overlap(event.start_time, event.end_time, shipment.planned_departure, shipment.planned_arrival)
    return True


IMPACTING_TYPES = {
    "port_disruption",
    "labor",
    "infrastructure",
    "geopolitical",
    "aviation_disruption",
    "road_disruption",
    "customs_regulatory",
    "carrier_exception",
}


def _event_can_create_exposure(event: ExternalEvent) -> bool:
    if event.severity in {"none"}:
        return False
    if event.event_type in IMPACTING_TYPES:
        return True
    if event.event_type == "weather" and event.severity in {"high", "severe"}:
        return True
    return False


def correlate_event_to_shipments(
    event: ExternalEvent,
    shipments: list[Shipment],
    evaluation_timestamp: str,
) -> CorrelationResult:
    result = CorrelationResult(event_id=event.id)
    event_tokens = _event_place_tokens(event)
    event_locodes = {locode_of(t) for t in event_tokens}
    event_locodes.discard(None)
    impacting = _event_can_create_exposure(event)
    for shipment in shipments:
        ship_places = _shipment_places(shipment)
        ship_locodes = {locode_of(p) for p in ship_places}
        ship_locodes.discard(None)
        entity_hits = sorted(event_locodes & ship_locodes)
        name_hits = [
            p
            for p in ship_places
            if any(same_place(p, t) for t in event_tokens)
        ]
        carrier_hits = _carrier_hits(event, shipment)
        time_ok = _time_compatible(event, shipment, evaluation_timestamp)
        reasons: list[str] = []
        linkage = "rule_based"
        affected = False
        if not impacting:
            reasons.append("event_type_or_severity_not_operationally_binding")
        elif entity_hits and time_ok:
            affected = True
            linkage = "deterministic_geospatial"
            reasons.append(f"locode_intersection={entity_hits}")
        elif name_hits and time_ok:
            affected = True
            linkage = "deterministic_entity"
            reasons.append(f"place_name_match={name_hits}")
        elif carrier_hits and time_ok:
            affected = True
            linkage = "deterministic_entity"
            reasons.append(f"carrier_match={carrier_hits}")
        else:
            reasons.append("no_place_or_time_match")
        if not time_ok:
            affected = False
            reasons.append("outside_time_window")
        result.hits.append(
            CorrelationHit(
                shipment_number=shipment.shipment_number,
                affected=affected,
                linkage_method=linkage if affected else "rule_based",
                reasons=tuple(reasons),
                matched_locodes=tuple(sorted(x for x in entity_hits if x)),
            )
        )
    return result
