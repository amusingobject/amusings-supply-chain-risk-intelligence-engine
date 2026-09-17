"""Replay provider for deterministic ship-tracking development and tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from rock_supply_intelligence.tracking.aisstream import normalize_message
from rock_supply_intelligence.tracking.models import NormalizationResult


class ReplayTrackingProvider:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def results(self) -> Iterator[NormalizationResult]:
        for line_number, line in enumerate(self.path.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            try:
                envelope = json.loads(line)
                received_at = envelope["received_at"]
                payload = envelope["payload"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(f"invalid replay envelope at line {line_number}") from exc
            yield normalize_message(payload, received_at=received_at, synthetic=True)
