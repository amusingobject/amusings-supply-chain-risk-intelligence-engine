"""Append-only local provenance store for vessel observations."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
from pathlib import Path

from rock_supply_intelligence.tracking.aisstream import _raw_bytes
from rock_supply_intelligence.tracking.models import NormalizationResult


class TrackingObservationStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self.records = self.root / "observations.jsonl"
        self.lock = self.root / ".tracking-store.lock"

    def _recorded(self, observation_id: str) -> bool:
        if not self.records.is_file():
            return False
        for line in self.records.read_text(encoding="utf-8").splitlines():
            if line and json.loads(line).get("observation_id") == observation_id:
                return True
        return False

    def append(self, result: NormalizationResult, raw_payload: bytes | str | dict) -> bool:
        if result.disposition != "accepted" or result.observation is None:
            raise ValueError("only accepted observations can be stored")
        raw = _raw_bytes(raw_payload)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != result.raw_sha256 or digest != result.observation.provenance.raw_sha256:
            raise ValueError("raw payload hash does not match observation provenance")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        with self.lock.open("a+b") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            raw_path = self.raw_dir / f"{digest}.json"
            if raw_path.exists():
                if raw_path.read_bytes() != raw:
                    raise ValueError("existing raw payload differs for the same digest")
            else:
                raw_path.write_bytes(raw)
            if self._recorded(result.observation.observation_id):
                return False
            with self.records.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result.observation.model_dump(mode="json"), sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return True
