# Rock Supply Intelligence Benchmark v0.1

Frozen, replayable evaluation assets for the supply-intelligence shadow POC. It tests evidence normalization, deterministic event-to-business correlation, and constrained recommendations. It does **not** authorize operational writes.

## Status

This scaffold implements the complete fixture topology, 28 synthetic end-to-end scenario manifests, schemas, quota-based atomic corpus plan, initial gates, and freeze tooling. No copyrighted source bodies have been collected or redistributed. The atomic corpus is therefore **0 / 420 complete** and every raw-evidence reference is an explicit collection placeholder.

## Layout

`atomic/` holds one future manifest per atomic OSINT sample; `scenarios/` holds executable scenario manifests; `raw/` is immutable lawful source capture storage; `expected/` holds derived gold-label indexes; `scoring/` defines gates; `reports/` is reserved for generated evaluation reports.

## Deterministic-first execution

Deterministic services own identifiers, time/geographic joins, ETA and inventory arithmetic, severity rules, policy gates, and audit writes. A local model may only classify/extract/translate into a schema-valid candidate. Cloud inference is optional and must run the same frozen inputs. Recommendations are drafts and require human approval; no benchmark runner may make an external operational write.

## Collection and freeze workflow

1. Register a lawful source in `atomic/corpus_manifest.json` and create a sample manifest from its requested quota.
2. Store permitted source bytes in `raw/<sample_id>/`; do not store copyrighted bodies unless their license and retention terms permit it.
3. Set its `collection_status` to `collected`, record source/retrieval/publication metadata and hash the bytes.
4. Put reviewed expected labels in `expected/` (holdout labels must remain access-controlled).
5. Run `python3 tools/freeze_hash.py verify` then `python3 tools/freeze_hash.py freeze` at lock. Commit the resulting root hash and manifest only after review.

`freeze_hash.py` excludes `reports/`, Python caches, and itself from the content tree. A new benchmark version is required for any post-lock fixture, label, or scoring change.

## Validation

Run `python3 tools/validate_scaffold.py`. It validates JSON syntax, declared counts, required directory structure, scenario split counts, and that scenario IDs are unique. It deliberately does not claim atomic-source completeness.

## Licensing and temporal integrity

Each evidence record must preserve source URL/locator, license/access constraints, provenance, language, retrieval time, publication/observation time, and a SHA-256 content hash. A scenario may use only evidence known at or before its `evaluation_timestamp`. Use lawful excerpts, structured payload paths, or metadata when raw body retention is not permitted.
