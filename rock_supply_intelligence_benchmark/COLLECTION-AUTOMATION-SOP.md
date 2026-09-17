# Collection Automation SOP

This workflow increases collection throughput while keeping every new fixture provisional, traceable, and fail closed.

## Safety boundary

- Collect only direct public HTTPS pages declared in `collection-source-registry.json`.
- Never use a search-results page as evidence.
- Never infer an operational disruption from a weather-only source.
- Never expose sealed holdout content to a model or collection process.
- Never freeze the benchmark, approve human labels, enable anti-spam by default, or push changes as part of collection.
- A candidate that fails URL, extraction, content-term, hash, or schema validation goes to `quarantine/` and is not materialized as a fixture.

## Routine run

From the repository root:

```bash
.venv/bin/python rock_supply_intelligence_benchmark/tools/registry_collect.py plan
.venv/bin/python rock_supply_intelligence_benchmark/tools/registry_collect.py run --limit 10
.venv/bin/python rock_supply_intelligence_benchmark/tools/validate_corpus.py
.venv/bin/python -m pytest -q
```

`plan` is network-free. It validates the registry, excludes existing IDs, observes retry cooldowns, and ranks candidates against current split, class, language, and event-category deficits.

`run` downloads one candidate at a time with source-specific rate limits and bounded retries. It checkpoints after every candidate, so an interrupted run can resume safely. Successful items are written to `raw/registry-wave3/` and `atomic/<split>/`; rejected payloads are retained under `quarantine/` with a machine-readable reason.

## Source-index discovery

Use the discovery tool to find potential direct pages from an approved publisher's own index:

```bash
.venv/bin/python rock_supply_intelligence_benchmark/tools/registry_discovery.py --limit 25
```

Discovery only writes `reports/registry-discovery-proposals.json`. It filters index links to the publisher's approved HTTPS domain and configured direct-page paths, verifies configured terms and a published date on the direct page, and ranks proposals against remaining quotas. It never writes a fixture, raw evidence, or a registry candidate automatically. Review each proposal, assign a stable sample ID, then add it to `collection-source-registry.json` before invoking the bounded collector.

## Review and monitoring

- Review the newest `reports/human-review-registry-*.md` packet and decide **Keep**, **Relabel**, **Reject**, or **Escalate** for every row.
- Use `registry_collect.py health` to refresh and display current source cursors, candidate states, remaining quotas, and the last 50 run summaries without fetching anything.
- Inspect `reports/collection-runs/` when diagnosing a particular run.
- Inspect `reports/collection-registry-state.json` for retry times and the last candidate checked per source.

Human decisions must be applied through the existing review workflow. Collection output remains provisional until that review is recorded.

## Adding or repairing a source

1. Add the official publisher/domain and direct dated candidates to `collection-source-registry.json`.
2. Include stable sample IDs, accurate publication timestamps, expected quota dimensions, and two or more page-specific acceptance terms.
3. Validate the registry and view the network-free plan before running collection.
4. If a source changes its page or document format, leave the failed body quarantined, correct the registry entry, and wait for or deliberately clear the recorded cooldown only after investigation.
5. Disable sources with unresolved legal, access, DNS, or content-stability problems and explain the reason in `access_constraints`.

## Scheduler entry point

A scheduler may invoke this bounded command once per interval:

```bash
.venv/bin/python rock_supply_intelligence_benchmark/tools/registry_collect.py run --limit 10
```

Do not overlap runs. The scheduler should alert on a nonzero exit, new quarantine entries, corpus validation errors, or a sustained zero-yield source. A successful scheduled run does not authorize freezing, model evaluation on holdout, automatic label approval, or publication.
