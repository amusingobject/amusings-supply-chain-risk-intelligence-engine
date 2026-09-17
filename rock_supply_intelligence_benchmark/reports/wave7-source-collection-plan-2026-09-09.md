# Wave 7 Source-Specific Collection Plan

Status: planning only. No release freeze, review certification, anti-spam default enablement, or GitHub push is authorized by this plan.

## Starting deficit

After Wave 6, the corpus is 349/420. Remaining targets are 1 dev, 35 selection, 35 holdout; 27 materially relevant and 44 irrelevant records; 50 zh-TW, 17 mixed, and 4 English records. Category deficits are 30 labor/infrastructure/transportation, 27 geopolitical/security, and 14 port/vessel/carrier.

## Collection sequence

1. **Taiwan official sources first (32 items)** — direct dated notices from the Maritime and Port Bureau, Taiwan International Trade Administration, and Taiwan PortNET. Target 28 zh-TW and 4 mixed records, divided among port operations, export controls, and transport/labor notices. Keep each source-specific; do not use search results, weather-only pages, or generic informational pages to assert operational disruption.
2. **Bilingual official controls (13 items)** — direct Chinese-English port notices and customs or trade operational forms. Target 13 mixed irrelevant controls, preventing the final corpus from learning that every bilingual record is a disruption.
3. **English gap closure (4 items)** — direct USTR/Treasury/official port releases only, selected to close the small English shortfall while prioritizing labor and geopolitical categories.
4. **Split discipline** — assign exactly 1 verified record to dev and distribute the rest approximately evenly across selection and sealed holdout. Use the registry allocator; do not read sealed inputs in a model pathway.

## Acceptance and stop conditions

- Collect only public direct HTTPS sources from an allowlisted publisher/domain.
- Require a source-specific title, date, content hash, raw retention, provenance, and acceptance terms before materialization.
- Quarantine wrong-domain, duplicate-hash, missing-term, malformed, future-dated, or unextractable material.
- Stop each batch for validation; none of the above substitutes for human adjudication.
- Do not use a later publication to ground an earlier scenario timestamp.
