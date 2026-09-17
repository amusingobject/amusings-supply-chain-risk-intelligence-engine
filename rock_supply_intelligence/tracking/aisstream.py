"""Pure AIS Stream protocol adapter. Network transport is deliberately absent."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rock_supply_intelligence.tracking.models import (
    BoundingBox,
    NormalizationResult,
    TrackingProvenance,
    VesselPosition,
)

AISSTREAM_ENDPOINT = "wss://stream.aisstream.io/v0/stream"


class AISStreamConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    api_key_env: str = "AISSTREAM_API_KEY"
    bounding_boxes: list[BoundingBox] = Field(min_length=1)
    mmsi_filter: list[str] = Field(default_factory=list, max_length=200)
    message_types: list[Literal["PositionReport"]] = Field(default_factory=lambda: ["PositionReport"], min_length=1)

    @field_validator("mmsi_filter")
    @classmethod
    def validate_mmsi_filter(cls, values: list[str]) -> list[str]:
        normalized = [str(value).strip() for value in values]
        if any(len(value) != 9 or not value.isdigit() or value == "000000000" for value in normalized):
            raise ValueError("mmsi_filter entries must be non-zero nine-digit identifiers")
        if len(normalized) != len(set(normalized)):
            raise ValueError("mmsi_filter entries must be unique")
        return normalized


def subscription_payload(config: AISStreamConfig, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Build a live subscription only after an explicit enable and secret check."""
    if not config.enabled:
        raise RuntimeError("live AIS Stream integration is disabled")
    env = environ if environ is not None else os.environ
    api_key = env.get(config.api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"missing AIS Stream credential in {config.api_key_env}")
    return {
        "APIKey": api_key,
        "BoundingBoxes": [
            [[box.south, box.west], [box.north, box.east]] for box in config.bounding_boxes
        ],
        "FiltersShipMMSI": list(config.mmsi_filter),
        "FilterMessageTypes": list(config.message_types),
    }


def _raw_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _utc(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("tracking timestamps require a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_message(
    payload: bytes | str | dict[str, Any],
    *,
    received_at: str,
    synthetic: bool = False,
) -> NormalizationResult:
    """Normalize a position report. Malformed/conflicting data is quarantined."""
    raw = _raw_bytes(payload)
    digest = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return NormalizationResult(disposition="quarantined", reason="invalid_json", raw_sha256=digest)
    if not isinstance(data, dict):
        return NormalizationResult(disposition="quarantined", reason="payload_not_object", raw_sha256=digest)
    if data.get("MessageType") != "PositionReport":
        return NormalizationResult(disposition="ignored", reason="unsupported_message_type", raw_sha256=digest)
    try:
        metadata = data["MetaData"]
        report = data["Message"]["PositionReport"]
        if not isinstance(metadata, dict) or not isinstance(report, dict):
            raise TypeError("position metadata and report must be objects")
        if not isinstance(report.get("Valid"), bool):
            raise TypeError("PositionReport.Valid must be a boolean")
        meta_mmsi = str(metadata.get("MMSI", "")).strip()
        report_mmsi = str(report.get("UserID", "")).strip()
        if meta_mmsi and report_mmsi and meta_mmsi != report_mmsi:
            return NormalizationResult(disposition="quarantined", reason="mmsi_conflict", raw_sha256=digest)
        mmsi = meta_mmsi or report_mmsi
        provider_time = metadata.get("time_utc") or metadata.get("TimeUTC")
        observed_at = _utc(str(provider_time)) if provider_time else _utc(received_at)
        heading = report.get("TrueHeading")
        if heading in {-1, 511}:
            heading = None
        provenance = TrackingProvenance(
            provider="aisstream",
            source_locator=AISSTREAM_ENDPOINT,
            received_at=_utc(received_at),
            raw_sha256=digest,
            raw_ref=f"tracking://aisstream/{digest}",
            synthetic=synthetic,
        )
        observation = VesselPosition(
            observation_id=f"AIS-{digest[:24]}",
            mmsi=mmsi,
            vessel_name=(str(metadata.get("ShipName") or "").strip() or None),
            observed_at=observed_at,
            timestamp_basis="provider" if provider_time else "received_time_fallback",
            latitude=metadata["Latitude"],
            longitude=metadata["Longitude"],
            speed_over_ground_knots=report.get("Sog"),
            course_over_ground_degrees=report.get("Cog"),
            true_heading_degrees=heading,
            navigational_status=report.get("NavigationalStatus"),
            source_valid=bool(report.get("Valid", False)),
            provenance=provenance,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return NormalizationResult(
            disposition="quarantined",
            reason=f"invalid_position:{type(exc).__name__}",
            raw_sha256=digest,
        )
    return NormalizationResult(disposition="accepted", observation=observation, reason="position_report", raw_sha256=digest)
