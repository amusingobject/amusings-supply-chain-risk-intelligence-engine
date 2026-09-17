# Wave 15 Human Review Packet

Status: review completed. The reviewer kept 17 accessible fixtures and rejected three defective records: the empty FAA NAS SPA shell plus two GDACS rolling-data payloads. No sealed-holdout content was included.

## What to review

Confirm each primary source and narrow label. A monitoring snapshot or search/listing page should not be upgraded to a normal operational decision. Likewise, an official disruption or sanctions record establishes only the stated evidence—not shipment, supplier, legal, or transaction applicability beyond that evidence.

## 15A — FAA status snapshots (2)

Expected decision for every item: `monitor`. National Airspace System status is for observation; it is not a supply-chain disruption decision.

- `ATOM-FAA-NAS-SNAPSHOT` — FAA NAS status snapshot; dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FAA-NAS-SNAPSHOT.html>)
- `ATOM-FAA-NAS-XML` — FAA NAS status snapshot; selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FAA-NAS-XML.xml>)

## 15B — GDACS Taiwan hazard records (2)

Expected decision for every item: `materially_relevant`. Keep as dated Taiwan hazard evidence only; do not infer port operations.

- `ATOM-GDACS-EQ-TW-2024` — GDACS event search payload; dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-GDACS-EQ-TW-2024.json>)
- `ATOM-GDACS-TC-GAEMI` — GDACS event search payload; selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-GDACS-TC-GAEMI.json>)

## 15C — Taiwan port movement snapshots (4)

Expected decision for every item: `monitor`. These are operational data snapshots for monitoring and correlation, not disruption claims.

- `ATOM-TWPORT-01` — International commercial port ship inbound and outbound dynamic data (release A100F444); dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/first20/ATOM-TWPORT-01.ods>)
- `ATOM-TWPORT-02` — International commercial port ship inbound and outbound dynamic data (release 3CA720A3); selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/first20/ATOM-TWPORT-02.ods>)
- `ATOM-TWPORT-03` — International commercial port ship inbound and outbound dynamic data (release EC6DCEA7); selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/first20/ATOM-TWPORT-03.ods>)
- `ATOM-TWPORT-04` — International commercial port ship inbound and outbound dynamic data (release A37ADB7A); selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/first20/ATOM-TWPORT-04.ods>)

## 15D — Federal Register tariff search pages (8)

Expected decision for every item: `monitor`. Search-result pages are monitoring references, not self-sufficient regulatory event evidence.

- `ATOM-FR-TARIFF-PAGE-03` — Federal Register tariff search results page 3; holdout; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-03.json>)
- `ATOM-FR-TARIFF-PAGE-04` — Federal Register tariff search results page 4; dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-04.json>)
- `ATOM-FR-TARIFF-PAGE-05` — Federal Register tariff search results page 5; selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-05.json>)
- `ATOM-FR-TARIFF-PAGE-06` — Federal Register tariff search results page 6; holdout; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-06.json>)
- `ATOM-FR-TARIFF-PAGE-07` — Federal Register tariff search results page 7; dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-07.json>)
- `ATOM-FR-TARIFF-PAGE-08` — Federal Register tariff search results page 8; selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-08.json>)
- `ATOM-FR-TARIFF-PAGE-09` — Federal Register tariff search results page 9; holdout; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-09.json>)
- `ATOM-FR-TARIFF-PAGE-10` — Federal Register tariff search results page 10; dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-FR-TARIFF-PAGE-10.json>)

## 15E — Direct official evidence records (2)

Expected decision for every item: `materially_relevant`. Keep the Port of Los Angeles incident as stated operational evidence and the OFAC designation as narrow sanctions evidence; neither establishes a user-specific action.

- `ATOM-OFAC-SOVCOMFLOT-2024` — Russia-related Designations; Issuance of Russia-related General Licenses; holdout; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-OFAC-SOVCOMFLOT-2024.html>)
- `ATOM-POLA-TRUCK-OPS-2024` — Port of Los Angeles Truck Accident Impacts Operations; dev; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-POLA-TRUCK-OPS-2024.html>)

## 15F — Coast Guard and OFAC listing references (2)

Expected decision for every item: `monitor`. These broad listings/notices require further narrowing before a normal business decision.

- `ATOM-NAVCEN-LNM-11-12-24` — Local Notice to Mariners District 11 Week 12/24; selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/first20/ATOM-NAVCEN-LNM-11-12-24.pdf>)
- `ATOM-OFAC-RECENT-ACTIONS` — OFAC Recent Actions listing; selection; [raw record](</var/home/amusing/Documents/projects/business_projects/supply-chain-disruption-project/rock_supply_intelligence_benchmark/raw/wave2/ATOM-OFAC-RECENT-ACTIONS.html>)

## Suggested response

```text
15A: Keep all
15B: Keep all
15C: Keep all
15D: Keep all
15E: Keep all
15F: Keep all
```

List any exceptions beneath the relevant group. After this packet, only the sealed-holdout review procedure remains.

## Applied review record

On 2026-09-10, the human reviewer kept all proposed labels except:

- `ATOM-FAA-NAS-SNAPSHOT` — rejected because its retrieved source is an empty SPA shell.
- `ATOM-GDACS-EQ-TW-2024` — rejected because its payload contains rolling 2025–2026 data rather than the claimed 2024 event.
- `ATOM-GDACS-TC-GAEMI` — rejected for the same rolling-data timestamp mismatch.

The 17 kept active manifests are marked `adjudication_status: reviewed`. The three rejected manifests and their retained raw evidence are preserved for audit; their replacements must satisfy the same quota dimensions. Hash-bound decisions are retained in `review-decisions-wave15.json`.
