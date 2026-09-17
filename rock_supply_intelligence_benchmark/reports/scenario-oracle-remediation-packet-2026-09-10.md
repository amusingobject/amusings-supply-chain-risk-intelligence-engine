# Scenario Oracle Remediation Packet

Status: proposed changes only. Nothing in this packet has altered an official scenario, evaluation time, expected result, or benchmark freeze state. A human approval must be recorded before any proposal is applied and regression-tested.

## Principle

The benchmark must not turn a weather advisory, a broad operational-response statement, or a synthetic shipment record into a claim of a specific port closure or shipment delay. Where primary evidence and deterministic route facts support only a narrower conclusion, the oracle must be narrowed as well.

## 18A — Panama affected-route scenario

Scenario: `E2E-PANAMA-DROUGHT-13`

Evidence available:

- Reviewed `GROUND-PANAMA-A48-2023` proves a time-valid Canal capacity restriction.
- The deterministic business fixture declares `SHP-SYN-013` via `Panama Canal`.

Proposed controlled change: attach the reviewed primary source and add an explicit, machine-checkable route-evidence assertion derived from the already-declared `via` field. Retain the event as infrastructure-related, but keep exposure as a **candidate** and preserve the prohibition on asserting an exact delay.

## 18B — Panama negative-route scenario

Scenario: `E2E-PANAMA-NEGATIVE-14`

Evidence available:

- The same reviewed Panama Canal source establishes the external restriction.
- `SHP-SYN-014` has a direct Kaohsiung-to-Long Beach leg and no Canal `via` field.

Proposed controlled change: add an explicit deterministic non-Canal route assertion and reuse the reviewed source as external context. Retain `unaffected` only because the fixture route is explicitly outside the Canal path; do not infer this from destination text alone.

## 18C — LA/LB affected-route scenario

Scenario: `E2E-LALB-CONGESTION-08`

Evidence available:

- Reviewed `GROUND-LALB-247-2021` proves a contemporaneous Port operational response (24/7 operations).
- `SHP-SYN-008` directly targets Long Beach.

Limit: no retained primary source quantifies congestion, a vessel queue, berth unavailability, or a delay for this shipment.

Proposed controlled change: replace the asserted high-severity `port_disruption` outcome with a **port-operations monitor** outcome, retain the route linkage only as a candidate exposure, and prohibit a congestion/delay claim. This preserves the routing test while removing unsupported historical severity.

## 18D — LA/LB negative-route scenario

Scenario: `E2E-LALB-NEGATIVE-09`

Evidence available:

- Reviewed `GROUND-LALB-247-2021` provides time-valid Port operational context.
- `SHP-SYN-LALB-N` has a direct Kaohsiung-to-Seattle leg.

Proposed controlled change: add an explicit deterministic out-of-route assertion for the Seattle leg, reuse the reviewed source only as external context, and retain the negative result. No claim is made that the source itself proves the Seattle shipment was unaffected.

## 18E — Three Gaemi cases

Scenarios: `E2E-GAEMI-KEELUNG-01`, `E2E-GAEMI-KHH-02`, `E2E-GAEMI-RECOVERY-03`

Finding: the retained Taiwan Maritime and Port Bureau operational notices are either later than the scenario cutoff or provide only a publication date, not a time that can be proven to precede the cutoff. The existing weather source remains valid weather evidence, but not port-operation evidence.

Proposed controlled change: keep these scenarios blocked from release until one of the following is separately approved:

1. retain a primary notice with exact timestamp provenance before each cutoff; or
2. redesign the scenarios as weather-only monitoring cases, removing all port-closure, restriction, recovery, affected-shipment, and strong-causality assertions.

No timestamp will be moved and no primary source will be backdated without an explicit new human decision.

## Reply format

```text
18A: Approve / Escalate
18B: Approve / Escalate
18C: Approve / Escalate
18D: Approve / Escalate
18E: Continue source collection / Approve weather-only redesign / Escalate
```
