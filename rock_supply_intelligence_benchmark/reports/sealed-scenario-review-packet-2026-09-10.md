# Sealed Scenario Evidence Review Packet

Status: **human-only review required.** This packet does not inspect, quote, copy, or alter sealed holdout scenario content. It is based only on strict-validator identifiers and requirement categories.

## Decision boundary

The six remaining non-Gaemi evidence gaps are sealed holdout scenarios. They must not be opened to a model or repaired from a validator message alone. A human reviewer should inspect each scenario in the local sealed-review workflow and record only one of these outcomes:

- **Evidence confirmed:** the retained primary evidence explicitly supports the operational claim before the scenario cutoff.
- **Narrow oracle:** retain the scenario but remove or reduce the unsupported operational claim.
- **Keep sealed / block release:** insufficient evidence; do not alter the expected result from inference.

No source should be attached and no expected result should change without a recorded human decision.

## Review items

### 19A — Carrier ETA conflict

Scenario: `E2E-CARRIER-ETA-CONFLICT-21`

Required support: an official carrier-service or carrier-exception record that is time-valid for the scenario. A generic status page, weather source, or inferred schedule disruption is not sufficient.

### 19B — Maersk cyber event

Scenario: `E2E-MAERSK-CYBER-23`

Required support: a time-valid carrier-service or carrier-exception statement. Do not infer an operational service impact from a general cyber-news claim.

### 19C — Yantian operational scenario

Scenario: `E2E-YANTIAN-21`

Required support: a time-valid port-operation, carrier-service, or explicit port-disruption source.

### 19D — Shanghai negative-route scenario

Scenario: `E2E-SHANGHAI-NEGATIVE-22`

Required support: the same standard as 19C, plus a deterministic route/entity assertion for any retained negative result.

### 19E — Conflicting-source scenario

Scenario: `E2E-CONFLICT-28`

Required support: each retained source must be provenance-complete and time-valid. If the sources conflict, the only valid result is an explicit ambiguity/review state; no first-match or majority inference.

### 19F — Prompt-injection scenario

Scenario: `E2E-PROMPT-INJECTION-27`

Required support: retain the injection payload as untrusted fixture content and verify that the expected outcome is quarantine/review. Do not require the malicious payload itself to serve as operational evidence; if the scenario asserts a real port outcome, separately retain time-valid operational evidence or narrow the oracle.

## Reply format

```text
19A: Evidence confirmed / Narrow oracle / Keep sealed
19B: Evidence confirmed / Narrow oracle / Keep sealed
19C: Evidence confirmed / Narrow oracle / Keep sealed
19D: Evidence confirmed / Narrow oracle / Keep sealed
19E: Evidence confirmed / Narrow oracle / Keep sealed
19F: Evidence confirmed / Narrow oracle / Keep sealed
```
