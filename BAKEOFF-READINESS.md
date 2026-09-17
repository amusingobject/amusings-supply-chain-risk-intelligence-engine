# Local-Model Bakeoff Readiness Checklist

Status: preparation in progress. The benchmark is not frozen and is not ready
for an official bakeoff yet.

## Collection and corpus balance

- [x] Rebalance the active release corpus to 225 fixtures, then validate 27 post-review collection candidates; the retained additions include one dated CBP record, three dated carrier operational notices, eight individual OFAC Federal Register records, seven explicit irrelevant longshore-domain controls, and six Taiwan Customs regulatory notices. Two unreviewed tariff search pages were subsequently rejected to preserve source-specific quality and the fixed monitor quota (250 active fixtures).
- [x] Preserve rejected manifests and raw sources for audit; reserve rejected IDs.
- [ ] Collect the remaining 170 fixtures using lawful, public, source-specific records (90 materially relevant and 80 irrelevant).
- [ ] Meet every class target without exceeding the fixed 420-fixture corpus.
- [ ] Meet all split, language, and event-category targets.
- [ ] Validate every retained source hash, provenance record, and raw reference.

## Scenario grounding

- [x] Create the scenario grounding queue.
- [ ] Collect dated primary sources for every operational claim in the queue.
- [ ] Attach only evidence that explicitly supports port, carrier, infrastructure, labor, or geopolitical claims.
- [ ] Re-run strict validation with no unsupported operational-claim errors.

## Human review — your role

- [ ] Review fixtures in small batches: Keep, Relabel, Reject, or Escalate.
- [ ] Confirm each source supports its proposed class and category.
- [ ] Confirm operational scenarios do not infer port or carrier impacts from weather-only evidence.
- [ ] Approve the final 420 active fixtures and their labels.
- [ ] Provide reviewer name and completion date for the release record.

## Bakeoff controls

- [x] Keep malformed identities, alias conflicts, invalid profiles, and unsafe source configurations fail-closed.
- [x] Keep holdout data protected and prevent development-mode access.
- [x] Keep expected/frozen truth protected from benchmark runs.
- [ ] Run strict corpus validation successfully.
- [ ] Freeze and lock the reviewed corpus hash.
- [ ] Run the official local-model bakeoff on locked inputs.
- [ ] Review metrics, safety gates, and failure cases before any production decision.

## What can continue while you are away

- Targeted lawful collection for the remaining quota gaps.
- Scenario-grounding source discovery and provenance preparation.
- Validator, test, and bakeoff-tooling hardening.
- Review-packet preparation. No human labels, freeze, or official bakeoff will be claimed without your approval.
