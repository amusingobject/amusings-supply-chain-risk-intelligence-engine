# Registry Collection Human Review

Status: human-review worksheet only. These items remain provisional until decisions are recorded.

## What to review

For each item, decide whether the retained direct source genuinely supports the proposed narrow class and category. Do not determine whether a particular shipment, supplier, vessel, product, or transaction is affected.

Use **Keep**, **Relabel**, **Reject**, or **Escalate**. Keep means the source supports the proposed evidence label; it does not authorize an operational or legal decision.

| ID | Proposed label | What the source must establish | Direct source |
| --- | --- | --- | --- |
| `ATOM-ILA-STRIKE-EXEMPTIONS-2024` | `materially_relevant / labor_infrastructure_transportation` | ILA identifies military-cargo and passenger-cruise exemptions during strike; verify cues: military cargo; passenger cruise ships | [primary source](https://ilaunion.org/ila-will-maintain-pledge-to-handle-military-cargo-during-strike-passenger-cruise-ships-to-be-unaffected-by-10-1-strike/) |
| `ATOM-PANAMA-TRANSIT-REDUCTION-A48-2023` | `materially_relevant / labor_infrastructure_transportation` | Panama Canal reduces transit booking slots amid watershed precipitation deficit; verify cues: number of booking slots; 18 per day | [primary source](https://pancanal.com/wp-content/uploads/2023/01/ADV48-2023-Reduction-in-Transits-Due-to-the-Ongoing-Deficit-in-Precipitation-in-the-Canal-Watershed.pdf) |
| `ATOM-ILA-EAST-GULF-STRIKE-2024` | `materially_relevant / labor_infrastructure_transportation` | ILA launches coastwide East and Gulf Coast port strike; verify cues: coastwide strike; Atlantic and Gulf Coasts | [primary source](https://ilaunion.org/ila-president-harold-j-daggett-joins-picket-lines-throughout-port-newark-elizabeth-at-start-of-strike-rallies-tens-of-thousands-of-ila-members-to-stay-strong-and-united/) |
| `ATOM-POLA-CONGESTION-CLEAR-CARGO-2021` | `materially_relevant / port_vessel_carrier` | Ports announce measures to improve cargo movement amid congestion; verify cues: cargo movement; congestion | [primary source](https://portoflosangeles.org/references/2021-news-releases/news_102521_jointclearcargo) |

## Scenario-grounding candidate

The ILA strike source is also a candidate to replace synthetic-only grounding for open scenario `E2E-LABOR-EAST-COAST-16`. Confirm that the source establishes a coastwide ILA labor disruption at Atlantic/Gulf port terminals by the scenario evaluation time. This approval would validate the evidence candidate only; it would not certify shipment impact, delay duration, or causality.

- `GROUND-ILA-EAST-GULF-STRIKE-2024`: **Keep** or **Escalate**.

## Reply format

Reply with `Keep all, including grounding candidate` or list per-ID exceptions, for example: `Keep ATOM-...; Relabel ATOM-... to monitor; Escalate GROUND-...`.

## Recorded disposition

The reviewer kept all four fixtures with their proposed narrow labels and approved the grounding candidate within its stated evidence-only scope. Fixture decisions are hash-bound in `review-decisions-wave10.json`; the grounding approval is recorded in `scenario-evidence-candidates.json`. This does not freeze the benchmark or establish shipment impact.
