"""Fail-closed financial/business header mapping.

A normalized header that matches more than one canonical field is AMBIGUOUS_HEADER.
No automatic financial mapping is produced in that case.
"""

from __future__ import annotations

from typing import Any

from rock_supply_intelligence.engine.profile import (
    ValidatedAliasIndex,
    resolve_alias,
    try_validate_alias_profile,
    validate_alias_profile,
)
from rock_supply_intelligence.engine.resolution import AmbiguousHeaderError, ResolutionResult, result

HEADER_STAGE = "financial_header_mapping"

DEFAULT_FINANCIAL_PROFILE: dict[str, Any] = {
    "profile_id": "financial-headers-v0.1",
    "version": "financial-headers-v0.1",
    "casefold": True,
    "fields": [
        {
            "canonical": "quantity_available",
            "aliases": ["qty_avail", "qty_available", "available_qty", "quantity available"],
        },
        {
            "canonical": "quantity_committed",
            "aliases": ["qty_committed", "committed_qty", "quantity committed"],
        },
        {
            "canonical": "quantity_ordered",
            "aliases": ["qty_ordered", "ordered_qty", "quantity ordered"],
        },
        {"canonical": "unit_cost", "aliases": ["unitcost", "unit_price_cost"]},
        {"canonical": "total_cost", "aliases": ["extended_cost", "line_cost"]},
        {"canonical": "price", "aliases": ["sell_price", "unit_sell_price"]},
        {"canonical": "inventory_on_hand", "aliases": ["on_hand", "inventory_onhand"]},
        {"canonical": "revenue", "aliases": ["sales_revenue"]},
        {"canonical": "margin", "aliases": ["gross_margin"]},
        {"canonical": "order_value", "aliases": ["po_value", "order_amount"]},
    ],
}


def load_financial_profile(raw: dict[str, Any] | None = None) -> ValidatedAliasIndex:
    return validate_alias_profile(raw or DEFAULT_FINANCIAL_PROFILE)


def map_header(header: Any, index: ValidatedAliasIndex | None = None) -> ResolutionResult:
    idx = index or load_financial_profile()
    resolved = resolve_alias(idx, header)
    if resolved.status == "UNRESOLVED" and resolved.code == "BLANK_IDENTITY":
        return result(
            status="INVALID_PROFILE",
            reason="blank_header",
            input_identifier="" if header is None else str(header),
            pipeline_stage=HEADER_STAGE,
            profile_version=idx.version,
            code="MALFORMED_ALIAS",
        )
    if resolved.status == "UNRESOLVED":
        return result(
            status="UNRESOLVED",
            reason="unresolved_header",
            input_identifier="" if header is None else str(header),
            normalized_identifier=resolved.normalized_identifier,
            pipeline_stage=HEADER_STAGE,
            profile_version=idx.version,
            code="UNRESOLVED",
        )
    if resolved.status != "VALID":
        return resolved.model_copy(update={"pipeline_stage": HEADER_STAGE})
    return resolved.model_copy(update={"pipeline_stage": HEADER_STAGE})


def map_headers(
    headers: list[Any],
    index: ValidatedAliasIndex | None = None,
) -> tuple[dict[str, str], list[ResolutionResult]]:
    """Return mapping only for uniquely resolved headers. Ambiguity yields no mapping."""
    idx = index or load_financial_profile()
    mapping: dict[str, str] = {}
    audits: list[ResolutionResult] = []
    for header in headers:
        resolved = map_header(header, idx)
        audits.append(resolved)
        if resolved.status in {"AMBIGUOUS", "INVALID_PROFILE", "REVIEW_REQUIRED"}:
            raise AmbiguousHeaderError(
                "normalized header matches multiple canonical fields or profile is invalid",
                audit=resolved.as_audit(),
            )
        if not resolved.is_valid or resolved.value is None:
            continue
        mapping[str(header)] = resolved.value
    return mapping, audits


def map_headers_from_profile(
    headers: list[Any],
    profile_raw: dict[str, Any],
) -> tuple[dict[str, str], list[ResolutionResult]]:
    """Fail closed: invalid or colliding profile produces no financial mapping."""
    index, profile_result = try_validate_alias_profile(profile_raw)
    if index is None or profile_result.blocks_downstream:
        return {}, [profile_result]
    try:
        return map_headers(headers, index)
    except AmbiguousHeaderError as exc:
        audit = exc.audit or {}
        return {}, [
            result(
                status="AMBIGUOUS",
                reason=str(exc),
                input_identifier=str(audit.get("input_identifier") or ""),
                candidates=list(audit.get("candidates") or []),
                pipeline_stage=HEADER_STAGE,
                code="AMBIGUOUS_HEADER",
            )
        ]
