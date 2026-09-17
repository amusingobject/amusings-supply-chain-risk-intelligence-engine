# Development Plan: Review, Bakeoff, and Scenario Grounding

Status: implementation plan. This work may proceed while fixture collection
continues. It must not freeze the benchmark, expose sealed holdout inputs, or
claim official bakeoff results.

Implementation note — 2026-09-08: shared schemas, review reconciliation and
batch tooling, candidate-evidence verification, bakeoff run specifications,
preflight, and descriptive report comparison are now deployed. Controlled
scenario attachment and checkpoint/resume remain intentionally gated behind
the next implementation increment because they mutate or reuse evaluation
artifacts.

## Current baseline

- Active corpus: 250 / 420 fixtures.
- Human-reviewed fixture manifests: 25.
- `manifest.json` review summary: 0 reviewed. This derived-summary drift is the
  first issue to fix.
- Existing model interfaces: Ollama and OpenAI-compatible endpoints. The latter
  already covers vLLM and llama.cpp servers.
- Existing safeguards: benchmark trust gate, protected output paths, sealed
  holdout access controls, deterministic prompt settings, source hashes, and
  scenario grounding warnings.

## Non-negotiable boundaries

- Fixture manifests and retained raw sources are the source of truth.
- Review decisions are human-authored; tooling may validate and apply them but
  may not invent or self-certify them.
- Development runs never read holdout inputs.
- Official bakeoff mode remains blocked until collection, review, strict
  validation, freeze, and lock gates all pass.
- Scenario evidence must directly support its declared claim. Weather-only or
  search-result evidence cannot establish port or carrier operations.
- Generated reports and checkpoints remain under `runs/` or `reports/` and
  cannot overwrite fixtures, schemas, scenarios, expected truth, or sealed
  inputs.

## Workstream 1: Human-review workflow

### 1.1 Decision contract and audit ledger

Add a versioned review-decision schema containing:

- decision ID, sample ID, reviewer, RFC 3339 timestamp, and rationale;
- `keep`, `relabel`, `reject`, or `escalate` outcome;
- previous labels and requested replacement labels;
- manifest hash observed by the reviewer;
- source checks for publisher/locator, retained-body match, label support, and
  unsupported-claim detection.

Store accepted decisions in an append-only review ledger. Reapplying the same
decision is idempotent; a different decision against the same manifest hash is
an explicit conflict.

### 1.2 Review batch generator

Create a CLI that can generate Markdown and JSON review batches filtered by:

- class, category, language, split, source family, or collection wave;
- provisional, reviewed, rejected, or escalated state;
- maximum batch size and deterministic sample ordering.

Every packet should show the source link, raw reference, current labels,
recommended review question, and a machine-readable response template. Sealed
holdout content must never be rendered without authorization.

### 1.3 Safe decision application

Create a dry-run-first command that:

- verifies the decision schema and manifest hash;
- applies exact relabels without guessing missing values;
- moves rejected manifests to `rejected/atomic/` while retaining raw sources
  and reserving IDs;
- records escalations without converting them into normal labels;
- updates adjudication metadata and the audit ledger atomically;
- refuses changes when the benchmark is frozen or a decision is stale;
- runs corpus validation before reporting success.

### 1.4 Derived review reconciliation

Derive reviewed totals from active fixture manifests and reconcile
`manifest.json` plus readiness reports. The global review state must remain
incomplete until all 420 active fixtures are reviewed and a named reviewer and
completion timestamp are present.

### Workstream 1 acceptance gates

- The current 25 reviewed manifests reconcile to a summary count of 25.
- Keep, relabel, reject, and escalate each have positive and fail-closed tests.
- Stale hashes, blank reviewers, unknown IDs, malformed label patches, and
  conflicting duplicate decisions are rejected without partial writes.
- Rejection preserves raw evidence and prevents sample-ID reuse.
- A development user cannot render or modify sealed holdout content.

## Workstream 2: Local-model bakeoff harness

### 2.1 Versioned run specification

Add a JSON run specification covering:

- provider (`ollama` or `openai_compat`), endpoint, model name, and model hash;
- execution class, context size, output-token limit, timeout, temperature, and
  seed;
- prompt/schema versions, selected open splits, and optional development limit;
- corpus/trust fingerprint and hardware capture settings.

An immutable normalized copy belongs in every run directory.

### 2.2 Provider preflight and metadata

Extend both existing adapters with health and model-metadata checks. Confirm
the requested model exists, the endpoint is local when execution class is
local, structured output is supported or explicitly emulated, and the model
hash/configuration is captured before inference begins.

### 2.3 Resumable execution

Write one atomic checkpoint per completed sample containing the sample ID,
run-spec hash, prompt version, latency, provider metadata, parsed response, and
scoring row. Resume only when the run specification and corpus fingerprint
match exactly. Configuration mismatch, duplicate sample output, or corrupted
checkpoint must fail closed.

### 2.4 Comparison reporting

Aggregate existing quality and safety metrics plus:

- provider failures and timeout rate;
- median and p95 latency;
- input/output tokens when the provider reports them;
- throughput and schema-repair rate;
- model hash, hardware snapshot, and run completeness.

Add a comparison command that reads completed run artifacts and produces JSON
and Markdown scorecards without selecting or declaring a winner automatically.

### Workstream 2 acceptance gates

- Fake Ollama and OpenAI-compatible providers pass identical contract tests.
- A stopped development run resumes without rerunning completed samples.
- Resume refuses changed model/config/corpus fingerprints.
- Development mode cannot include or read holdout fixtures.
- Official mode continues to refuse an incomplete, unreviewed, or unlocked
  benchmark.
- Run artifacts cannot write into protected benchmark truth directories.

## Workstream 3: Scenario-grounding workflow

### 3.1 Candidate-evidence registry

Add a schema and registry for candidate evidence with:

- candidate ID and scenario ID;
- publisher, authority, direct locator, publication/effective/observed times;
- retained raw reference and SHA-256 hash;
- explicit `supported_claims` values;
- exact supporting excerpt or structured payload path;
- discovery, captured, verified, reviewed, rejected, or escalated state.

Registration does not alter a scenario or certify a claim.

### 3.2 Deterministic evidence verifier

Verify that:

- the retained body and hash exist and the quoted span occurs in the source;
- publication/effective time is eligible for the scenario evaluation time;
- the source is a direct primary record, not a search-results page;
- operational claims have `port_operations`, `carrier_service`, or the exact
  required event type;
- weather-only evidence cannot satisfy port-operation or carrier-service
  support;
- duplicate or contradictory candidates are surfaced for review rather than
  resolved by first match.

### 3.3 Review and attachment workflow

Generate a review packet from the candidate registry. A separate dry-run-first
attachment command may attach only a verified, human-approved candidate to an
open dev or selection scenario. It must preserve existing evidence and expected
truth. For sealed holdout scenarios, generate a release-manager patch proposal
without reading or changing sealed content unless holdout authorization is
present.

### 3.4 Queue and validator integration

Enhance `scenario_grounding_queue.py` to show candidate state, missing claims,
temporal failures, and the next required action. Strict corpus validation must
consume the same verifier so the queue and release gate cannot disagree.

### Workstream 3 acceptance gates

- Direct primary evidence with a valid span, date, hash, and supported claim is
  accepted as a candidate.
- Search pages, missing spans, future-dated evidence, hash mismatches, and
  weather-only port claims fail closed.
- Conflicting sources create an explicit review state.
- Open-scenario attachments are auditable and do not rewrite expectations.
- Sealed holdout scenarios remain unchanged without explicit authorization.

## Implementation order

1. Add shared schemas, audit-record utilities, and fail-closed filesystem
   transactions used by all three workstreams.
2. Deliver review generation, decision application, and manifest reconciliation.
3. Deliver the candidate-evidence registry and deterministic verifier.
4. Integrate grounding packets and safe open-scenario attachment.
5. Add versioned bakeoff run specifications and provider preflight.
6. Add checkpoint/resume and comparison reporting.
7. Run the full regression suite, add end-to-end tests across the three
   workflows, and update the bakeoff-readiness report.

## Definition of done

Items 1–3 are complete when a reviewer can generate and safely apply a batch,
candidate scenario evidence can be verified and attached without unsupported
claims or sealed-data leakage, and two local providers can execute resumable,
reproducible development runs with comparable reports. Official bakeoff status
must remain blocked until the independent corpus release gates are satisfied.
