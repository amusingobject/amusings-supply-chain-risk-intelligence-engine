"""Write JSON Schema files from the Pydantic canonical models."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rock_supply_intelligence.schemas.canonical import CANONICAL_MODELS
from rock_supply_intelligence.schemas.source_quality import SourceQuality, SourceQualityAssessment

OUT = ROOT / "rock_supply_intelligence_benchmark" / "schemas"


def emit(out_dir: Path | None = None) -> list[Path]:
    dest = out_dir or OUT
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in CANONICAL_MODELS.items():
        schema = model.model_json_schema()
        schema["title"] = f"Canonical {name} v0.1"
        path = dest / f"{SLUGS[name]}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n")
        written.append(path)
    extra = {
        "source-quality": SourceQuality,
        "source-quality-assessment": SourceQualityAssessment,
    }
    for slug, model in extra.items():
        schema = model.model_json_schema()
        schema["title"] = f"Canonical {model.__name__} v0.1"
        path = dest / f"{slug}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n")
        written.append(path)
    return written


SLUGS = {
    "Evidence": "evidence-record",
    "ExternalEvent": "external-event",
    "PurchaseOrder": "purchase-order",
    "Shipment": "shipment",
    "ShipmentLeg": "shipment-leg",
    "Container": "container",
    "CarrierEvent": "carrier-event",
    "InventoryPosition": "inventory-position",
    "SalesOrder": "sales-order",
    "SKU": "sku",
    "Supplier": "supplier",
    "Exposure": "exposure",
    "Recommendation": "recommendation",
}


if __name__ == "__main__":
    for path in emit():
        print(path)
