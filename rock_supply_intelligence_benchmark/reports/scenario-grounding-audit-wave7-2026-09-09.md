# Scenario Grounding Audit — Wave 7

Status: reviewed collection disposition, not benchmark certification. No scenario truth, evaluation timestamp, or expected outcome was changed.

## Outcome

The 13 validator warnings remain explicitly unresolved. Candidate primary sources were assessed against the scenario evaluation timestamp and operational-claim requirement. No later or ambiguously timed source was used to backfill historical truth.

| Scenario warning | Current status | Reason / next admissible action |
| --- | --- | --- |
| `e2e-gaemi-keelung-01` | Unresolved | Existing evidence is weather-only. The direct MPB ferry recovery release is dated 2024-07-27, after the 2024-07-24 evaluation timestamp. Find a direct operational notice demonstrably published by 01:00Z on July 24 or redesign the scenario through a separately reviewed oracle change. |
| `e2e-gaemi-khh-02` | Unresolved | The MPB Costa Serena release is dated July 24, but the retained page does not establish a publication time before the 03:00Z evaluation cutoff. It cannot be admitted as time-valid grounding without stronger timestamp provenance. |
| `e2e-gaemi-recovery-03` | Unresolved | The dated recovery release is July 27, after the July 26 evaluation cutoff. |
| `e2e-lalb-congestion-08` | Unresolved | Existing source is synthetic. Later Port of Los Angeles annual/statistical reporting cannot prove what was available at the 2021-10-18 evaluation timestamp. Find a contemporaneous direct port notice or review the oracle. |
| `e2e-lalb-negative-09` | Unresolved | A port disruption source cannot by itself prove that an unrelated Seattle shipment was unaffected. This requires deterministic route/entity evidence in addition to contemporaneous port evidence. |
| `e2e-panama-drought-13` | Unresolved | Panama Canal primary material confirms transit restrictions, but the available page/advisory publication timing has not been proven to precede the 2023-12-15 12:00Z cutoff. |
| `e2e-panama-negative-14` | Unresolved | Canal restrictions do not prove a Long Beach route was unaffected. Route evidence and a time-valid canal notice are both required. |
| `e2e-carrier-eta-conflict-21` | Unresolved | This is a synthetic conflict case. A real primary source cannot certify the constructed carrier-versus-AIS contradiction without retained, timestamped carrier and AIS records for the same voyage. |
| `e2e-conflict-28` | Unresolved | The constructed conflict needs two retained, timestamp-valid operational notices with incompatible states. Neither may be inferred or synthesized as primary evidence. |
| `e2e-maersk-cyber-23` | Unresolved | Maersk's direct cyber update was published June 28, after the scenario's June 27 12:00Z cutoff. It explicitly states APM Terminals impacts, but cannot be backdated. |
| `e2e-prompt-injection-27` | Unresolved | The adversarial untrusted text must remain untrusted and cannot ground its own port claim. A separate time-valid primary operational source is required, or the oracle must explicitly test rejection without asserting an external disruption. |
| `e2e-shanghai-negative-22` | Unresolved | A Shanghai disruption source cannot establish absence of a Taiwan-origin dependency. Deterministic entity/route evidence is required alongside a contemporaneous primary port source. |
| `e2e-yantian-21` | Unresolved | No direct Yantian operator notice demonstrably available by the scenario cutoff has been retained. Secondary reporting is insufficient. |

## Primary-source leads retained for follow-up

- A.P. Moller–Maersk, “Cyber attack update,” published 2017-06-28: explicit IT-system and APM Terminals operational impact, but too late for the current scenario timestamp.
- Panama Canal Authority, December 2023 transit-restriction and booking-slot notices: operationally relevant, but exact publication timing must be proven before linking to a noon-UTC cutoff.
- Taiwan Maritime and Port Bureau, Costa Serena Gaemi itinerary change, dated 2024-07-24: operationally relevant, but exact publication time is not present in the retained page.
- Taiwan Maritime and Port Bureau, ferry-service recovery notice, dated 2024-07-27: valid Wave 6 fixture, but too late for all three existing Gaemi scenario cutoffs.

## Gate

Strict validation must continue to fail on these warnings until each scenario has time-valid primary operational support or a separately reviewed and regression-tested oracle redesign. Merely adding `supported_claims` metadata is not an acceptable repair.
