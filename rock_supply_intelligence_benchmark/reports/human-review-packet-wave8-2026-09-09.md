# Wave 8 Human Review Packet

Status: human-review worksheet. These nine mixed-language Taiwan Maritime and Port Bureau records remain provisional until decisions are applied. A Keep decision confirms only the narrow evidence label; it does not establish a supplier or shipment impact and does not freeze the benchmark.

## 8A — Material geopolitical navigation restrictions

Proposed label: `materially_relevant / geopolitical_security`. Verify that each source announces a concrete military or live-ammunition navigation restriction, rather than general political commentary.

- [ATOM-MPB-FIRING-EXERCISE-JUNE2025](https://www.motcmpb.gov.tw/Information/Detail/6b700edb-069a-41bc-b85e-4f6915453f1e?NodeId=10016&SiteId=2)
- [ATOM-MPB-CCP-EXERCISE-WARNING-2025](https://www.motcmpb.gov.tw/ServerFile/Get/10596867-66a5-473c-98ce-f2e1fdc11725?DLCount=1)
- [ATOM-MPB-MILITARY-EXERCISE-MAY2025](https://www.motcmpb.gov.tw/En/Information/Detail/78eb03a9-f17e-456f-8018-42161ee550cd?NodeId=10016&SiteId=2)

## 8B — Material port and vessel navigation restrictions

Proposed label: `materially_relevant / port_vessel_carrier`. Verify that each source announces a concrete work area or vessel-navigation restriction. Do not infer a wider port shutdown or shipment impact.

- [ATOM-MPB-NORTHEAST-MET-MAINTENANCE-2025](https://www.motcmpb.gov.tw/En/Information/Detail/a3e56eb4-e3bd-49b3-974f-54bce232d53d?NodeId=10016&SiteId=2)
- [ATOM-MPB-NORTHEAST-WRECK-OPS-2025](https://www.motcmpb.gov.tw/En/Information/Detail/5ac9e827-f30c-46d7-b849-ee1259fded91?NodeId=10016&SiteId=2)
- [ATOM-MPB-TAIPEI-BREAKWATER-WORK-2025](https://www.motcmpb.gov.tw/En/Information/Detail/6a1e4bf7-302d-411f-9d9f-61218e7fd146?NodeId=10016&SiteId=2)
- [ATOM-MPB-NORTHEAST-CABLE-REPAIR-2025](https://www.motcmpb.gov.tw/En/Information/Detail/29cdda0e-2669-4ec3-ae62-8a06d429d414?NodeId=10016&SiteId=2)
- [ATOM-MPB-NORTHEAST-OPS-JUNE2025](https://www.motcmpb.gov.tw/En/Information/Detail/7e2fb50d-bad8-4e67-ab5b-b4d1e743f660?NodeId=10016&SiteId=2)
- [ATOM-MPB-TAIPEI-BUOY-WORK-2025](https://www.motcmpb.gov.tw/Information/Detail/3f3cef70-3758-4a94-80c3-989d56e7d90c?NodeId=10016&SiteId=2)

## Excluded by collection safeguards

These candidates are not review items and were not admitted to the corpus:

- `ATOM-MPB-TAICHUNG-DREDGING-2025` — required source terms absent.
- `ATOM-MPB-TAICHUNG-PIERS-WORK-2025` — required source terms absent.
- `ATOM-MPB-TAICHUNG-MAINTENANCE-2025` — required source terms absent.
- `ATOM-MPB-TAICHUNG-CABLE-WORK-2026` — source fetch failed after bounded retries.

## Reply format

Reply with one decision per group:

`8A Keep all`  
`8B Keep all`

List any exception as `Relabel`, `Reject`, or `Escalate` followed by the exact sample ID.

## Recorded disposition

The reviewer kept every fixture in Wave 8A and 8B with its proposed narrow label. The nine hash-bound decisions are retained in `review-decisions-wave8.json`; applying them marks the corresponding manifests as reviewed without freezing the benchmark.
