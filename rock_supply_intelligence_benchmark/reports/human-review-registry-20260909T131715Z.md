# Registry Collection Human Review

For each item, decide whether the retained direct source genuinely supports the proposed narrow class and category. Do not determine whether a particular shipment, supplier, vessel, product, or transaction is affected.

Use **Keep**, **Relabel**, **Reject**, or **Escalate**. Keep means the source supports the proposed evidence label; it does not authorize an operational or legal decision.

Evidence cues for this batch:

- The two ILWU records must explicitly support labor action that halted operations or disrupted vehicle offloading.
- The two OFAC records must be official maritime entity/vessel designation records. They are geopolitical/compliance cues, not transaction-specific legal conclusions.
- The CBP archive must explicitly identify the CrowdStrike outage and an impact on CBP operations.

| ID | Split | Class | Category | Direct source |
| --- | --- | --- | --- | --- |
| `ATOM-ILWU-WWL-CONTRACT-2025` | holdout | materially_relevant | labor_infrastructure_transportation | https://www.ilwu.org/wwl-tacoma-contract/ |
| `ATOM-ILWU-WWL-STRIKE-2024` | holdout | materially_relevant | labor_infrastructure_transportation | https://www.ilwu.org/logistics-workers-use-supply-chain-power-to-win/ |
| `ATOM-OFAC-OCEANLINK-2024` | holdout | materially_relevant | geopolitical_security | https://ofac.treasury.gov/recent-actions/20240404 |
| `ATOM-OFAC-SHADOW-FLEET-2024` | holdout | materially_relevant | geopolitical_security | https://ofac.treasury.gov/recent-actions/20241203 |
| `ATOM-CBP-CSMS-CROWDSTRIKE-2024` | selection | materially_relevant | regulatory_trade_customs | https://www.cbp.gov/sites/default/files/2024-08/CSMS%20ArchiveJuly2024_508.pdf |

## Recorded decisions — 2026-09-09

The reviewer kept all five fixtures with their proposed narrow labels:

- Batch 3A: both ILWU labor fixtures kept.
- Batch 3B: both OFAC maritime/geopolitical fixtures kept.
- Batch 3C: the CBP customs-operations fixture kept.

The records are marked `adjudication_status: reviewed`. Reviewer identity was not supplied and remains required for the eventual release record.
