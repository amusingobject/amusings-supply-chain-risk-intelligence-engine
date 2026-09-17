# Gaemi Weather-Only Redesign Packet

Status: proposed changes only. No scenario, timestamp, expected result, or benchmark freeze state has been changed by this packet.

## Why this redesign is needed

The retained Central Weather Administration source proves the Gaemi weather event. It does not prove a general Keelung or Kaohsiung port closure, a terminal restriction, carrier-service impact to the synthetic Keelung-to-Long-Beach shipments, an actual delay, or a recovery state. All collected operational candidates were rejected or could not be captured under the source-integrity rules.

The safe remedy is to test weather-event handling without asserting unsupported operational outcomes.

## 22A — Keelung weather monitor

Scenario: `E2E-GAEMI-KEELUNG-01`

Proposed controlled change:

- Retain the CWA Gaemi weather event as `weather`, high severity, `monitor` disposition.
- Remove the asserted Keelung closure, affected shipment, and deterministic departure-delay linkage.
- Replace the exposure with a provisional `weather_monitoring` candidate, rule-based and not shipment-linked.
- Recommendation: monitor official weather notices and request carrier confirmation; no rerouting, order change, or port-closure claim.
- Explicitly prohibit port-closure, terminal-restriction, and actual-delay assertions without separate evidence.

## 22B — Kaohsiung weather monitor

Scenario: `E2E-GAEMI-KHH-02`

Proposed controlled change:

- Retain the CWA Gaemi weather event as `weather`, high severity, `monitor` disposition.
- Remove the asserted Kaohsiung port restriction, affected shipment, and deterministic departure-delay linkage.
- Replace the exposure with a provisional `weather_monitoring` candidate, rule-based and not shipment-linked.
- Recommendation: monitor official weather notices and request carrier confirmation; no autonomous action.
- Explicitly prohibit general port-closure, terminal-restriction, carrier-cancellation, and actual-delay assertions without separate evidence.

## 22C — Weather lifecycle monitor, not recovery claim

Scenario: `E2E-GAEMI-RECOVERY-03`

Proposed controlled change:

- Retain the CWA Gaemi weather event as `weather`, moderate severity, `monitor` disposition.
- Remove the `port_disruption` recovery-lifecycle claim, affected shipment, and deterministic linkage.
- Replace the exposure with a provisional `weather_lifecycle_monitoring` candidate, rule-based and not shipment-linked.
- Recommendation: monitor official weather notices and request carrier confirmation; do not claim recovery, reopening, or continued closure without separate operational evidence.
- Explicitly prohibit recovery, port-closure, terminal-restriction, and actual-delay assertions without separate evidence.

## Outcome

This keeps the three scenarios useful for weather-event detection, evidence discipline, and safe-monitoring behavior. It deliberately stops using them to benchmark port or carrier operational correlation.

## Reply format

```text
22A: Approve / Escalate
22B: Approve / Escalate
22C: Approve / Escalate
```
