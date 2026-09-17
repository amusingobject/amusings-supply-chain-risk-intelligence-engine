"""Fail-closed business identity handling.

Blank, whitespace-only, null, and duplicate identities never become NEW_SKU,
REMOVED_SKU, or any other normal classification.
"""

from __future__ import annotations

from typing import Any, Literal

from rock_supply_intelligence.engine.profile import ValidatedAliasIndex, resolve_alias
from rock_supply_intelligence.engine.resolution import (
    DuplicateIdentityError,
    ResolutionResult,
    UnresolvedIdentityError,
    is_blank,
    normalize_key,
    result,
)

IdentityKind = Literal["sku", "supplier", "shipment", "purchase_order", "sales_order", "source"]
SkuDelta = Literal["UNCHANGED", "NEW_SKU", "REMOVED_SKU", "AMBIGUOUS", "INVALID"]

IDENTITY_STAGE = "identity_resolution"


def normalize_identity(value: Any) -> str:
    return normalize_key(value, casefold=True)


def identity_status(value: Any, *, kind: IdentityKind = "sku") -> ResolutionResult:
    if value is None:
        return result(
            status="INVALID_PROFILE",
            reason="null_entity_identifier",
            input_identifier="",
            pipeline_stage=IDENTITY_STAGE,
            code="BLANK_IDENTITY",
        )
    if not isinstance(value, str):
        return result(
            status="INVALID_PROFILE",
            reason="unsupported_field_type",
            input_identifier=repr(value),
            pipeline_stage=IDENTITY_STAGE,
            code="BLANK_IDENTITY",
        )
    if is_blank(value):
        return result(
            status="INVALID_PROFILE",
            reason="blank_identity",
            input_identifier=value,
            normalized_identifier="",
            pipeline_stage=IDENTITY_STAGE,
            code="BLANK_IDENTITY",
        )
    key = normalize_identity(value)
    return result(
        status="VALID",
        reason=f"valid_{kind}_identity",
        input_identifier=value,
        normalized_identifier=key,
        candidates=[key],
        value=key,
        pipeline_stage=IDENTITY_STAGE,
    )


def validate_identity_set(
    values: list[Any],
    *,
    kind: IdentityKind = "sku",
) -> ResolutionResult:
    """All identities in a set must be valid and unique after normalization."""
    seen: dict[str, str] = {}
    for item in values:
        item_result = identity_status(item, kind=kind)
        if item_result.blocks_downstream:
            return item_result
        key = item_result.normalized_identifier
        if key in seen:
            return result(
                status="AMBIGUOUS",
                reason="duplicate_identity",
                input_identifier=str(item),
                normalized_identifier=key,
                candidates=[seen[key], str(item)],
                pipeline_stage=IDENTITY_STAGE,
                code="DUPLICATE_IDENTITY",
            )
        seen[key] = str(item)
    return result(
        status="VALID",
        reason="unique_identity_set",
        input_identifier=",".join(seen.values()),
        normalized_identifier="",
        candidates=list(seen.keys()),
        pipeline_stage=IDENTITY_STAGE,
    )


def match_identity_pair(
    left: Any,
    right: Any,
    *,
    kind: IdentityKind = "sku",
    alias_index: ValidatedAliasIndex | None = None,
) -> ResolutionResult:
    left_r = identity_status(left, kind=kind)
    right_r = identity_status(right, kind=kind)
    if left_r.blocks_downstream:
        return left_r
    if right_r.blocks_downstream:
        return right_r
    left_key = left_r.normalized_identifier
    right_key = right_r.normalized_identifier
    if alias_index is not None:
        left_alias = resolve_alias(alias_index, left)
        right_alias = resolve_alias(alias_index, right)
        if left_alias.status == "AMBIGUOUS" or right_alias.status == "AMBIGUOUS":
            return result(
                status="AMBIGUOUS",
                reason="alias_collision",
                input_identifier=f"{left}|{right}",
                normalized_identifier=left_key,
                candidates=list(dict.fromkeys(left_alias.candidates + right_alias.candidates)),
                pipeline_stage=IDENTITY_STAGE,
                code="AMBIGUOUS_ALIAS",
            )
        if left_alias.status == "INVALID_PROFILE" or right_alias.status == "INVALID_PROFILE":
            return left_alias if left_alias.status == "INVALID_PROFILE" else right_alias
        if left_alias.is_valid:
            left_key = normalize_identity(left_alias.value)
        if right_alias.is_valid:
            right_key = normalize_identity(right_alias.value)
    matched = left_key == right_key
    return result(
        status="VALID",
        reason="identity_match" if matched else "identity_distinct",
        input_identifier=f"{left}|{right}",
        normalized_identifier=left_key,
        candidates=[left_key, right_key],
        value="MATCH" if matched else "NO_MATCH",
        pipeline_stage=IDENTITY_STAGE,
        decision="proceed",
    )


def classify_sku_delta(before: list[Any], after: list[Any]) -> tuple[SkuDelta, ResolutionResult]:
    """NEW_SKU / REMOVED_SKU only from two valid unique identity sets."""
    before_r = validate_identity_set(before, kind="sku")
    if before_r.blocks_downstream:
        return "INVALID" if before_r.status == "INVALID_PROFILE" else "AMBIGUOUS", before_r
    after_r = validate_identity_set(after, kind="sku")
    if after_r.blocks_downstream:
        return "INVALID" if after_r.status == "INVALID_PROFILE" else "AMBIGUOUS", after_r
    before_keys = set(before_r.candidates)
    after_keys = set(after_r.candidates)
    added = after_keys - before_keys
    removed = before_keys - after_keys
    if added and not removed:
        delta: SkuDelta = "NEW_SKU"
    elif removed and not added:
        delta = "REMOVED_SKU"
    else:
        delta = "UNCHANGED"
    return delta, result(
        status="VALID",
        reason=delta.lower(),
        input_identifier="",
        candidates=sorted(added | removed),
        value=delta,
        pipeline_stage="sku_delta",
    )


def require_valid_identity(value: Any, *, kind: IdentityKind = "sku") -> str:
    resolved = identity_status(value, kind=kind)
    if resolved.status == "INVALID_PROFILE":
        raise UnresolvedIdentityError(resolved.reason, audit=resolved.as_audit())
    if resolved.blocks_downstream:
        raise UnresolvedIdentityError(resolved.reason, audit=resolved.as_audit())
    assert resolved.value is not None
    return resolved.value


def require_unique_set(values: list[Any], *, kind: IdentityKind = "sku") -> list[str]:
    resolved = validate_identity_set(values, kind=kind)
    if resolved.code == "DUPLICATE_IDENTITY":
        raise DuplicateIdentityError(resolved.reason, audit=resolved.as_audit())
    if resolved.blocks_downstream:
        raise UnresolvedIdentityError(resolved.reason, audit=resolved.as_audit())
    return list(resolved.candidates)
