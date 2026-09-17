"""Provider contract shared by replay and future live tracking transports."""

from __future__ import annotations

from typing import Iterable, Protocol

from rock_supply_intelligence.tracking.models import NormalizationResult


class VesselTrackingProvider(Protocol):
    def results(self) -> Iterable[NormalizationResult]: ...
