# Antigravity first-pass remediation record

Date: 2026-09-07

The Antigravity first-pass run exceeded its assigned Stages 0–2 scope. It added
collection artifacts, synthetic quota fixtures, deterministic-engine modules,
E2E replay code, generated reports, and a local holdout directory. These
artifacts are preserved for review, but are **not approved benchmark inputs**.

## Trust status

The benchmark remains `scaffold_unlocked`, label review remains incomplete, the
corpus is below the required 420 fixtures, and strict validation fails. No
result generated from these artifacts may be described as a benchmark result,
model comparison, or readiness decision.

The atomic fixtures in `raw/synthetic-quota/` and matching `ATOM-SYN-*`
manifests are authored synthetic data. They may be useful for safety testing,
but they do not substitute for the required adjudicated real-source corpus.
The newly generated E2E reports and files in `runs/` are development artifacts,
not evidence that the E2E benchmark has passed.

## Holdout boundary

`holdout_sealed/` is a workflow guardrail, not access control: it is readable
to anyone with repository access and the environment-variable gate can be
bypassed. Before any official evaluation, move holdout raw data and labels to
a separately permissioned evaluation environment and record the authorization
procedure in the release record.

## Review disposition

Retain the generated work until a human selects specific artifacts for adoption.
Do not freeze, publish, score, or tune against it. Future cleanup should be
recoverable (move to an external review archive), because this workspace is not
a Git repository and an automatic revert is unavailable.
