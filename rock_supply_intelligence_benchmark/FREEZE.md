# Freeze specification

The freeze unit is the content tree below this directory, excluding generated `reports/`, caches, `manifest.json` (which records the result), and the hash tool itself. Every included file receives a SHA-256 hash. The root hash is SHA-256 of the canonical JSON object mapping relative POSIX paths to those hashes.

Atomic evidence hashes apply to the exact retained source bytes, not a rendered page or a paraphrase. A `null` content hash means no source material has been captured; it is never a substitute for a hash. Source manifests must separately record the source locator, source type, language, provenance, retrieval/publication/observation timestamps, raw reference, license, and split.

Before release, `tools/validate_corpus.py --strict-quotas` must pass, expected labels must have `label_review.state=complete` with a reviewed count of 420, then `tools/freeze_hash.py freeze` records the tree hash. `tools/freeze_hash.py lock` sets `status=locked` and a real RFC 3339 `locked_at`. Generated `runs/` and `reports/` are excluded from the freeze tree. A locked content mismatch or any mutation of frozen inputs requires a new benchmark version, not an in-place edit. Unlocked or incomplete corpora are `NOT_RELEASE_READY` and must not be treated as official bakeoff truth.
