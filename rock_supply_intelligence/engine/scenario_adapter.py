"""Map scenario synthetic_business_state into canonical records."""

from __future__ import annotations

from rock_supply_intelligence.engine.identity import require_unique_set, require_valid_identity
from rock_supply_intelligence.engine.inventory import available_quantity
from rock_supply_intelligence.engine.locodes import locode_of
from rock_supply_intelligence.schemas.canonical import (
    InventoryPosition,
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrder,
    SalesOrderLine,
    Shipment,
    ShipmentLeg,
    SKU,
    Supplier,
)
from rock_supply_intelligence.schemas.common import SCHEMA_VERSION, TENANT_POC


def _ts(evaluation_timestamp: str) -> str:
    return evaluation_timestamp


def _validate_business_identities(state: dict) -> None:
    """Blank or duplicate identities stop adaptation. No NEW_SKU inference."""
    supplier_ids = [raw.get("supplier_id") for raw in state.get("suppliers") or []]
    po_numbers = [raw.get("po_number") for raw in state.get("purchase_orders") or []]
    shipment_numbers = [raw.get("shipment_number") for raw in state.get("shipments") or []]
    sales_numbers = [raw.get("sales_order_number") for raw in state.get("sales_orders") or []]
    sku_ids: list = []
    for raw in state.get("purchase_orders") or []:
        for line in raw.get("lines") or []:
            sku_ids.append(line.get("sku_id"))
    for raw in state.get("inventory_positions") or []:
        sku_ids.append(raw.get("sku_id"))
    for raw in state.get("sales_orders") or []:
        for line in raw.get("lines") or []:
            sku_ids.append(line.get("sku_id"))
    if supplier_ids:
        require_unique_set(supplier_ids, kind="supplier")
    if po_numbers:
        require_unique_set(po_numbers, kind="purchase_order")
    if shipment_numbers:
        require_unique_set(shipment_numbers, kind="shipment")
    if sales_numbers:
        require_unique_set(sales_numbers, kind="sales_order")
    for sku in sku_ids:
        require_valid_identity(sku, kind="sku")
    inv_keys = []
    for raw in state.get("inventory_positions") or []:
        sku = require_valid_identity(raw.get("sku_id"), kind="sku")
        loc = require_valid_identity(raw.get("location_id"), kind="source")
        inv_keys.append(f"{sku}|{loc}")
    if inv_keys:
        require_unique_set(inv_keys, kind="sku")


def adapt_business_state(state: dict, evaluation_timestamp: str) -> dict:
    ts = _ts(evaluation_timestamp)
    _validate_business_identities(state)
    suppliers = []
    for raw in state.get("suppliers") or []:
        suppliers.append(
            Supplier(
                id=raw["supplier_id"],
                status="active",
                created_at=ts,
                updated_at=ts,
                supplier_code=raw.get("supplier_code") or raw["supplier_id"],
                legal_name=raw.get("legal_name") or raw.get("supplier_code") or raw["supplier_id"],
                supplier_status=raw.get("status") or "active",
                facilities=[raw["facility_location"]] if raw.get("facility_location") else [],
            )
        )
    pos = []
    for raw in state.get("purchase_orders") or []:
        pos.append(
            PurchaseOrder(
                id=raw["po_number"],
                status="active",
                created_at=ts,
                updated_at=ts,
                po_number=raw["po_number"],
                supplier_id=raw["supplier_id"],
                order_date=raw.get("order_date") or ts[:10],
                po_status=raw.get("status") or "open",
                currency=raw.get("currency") or "USD",
                lines=[
                    PurchaseOrderLine(
                        sku_id=line["sku_id"],
                        quantity_ordered=line["quantity_ordered"],
                        promised_date=line.get("promised_date"),
                    )
                    for line in raw.get("lines") or []
                ],
            )
        )
    shipments = []
    for raw in state.get("shipments") or []:
        origin = raw["origin"]
        dest = raw["destination"]
        via = raw.get("via") or None
        legs = []
        seq = 1
        for i, leg in enumerate(raw.get("legs") or [], start=1):
            legs.append(
                ShipmentLeg(
                    leg_sequence=leg.get("leg_sequence") or i,
                    mode=leg.get("mode") or raw.get("mode") or "ocean",
                    origin=leg["origin"],
                    destination=leg["destination"],
                    origin_locode=locode_of(leg["origin"]),
                    destination_locode=locode_of(leg["destination"]),
                    status=leg.get("status") or "planned",
                )
            )
            seq = max(seq, legs[-1].leg_sequence + 1)
        if via:
            legs.append(
                ShipmentLeg(
                    leg_sequence=seq,
                    mode=raw.get("mode") or "ocean",
                    origin=origin,
                    destination=via,
                    origin_locode=locode_of(origin),
                    destination_locode=locode_of(via),
                    status="planned",
                )
            )
        shipments.append(
            Shipment(
                id=raw["shipment_number"],
                status="active",
                created_at=ts,
                updated_at=ts,
                shipment_number=raw["shipment_number"],
                shipment_status=raw.get("status") or "booked",
                mode=raw.get("mode") or "ocean",
                origin=origin,
                destination=dest,
                origin_locode=locode_of(origin),
                destination_locode=locode_of(dest),
                po_refs=list(raw.get("po_refs") or []),
                carrier_id=raw.get("carrier_id"),
                legs=legs,
            )
        )
    inventory = []
    for raw in state.get("inventory_positions") or []:
        on_hand = float(raw["on_hand"])
        allocated = float(raw["allocated"])
        available = float(raw.get("available", available_quantity(on_hand, allocated)))
        inventory.append(
            InventoryPosition(
                id=f"INV-{raw['sku_id']}-{raw['location_id']}",
                status="active",
                created_at=ts,
                updated_at=ts,
                snapshot_at=raw.get("snapshot_at") or ts,
                sku_id=raw["sku_id"],
                location_id=raw["location_id"],
                on_hand=on_hand,
                allocated=allocated,
                available=available,
                on_order=raw.get("on_order"),
                in_transit=raw.get("in_transit"),
                safety_stock=raw.get("safety_stock"),
                unit=raw.get("unit") or "EA",
            )
        )
    sales_orders = []
    for raw in state.get("sales_orders") or []:
        sales_orders.append(
            SalesOrder(
                id=raw["sales_order_number"],
                status="active",
                created_at=ts,
                updated_at=ts,
                sales_order_number=raw["sales_order_number"],
                order_status=raw.get("status") or "open",
                lines=[
                    SalesOrderLine(
                        sku_id=line["sku_id"],
                        ordered=line["ordered"],
                        allocated=line.get("allocated") or 0,
                        shipped=line.get("shipped") or 0,
                    )
                    for line in raw.get("lines") or []
                ],
            )
        )
    skus = []
    sku_ids = {line.sku_id for po in pos for line in po.lines}
    sku_ids.update(posi.sku_id for posi in inventory)
    for sku_id in sorted(sku_ids):
        skus.append(
            SKU(
                id=sku_id,
                status="active",
                created_at=ts,
                updated_at=ts,
                sku_code=sku_id,
                description=sku_id,
                base_unit="EA",
                active=True,
            )
        )
    return {
        "suppliers": suppliers,
        "purchase_orders": pos,
        "shipments": shipments,
        "inventory": inventory,
        "sales_orders": sales_orders,
        "skus": skus,
    }
