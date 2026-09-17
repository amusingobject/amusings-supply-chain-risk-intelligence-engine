# Gaemi Source Collection Status

Status: **both provisional candidates rejected by human review; raw captures retained; no candidate remains eligible for attachment.**

## Review candidate — Keelung service disruption

Candidate: `GROUND-GAEMI-KEELUNG-MATSU-2024`

- Publisher: Matsu Sea Transportation Booking System
- Direct source: https://matsuebs.com/news/Detail/202407230000008?isLayoutForApp=False&pageIndex=98
- Source date: 2024-07-23; recorded conservatively as `2024-07-23T23:59:59Z`, before the `E2E-GAEMI-KEELUNG-01` cutoff.
- Narrow supported claim: **Keelung–Matsu carrier-service cancellation** on July 23.
- Raw capture: `raw/scenario-grounding/GROUND-GAEMI-KEELUNG-MATSU-2024.html`
- SHA-256: `ccc0c843ff67dbd322073f33d9868c24ca6a90f5a36cd900d7353d70c1404d1c`

Limit: it does **not** prove a general Keelung port closure, a container-terminal restriction, or an impact to the scenario's Keelung-to-Long-Beach shipment. It can support only a narrower carrier-service monitor with an unlinked, candidate-only shipment advisory.

Reply: `21A: Keep as narrow carrier-service evidence / Reject / Escalate`

Decision: **Rejected.** Not attached to `E2E-GAEMI-KEELUNG-01`.

## Review candidate — Kaohsiung service disruption

Candidate: `GROUND-GAEMI-KHH-MOTC-2024`

- Publisher: Ministry of Transportation and Communications, Taiwan
- Direct source: https://www.motc.gov.tw/ch/app/data/view?id=14&module=news&serno=d1c1dd95-ed5e-4ee8-9d1f-067867e2fbb6
- Source date: 2024-07-22; recorded conservatively as `2024-07-22T23:59:59Z`, which is still before the `E2E-GAEMI-KHH-02` cutoff.
- Narrow supported claim: scheduled **Kaohsiung–Magong carrier service cancellation** on July 24.
- Raw capture: `raw/scenario-grounding/GROUND-GAEMI-KHH-MOTC-2024.html`
- SHA-256: `8e0dde227853e4c84f4276dfb86b29d9b94ad02ae21fd62595beb565560019a4`

Limit: this does **not** prove a general Kaohsiung port closure, a container-terminal restriction, a shipment delay, or a recovery state. It may support only a narrowed carrier-service monitor oracle if a human approves that redesign.

Reply: `20A: Keep as narrow carrier-service evidence / Reject / Escalate`

Decision: **Rejected.** Not attached to `E2E-GAEMI-KHH-02`; the dependent 20B redesign was withdrawn and the scenario returned to pending source collection.

## Recovery collection attempt

Candidate plan: `GROUND-GAEMI-RECOVERY-MPB-2024`

The direct Maritime and Port Bureau notice describes a July 26 Keelung–Matsu cancellation and is relevant only as possible continued carrier-service disruption, not recovery or a Long Beach shipment impact. The controlled collector could not retrieve a hashable source body after two attempts, so **no candidate was created** and nothing was attached. The plan remains only as a retry reference; no search-result content was substituted.

The official Maritime and Port Bureau sources located during this pass are either after the applicable scenario cutoffs or provide a calendar date without a timestamp that proves publication before the cutoff. They cannot be attached under the benchmark's time-validity rule.

The 2024-07-24 Maritime and Port Bureau Costa Serena notice is relevant context for a typhoon-driven itinerary change, but it provides only a publication date. It is not sufficient for the Keelung or Kaohsiung scenarios at their early 2024-07-24 evaluation times.

The 2024-07-27 ferry recovery notice and later incident/recovery notices are after the scenario cutoffs and are rejected as scenario evidence. No timestamp has been moved, inferred, or backdated.

Next collection target: an official Maritime and Port Bureau, Taiwan International Ports Corporation, carrier, or harbor-master notice with a preserved precise timestamp before each scenario cutoff, explicitly covering the relevant port operation or carrier service.
