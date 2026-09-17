# Human Review Packet — Collection Wave 3

Status: review aid only. This document does not certify labels or modify the
benchmark release state.

## Scope

Review the newly collected fixtures in these three groups:

| Group | IDs | Intended review question |
| --- | --- | --- |
| Taiwan weather | `ATOM-CWA-TDB-2024*.json` | Does the retained Traditional-Chinese CWA page identify a real typhoon record, and is `monitor` appropriate rather than a stronger routing claim? |
| Labor/infrastructure queue | `ATOM-FR-MARITIME-LABOR-PAGE-*.json` | Does the official result page contain the stated query results, and should any individual item be promoted, suppressed, or left as a review cue? |
| Security queue | `ATOM-FR-SANCTIONS-SECURITY-PAGE-*.json` | Does the official result page contain the stated query results, and is a security-related review cue justified without asserting a legal conclusion? |
| Taiwan earthquake windows | `ATOM-USGS-HUALIEN-FOLLOWUP-WINDOW-*.json` and `ATOM-USGS-TAITUNG-WINDOW-*.json` | Does the bounded official payload contain Taiwan-region events, and does it support a material-relevance review cue without asserting a confirmed disruption? |
| Negative controls | `ATOM-USGS-NOTO-WINDOW-*.json` and `ATOM-NOAA-BERYL-*.json` | Is the source genuinely outside the Taiwan-to-U.S.-Pacific routing scope and therefore suitable as an irrelevant control? |

## Per-fixture checklist

For each manifest, open its `source.raw_ref` and check:

- [ ] The hash matches the retained raw file (the validator already checks this).
- [ ] The publisher, locator, language, and retrieval metadata describe the actual source.
- [ ] The source supports the proposed class and event category; otherwise record the corrected value or reject it.
- [ ] No claim of a port closure, shipment impact, sanction match, or required action has been inferred beyond the source.

## Review decisions

Use one of these outcomes for each fixture:

| Outcome | Meaning |
| --- | --- |
| Keep provisional | Source is sound but needs later domain adjudication. |
| Relabel | Source is sound; proposed class/category needs correction. |
| Reject | Empty, off-topic, misleading, duplicate, or unsuitable for this benchmark. |
| Escalate | A legal, geopolitical, translation, or routing-domain decision is needed. |

## Important constraints

- Do not mark the global benchmark label review complete tonight. The corpus is still below the 420-fixture quota.
- Keep source records provisional until any relabel/reject decision is captured in the canonical manifest and reviewed again.
- A sanctions or security result is a review cue only, never a legal determination.
- A weather record is not proof of a port closure or shipment delay without specific supporting evidence.

## Quota-rebalancing decision needed before more collection

The current corpus has 288 fixtures. It already exceeds the planned minimum for
`monitor` (102 versus 50) and `ambiguous_conflicting` (52 versus 50). Because
the intended class targets add up to the 420-fixture corpus, continuing to add
new records without reviewing this queue would make a 420-fixture balanced
release impossible.

Please review the 54 excess records before authorizing another collection wave:

- `monitor`: Federal Register review queues, CWA typhoon records, and selected
  NOAA advisories.
- `ambiguous_conflicting`: synthetic ambiguity fixtures above the target.

For each, choose **Keep as monitor/ambiguous**, **Relabel if the retained source
supports another class**, or **Reject from the release corpus**. Do not relabel
just to meet a quota; the source must support the result. Once this review is
complete, the remaining collection plan can be sized accurately without
overshooting the fixed 420-fixture target.

### Proposed review decision set

This is a proposal for your approval, not an applied change:

1. **Reject the 40 Federal Register search-result pages** (`ATOM-FR-MARITIME-*
   and `ATOM-FR-SANCTIONS-*`) from the release corpus. They are useful
   collection leads, but search pages are not individual event records.
2. **Keep the two oracle ambiguity fixtures** (`ATOM-SYN-AMBIG-01` and
   `ATOM-SYN-AMBIG-02`) and the two synthetic conflict fixtures; **reject
   `ATOM-SYN-AMB-EN-045` and `ATOM-SYN-AMB-EN-048`** as redundant generated
   ambiguity records. This brings ambiguity coverage from 52 to 50.
3. From the 30 `ATOM-CWA-TDB-*` monitor fixtures, **select 18 records with a
   documented Taiwan impact or a meaningful uncertainty case and reject the
   remaining 12**. Do not use a storm name alone as evidence of a supply-chain
   impact.

If you approve all three decisions after reviewing the raw sources, the release
corpus returns to 234 fixtures with exactly 50 monitor and 50 ambiguity
fixtures. The remaining 186 collection slots then line up exactly with the
shortfalls: 106 materially relevant, 78 irrelevant, and 2 prompt-injection
fixtures. Those future additions must also meet the language and event-category
requirements.

### Approved outcome — 2026-09-08

The proposed cleanup was approved and applied. The active CWA subset is:

`202301`, `202302`, `202303`, `202304`, `202306`, `202307`, `202308`,
`202309`, `202310`, `202402`, `202404`, `202405`, `202406`, `202407`,
`202408`, `202409`, `202412`, and `202414`.

The 12 non-selected CWA manifests, 40 Federal Register search pages, and two
redundant generated ambiguity fixtures were moved to `rejected/atomic/`. Their
raw sources were retained, and their IDs are reserved so future collector runs
cannot re-add them.

### Remaining category-balance decision

The approved cleanup leaves 89 weather fixtures against the fixed 80-fixture
target. To preserve a 420-fixture release corpus while meeting the remaining
port, labor, geopolitical, regulatory, and irrelevant-world quotas, review and
approve archival of these nine redundant Beryl negative controls:

`ATOM-NOAA-BERYL-06`, `ATOM-NOAA-BERYL-08`, `ATOM-NOAA-BERYL-10`,
`ATOM-NOAA-BERYL-12`, `ATOM-NOAA-BERYL-14`, `ATOM-NOAA-BERYL-16`,
`ATOM-NOAA-BERYL-18`, `ATOM-NOAA-BERYL-22`, and `ATOM-NOAA-BERYL-24`.

They are dated official NOAA records, but are redundant Taiwan-route negative
controls. Archiving them would bring the active corpus to 225 and leave exactly
195 category-balanced collection slots.

### Approved weather outcome — 2026-09-08

The nine listed Beryl weather negative controls were approved for archival and
moved to `rejected/atomic/`. An initial archive selection was restored because
it did not reduce the weather category; their raw files remain available for
audit and all archived IDs remain reserved.
