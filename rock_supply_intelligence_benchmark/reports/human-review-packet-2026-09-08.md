# Human Review Packet — Bakeoff Preparation, Batch 1

Status: human-review worksheet only.  Your decisions will be recorded only
after you send them back; this document does not freeze the corpus or certify
the benchmark.

## What to review

For each item, answer one question:

> Does the retained primary source support this fixture's **provisional**
> label, without implying that a particular Rock Supply shipment is affected?

Use **Keep**, **Relabel**, **Reject**, or **Escalate**.  `Keep` means the
fixture can remain *reviewed* with its stated narrow label.  It never permits
an automated order, routing, tariff, or sanctions decision.

Do not decide whether a specific product is legally covered by a tariff or
sanction; that is an **Escalate** decision.

## Batch 1A — Carrier operations (plain English)

Recommendation: **Keep all three**.  Each is a dated first-party carrier
notice and explicitly describes carrier/terminal conditions.  Keep the labels
as `materially_relevant` / `port_vessel_carrier`; they still require later
route, entity, and time matching before an exposure is asserted.

| ID | Primary source | What the source must establish |
| --- | --- | --- |
| `ATOM-MAERSK-YANTIAN-OPS-2021` | [Maersk operations update](https://www.maersk.com/news/articles/2021/05/27/greater-china-yantian-port-operations-update) | Yantian/Shekou/Nansha yard, delay, gate-in, or service condition. |
| `ATOM-MAERSK-YANTIAN-GLOBAL-2021` | [Maersk global disruption update](https://www.maersk.com/news/articles/2021/06/16/new-levels-of-disruption) | Yantian congestion and carrier service impacts. |
| `ATOM-MAERSK-YANTIAN-MARKET-2021` | [Maersk Asia-Pacific update](https://www.maersk.com/news/articles/2021/06/15/asia-pacific-market-update-june) | Carrier/port or landside restriction information. |

## Batch 1B — Taiwan Customs notices (Traditional Chinese)

Recommendation: **Keep all six** if the page is a dated Customs notice about
the stated import/export, declaration, bonded-zone, or clearance rule.  The
fixture labels do **not** claim that every product is covered; if a notice is
only a draft or administrative form change, use **Relabel** to `monitor` or
**Escalate** rather than treating it as automatically applicable.

| ID | Primary source | Narrow proposed label |
| --- | --- | --- |
| `ATOM-TW-CUSTOMS-2025-0506` | [2025-05-06 notice](https://web.customs.gov.tw/singlehtml/698?cntId=076d783e62cb4279bf45b85b12b4d18f) | Customs export-declaration / origin-code rule. |
| `ATOM-TW-CUSTOMS-2026-0105` | [2026-01-05 draft notice](https://web.customs.gov.tw/singlehtml/698?cntId=cf893a4b015543ba87d4da801363b9ab) | Draft export-clearance rule; likely `monitor`, not automatically applicable. |
| `ATOM-TW-CUSTOMS-2022-0509` | [2022-05-09 notice](https://web.customs.gov.tw/singlehtml/698?cntId=0ef6c339f6f04d89af003bf53cfe231b) | Export-declaration manual change. |
| `ATOM-TW-CUSTOMS-2024-0105` | [2024-01-05 notice](https://web.customs.gov.tw/singlehtml/698?cntId=e5e8902aba53443d9a15a79990d40b6c) | Export declaration / strategic-high-tech clearance fields. |
| `ATOM-TW-CUSTOMS-2025-1223` | [2025-12-23 notice](https://web.customs.gov.tw/singlehtml/698?cntId=794cd409d66d4a24b4fe3d754bee5669) | Import/export cargo application and return-to-warehouse form change. |
| `ATOM-TW-CUSTOMS-2024-1213` | [2024-12-13 notice](https://web.customs.gov.tw/singlehtml/698?cntId=364c1ffd3e5846209d85ae2134a0ec67) | Bonded/free-trade-zone customs-code change. |

## Batch 1C — U.S. quota control

Recommendation: **Keep** if the page is a dated CBP quota bulletin; otherwise
**Relabel**.  It should remain a commodity-specific compliance cue, never a
general tariff conclusion.

| ID | Primary source | Narrow proposed label |
| --- | --- | --- |
| `ATOM-CBP-TUNA-QUOTA-2025` | [CBP quota bulletin](https://www.cbp.gov/trade/quota/bulletins/qb-25-214-2025) | U.S. tuna quota / proration record. |

## Reply format

You can reply in a single compact line, for example:

```text
1A: Keep all
1B: Keep 2025-0506, 2022-0509, 2024-0105, 2025-1223, 2024-1213; Relabel 2026-0105 to monitor
1C: Keep
```

Or use any per-ID list.  I will record only the decisions you make, rerun the
validator, and prepare Batch 2 (OFAC and longshore hard-negative controls).

## Recorded decisions — 2026-09-08

The reviewer approved Batch 1A, approved `ATOM-CBP-TUNA-QUOTA-2025`, and
approved the following Taiwan Customs fixtures without label changes:

`ATOM-TW-CUSTOMS-2025-0506`, `ATOM-TW-CUSTOMS-2022-0509`,
`ATOM-TW-CUSTOMS-2024-0105`, and `ATOM-TW-CUSTOMS-2024-1213`.

The reviewer relabeled `ATOM-TW-CUSTOMS-2026-0105` and
`ATOM-TW-CUSTOMS-2025-1223` from `materially_relevant` to `monitor`.
All ten decisions are recorded in the relevant atomic manifests as
`adjudication_status: reviewed`.  Reviewer identity was not supplied and is
still required for the eventual release record.

# Human Review Packet — Bakeoff Preparation, Batch 2

## Batch 2A — OFAC primary records (legal/compliance cues)

Recommendation: **Keep all eight as provisional `materially_relevant` /
`geopolitical_security` fixtures** if the individual Federal Register record
matches its title and is an OFAC notice, rule, determination, or general
license.  This is an evidence-quality decision only.  Do **not** determine
whether a supplier, vessel, product, or transaction is legally covered; that
would require a separate legal/compliance review.

| ID | Record |
| --- | --- |
| `ATOM-FR-OFAC-2026-17725` | [Notice of OFAC Sanctions Actions](https://www.federalregister.gov/api/v1/documents/2026-17725.json) |
| `ATOM-FR-OFAC-2026-17724` | [Notice of OFAC Sanctions Action](https://www.federalregister.gov/api/v1/documents/2026-17724.json) |
| `ATOM-FR-OFAC-2026-17613` | [Notice of OFAC Sanctions Action](https://www.federalregister.gov/api/v1/documents/2026-17613.json) |
| `ATOM-FR-OFAC-2026-17491` | [Iran-related Web General Licenses](https://www.federalregister.gov/api/v1/documents/2026-17491.json) |
| `ATOM-FR-OFAC-2026-17487` | [EO 13902 determination](https://www.federalregister.gov/api/v1/documents/2026-17487.json) |
| `ATOM-FR-OFAC-2026-17426` | [Iranian Transactions and Sanctions Regulations](https://www.federalregister.gov/api/v1/documents/2026-17426.json) |
| `ATOM-FR-OFAC-2026-17332` | [Notice of OFAC Sanctions Action](https://www.federalregister.gov/api/v1/documents/2026-17332.json) |
| `ATOM-FR-OFAC-2026-17265` | [Notice of OFAC Sanctions Action](https://www.federalregister.gov/api/v1/documents/2026-17265.json) |

## Batch 2B — Longshore-domain hard-negative controls

Recommendation: **Keep all seven as `irrelevant` /
`labor_infrastructure_transportation`**.  Each official record mentions
longshore labor, but concerns compensation, hearing tests, benefits, or
administrative paperwork—not a labor stoppage, terminal restriction, or
shipment disruption.  This distinction is the point of the controls.

| ID | Record |
| --- | --- |
| `ATOM-FR-LONGSHORE-2026-16904` | [Pre-hearing statement](https://www.federalregister.gov/api/v1/documents/2026-16904.json) |
| `ATOM-FR-LONGSHORE-2026-16901` | [Notice of recurrence form](https://www.federalregister.gov/api/v1/documents/2026-16901.json) |
| `ATOM-FR-LONGSHORE-2026-16896` | [Financial-obligations collection](https://www.federalregister.gov/api/v1/documents/2026-16896.json) |
| `ATOM-FR-LONGSHORE-2026-16882` | [Compensation-continuance claim](https://www.federalregister.gov/api/v1/documents/2026-16882.json) |
| `ATOM-FR-LONGSHORE-2026-12644` | [Hearing-loss testing standards](https://www.federalregister.gov/api/v1/documents/2026-12644.json) |
| `ATOM-FR-LONGSHORE-2026-12439` | [Student death-benefit continuation](https://www.federalregister.gov/api/v1/documents/2026-12439.json) |
| `ATOM-FR-LONGSHORE-2026-12433` | [Funeral-expense certification](https://www.federalregister.gov/api/v1/documents/2026-12433.json) |

## Reply format

```text
2A: Keep all
2B: Keep all
```

Or list exceptions by ID.  I will preserve any escalation as an explicit
review state rather than guessing at a legal or operational conclusion.

## Recorded Batch 2 decisions — 2026-09-08

The reviewer approved all eight OFAC records as source-quality-reviewed
geopolitical/compliance cues, explicitly without a sanctions-applicability
determination.  The reviewer also approved all seven longshore records as
irrelevant operational hard-negative controls.  Each corresponding fixture is
now marked `adjudication_status: reviewed`.

## Monitor-quota rebalance — approved 2026-09-08

To return the active monitor class to its fixed quota of 50 without altering
any reviewed decision, two unreviewed Federal Register **search-result pages**
were moved from the active corpus to `rejected/atomic/`:

- `ATOM-FR-TARIFF-PAGE-01`
- `ATOM-FR-TARIFF-PAGE-02`

Their raw payloads remain retained and their IDs remain reserved.  The removal
does not treat search results as individual trade events or legal conclusions.
