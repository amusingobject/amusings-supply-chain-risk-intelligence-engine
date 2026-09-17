"""Deterministic inventory arithmetic. No LLM involvement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InventoryRisk = Literal["none", "watch", "at_risk", "stockout_expected"]
RULE_VERSION = "inventory-v0.1"


def available_quantity(on_hand: float, allocated: float) -> float:
    return on_hand - allocated


@dataclass(frozen=True)
class StockoutAssessment:
    available: float
    net_after_delay: float
    inventory_risk: InventoryRisk
    method: str
    inputs: dict
    outputs: dict


def stockout_assessment(
    *,
    on_hand: float,
    allocated: float,
    safety_stock: float = 0,
    incoming_quantity: float = 0,
    incoming_delayed: bool = False,
    open_demand: float = 0,
) -> StockoutAssessment:
    available = available_quantity(on_hand, allocated)
    incoming_usable = 0.0 if incoming_delayed else incoming_quantity
    net = available + incoming_usable - open_demand
    if net < 0:
        risk: InventoryRisk = "stockout_expected"
    elif available < safety_stock or (incoming_delayed and open_demand > available):
        risk = "at_risk"
    elif incoming_delayed:
        risk = "watch"
    else:
        risk = "none"
    inputs = {
        "on_hand": on_hand,
        "allocated": allocated,
        "safety_stock": safety_stock,
        "incoming_quantity": incoming_quantity,
        "incoming_delayed": incoming_delayed,
        "open_demand": open_demand,
        "rule_version": RULE_VERSION,
    }
    outputs = {"available": available, "net_after_delay": net, "inventory_risk": risk}
    return StockoutAssessment(
        available=available,
        net_after_delay=net,
        inventory_risk=risk,
        method=RULE_VERSION,
        inputs=inputs,
        outputs=outputs,
    )
