"""Build Exposure records from deterministic correlation and inventory math."""

from __future__ import annotations

from datetime import datetime, timezone

from rock_supply_intelligence.engine.correlation import CorrelationResult
from rock_supply_intelligence.engine.inventory import stockout_assessment
from rock_supply_intelligence.schemas.canonical import (
    CalculationTraceItem,
    DelayRange,
    Exposure,
    ExternalEvent,
    ImpactWindow,
    InventoryPosition,
    SalesOrder,
    Shipment,
)
from rock_supply_intelligence.schemas.common import SCHEMA_VERSION, TENANT_POC

RULE_VERSION = "exposure-v0.1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _delay_range(event: ExternalEvent) -> DelayRange | None:
    if event.severity in {"high", "severe"}:
        return DelayRange(min_hours=24, max_hours=168, method=RULE_VERSION)
    if event.severity == "moderate":
        return DelayRange(min_hours=12, max_hours=96, method=RULE_VERSION)
    if event.severity == "low":
        return DelayRange(min_hours=0, max_hours=48, method=RULE_VERSION)
    return None


def build_exposures(
    event: ExternalEvent,
    shipments: list[Shipment],
    correlation: CorrelationResult,
    inventory: list[InventoryPosition] | None = None,
    sales_orders: list[SalesOrder] | None = None,
    evaluation_timestamp: str | None = None,
) -> list[Exposure]:
    inventory = inventory or []
    sales_orders = sales_orders or []
    ts = _now()
    as_of = evaluation_timestamp or event.start_time or ts
    out: list[Exposure] = []
    shipment_by_number = {s.shipment_number: s for s in shipments}
    for hit in correlation.hits:
        shipment = shipment_by_number.get(hit.shipment_number)
        if shipment is None:
            continue
        if not hit.affected:
            continue
        sku_ids = _skus_for_shipment(shipment, inventory, sales_orders)
        so_ids = [so.sales_order_number for so in sales_orders if _so_uses_skus(so, sku_ids)]
        delay = _delay_range(event)
        inv_risk = None
        traces = [
            CalculationTraceItem(
                rule_id="correlation",
                rule_version=RULE_VERSION,
                inputs={"event_id": event.id, "shipment": hit.shipment_number, "reasons": list(hit.reasons)},
                outputs={"affected": True, "linkage_method": hit.linkage_method},
            )
        ]
        for pos in inventory:
            if pos.sku_id not in sku_ids:
                continue
            delayed_qty = pos.in_transit or 0
            demand = sum(
                line.ordered - line.shipped
                for so in sales_orders
                for line in so.lines
                if line.sku_id == pos.sku_id
            )
            assessment = stockout_assessment(
                on_hand=pos.on_hand,
                allocated=pos.allocated,
                safety_stock=pos.safety_stock or 0,
                incoming_quantity=delayed_qty,
                incoming_delayed=True,
                open_demand=demand,
            )
            traces.append(
                CalculationTraceItem(
                    rule_id="inventory_stockout",
                    rule_version=assessment.method,
                    inputs=assessment.inputs,
                    outputs=assessment.outputs,
                )
            )
            inv_risk = assessment.inventory_risk
        exposure_type = "inventory_stockout" if inv_risk == "stockout_expected" else "delay"
        out.append(
            Exposure(
                id=f"EXP-{event.id}-{shipment.shipment_number}",
                schema_version=SCHEMA_VERSION,
                tenant_id=TENANT_POC,
                status="draft",
                created_at=ts,
                updated_at=ts,
                evidence_ids=list(event.evidence_ids),
                event_id=event.id,
                exposure_type=exposure_type,
                exposure_status="candidate",
                subject_type="shipment",
                subject_id=shipment.shipment_number,
                linkage_method=hit.linkage_method,  # type: ignore[arg-type]
                impact_window=ImpactWindow(start=as_of, end=event.end_time, method=RULE_VERSION),
                expected_delay=delay,
                affected_sku_ids=sku_ids,
                sales_order_ids=so_ids,
                inventory_risk=inv_risk,
                confidence=event.confidence,
                calculation_trace=traces,
            )
        )
    return out


def _skus_for_shipment(
    shipment: Shipment,
    inventory: list[InventoryPosition],
    sales_orders: list[SalesOrder],
) -> list[str]:
    ids: set[str] = set()
    for pos in inventory:
        ids.add(pos.sku_id)
    for so in sales_orders:
        for line in so.lines:
            ids.add(line.sku_id)
    return sorted(ids)


def _so_uses_skus(order: SalesOrder, sku_ids: list[str]) -> bool:
    return any(line.sku_id in sku_ids for line in order.lines)
