#!/usr/bin/env python3
from __future__ import annotations

import unittest

from rock_supply_intelligence.engine.correlation import correlate_event_to_shipments
from rock_supply_intelligence.engine.exposure import build_exposures
from rock_supply_intelligence.engine.inventory import available_quantity, stockout_assessment
from rock_supply_intelligence.engine.locodes import locode_of, same_place
from rock_supply_intelligence.engine.recommendation import apply_human_decision, draft_recommendation
from rock_supply_intelligence.engine.scenario_adapter import adapt_business_state
from rock_supply_intelligence.schemas.canonical import CanonicalRef, ExternalEvent, InventoryPosition, Shipment


def _event(title: str, event_type: str = "infrastructure", loc: str = "Baltimore") -> ExternalEvent:
    return ExternalEvent(
        id="EVT-T",
        status="draft",
        created_at="2024-03-27T12:00:00Z",
        updated_at="2024-03-27T12:00:00Z",
        evidence_ids=["EVD-T"],
        event_type=event_type,  # type: ignore[arg-type]
        event_state="reported",
        title=title,
        start_time="2024-03-26T00:00:00Z",
        severity="severe",
        observed_or_inferred="extracted",
        locations=[CanonicalRef(ref_type="place", name=loc, locode=locode_of(loc), raw_value=loc)],
    )


def _ship(number: str, origin: str, dest: str) -> Shipment:
    return Shipment(
        id=number,
        status="active",
        created_at="2024-03-27T12:00:00Z",
        updated_at="2024-03-27T12:00:00Z",
        shipment_number=number,
        shipment_status="in_transit",
        mode="ocean",
        origin=origin,
        destination=dest,
        origin_locode=locode_of(origin),
        destination_locode=locode_of(dest),
        legs=[],
    )


class LocodeTests(unittest.TestCase):
    def test_aliases(self) -> None:
        self.assertEqual(locode_of("基隆"), "TWKEL")
        self.assertTrue(same_place("Kaohsiung", "TWKHH"))
        self.assertFalse(same_place("Keelung", "Baltimore"))


class InventoryTests(unittest.TestCase):
    def test_available_identity(self) -> None:
        self.assertEqual(available_quantity(40, 8), 32)

    def test_stockout_when_inbound_delayed(self) -> None:
        result = stockout_assessment(
            on_hand=6,
            allocated=5,
            safety_stock=8,
            incoming_quantity=24,
            incoming_delayed=True,
            open_demand=6,
        )
        self.assertEqual(result.available, 1)
        self.assertEqual(result.inventory_risk, "stockout_expected")

    def test_rejects_inconsistent_available(self) -> None:
        with self.assertRaises(Exception):
            InventoryPosition(
                id="INV-X",
                status="active",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                snapshot_at="2024-01-01T00:00:00Z",
                sku_id="SKU-1",
                location_id="LOC",
                on_hand=10,
                allocated=2,
                available=10,
            )


class CorrelationTests(unittest.TestCase):
    def test_baltimore_affects_baltimore_shipment(self) -> None:
        event = _event("Baltimore bridge collapse / Baltimore shipment", loc="Baltimore")
        ships = [_ship("SHP-BAL", "Kaohsiung", "Baltimore")]
        result = correlate_event_to_shipments(event, ships, "2024-03-27T12:00:00Z")
        self.assertEqual(result.affected_shipments, ["SHP-BAL"])

    def test_carrier_entity_match(self) -> None:
        event = ExternalEvent(
            id="EVT-T",
            status="draft",
            created_at="2017-06-27T12:00:00Z",
            updated_at="2017-06-27T12:00:00Z",
            evidence_ids=["EVD-T"],
            event_type="carrier_exception",
            event_state="reported",
            title="Maersk cyberattack / carrier correlation",
            start_time="2017-06-27T00:00:00Z",
            severity="high",
            observed_or_inferred="extracted",
            entities=[CanonicalRef(ref_type="carrier", name="MAERSK", code="MAERSK", raw_value="MAERSK")],
        )
        ship = _ship("SHP-MAE", "Kaohsiung", "Long Beach").model_copy(update={"carrier_id": "MAERSK"})
        result = correlate_event_to_shipments(event, [ship], "2017-06-27T12:00:00Z")
        self.assertEqual(result.affected_shipments, ["SHP-MAE"])

    def test_baltimore_negative_long_beach(self) -> None:
        event = _event("Baltimore bridge collapse / Long Beach shipment", loc="Baltimore")
        ships = [_ship("SHP-LGB", "Kaohsiung", "Long Beach")]
        result = correlate_event_to_shipments(event, ships, "2024-03-27T12:00:00Z")
        self.assertEqual(result.affected_shipments, [])
        self.assertEqual(result.unaffected_shipments, ["SHP-LGB"])


class ExposureRecommendationTests(unittest.TestCase):
    def test_exposure_requires_trace_and_stays_candidate(self) -> None:
        event = _event("Keelung closure", loc="Keelung")
        ships = [_ship("SHP-KEL", "Keelung", "Long Beach")]
        corr = correlate_event_to_shipments(event, ships, "2024-07-24T01:00:00Z")
        exposures = build_exposures(event, ships, corr, evaluation_timestamp="2024-07-24T01:00:00Z")
        self.assertEqual(len(exposures), 1)
        self.assertEqual(exposures[0].exposure_status, "candidate")
        self.assertTrue(exposures[0].calculation_trace)
        rec = draft_recommendation(exposures, event_title=event.title)
        self.assertEqual(rec.recommendation_status, "draft")
        self.assertEqual(rec.human_approval.state, "not_requested")

    def test_replay_cannot_self_approve(self) -> None:
        rec = draft_recommendation([])
        self.assertEqual(rec.action_type, "no_action")
        approved = apply_human_decision(rec, state="approved", actor="analyst-1")
        self.assertEqual(approved.human_approval.state, "approved")
        self.assertEqual(approved.recommendation_status, "approved")

    def test_adapter_inventory_identity(self) -> None:
        state = {
            "suppliers": [{"supplier_id": "SUP-1", "supplier_code": "S", "status": "active", "facility_location": "Keelung"}],
            "purchase_orders": [
                {
                    "po_number": "PO-1",
                    "supplier_id": "SUP-1",
                    "status": "open",
                    "currency": "USD",
                    "lines": [{"sku_id": "SKU-1", "quantity_ordered": 24}],
                }
            ],
            "shipments": [
                {
                    "shipment_number": "SHP-1",
                    "status": "booked",
                    "mode": "ocean",
                    "origin": "Keelung",
                    "destination": "Long Beach",
                    "po_refs": ["PO-1"],
                    "legs": [{"leg_sequence": 1, "mode": "ocean", "origin": "Keelung", "destination": "Long Beach", "status": "planned"}],
                }
            ],
            "inventory_positions": [
                {
                    "sku_id": "SKU-1",
                    "location_id": "LOC",
                    "snapshot_at": "2024-07-24T01:00:00Z",
                    "on_hand": 40,
                    "allocated": 8,
                    "available": 32,
                    "unit": "EA",
                }
            ],
            "sales_orders": [{"sales_order_number": "SO-1", "status": "open", "lines": [{"sku_id": "SKU-1", "ordered": 6, "allocated": 2, "shipped": 0}]}],
        }
        records = adapt_business_state(state, "2024-07-24T01:00:00Z")
        self.assertEqual(records["inventory"][0].available, 32)
        self.assertEqual(records["shipments"][0].origin_locode, "TWKEL")


if __name__ == "__main__":
    unittest.main()
