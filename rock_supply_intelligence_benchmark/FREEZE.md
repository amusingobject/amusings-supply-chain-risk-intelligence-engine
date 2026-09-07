# Freeze specification

The freeze unit is the content tree below this directory, excluding generated `reports/`, caches, `manifest.json` (which records the result), and the hash tool itself. Every included file receives a SHA-256 hash. The root hash is SHA-256 of the canonical JSON object mapping relative POSIX paths to those hashes.

Atomic evidence hashes apply to the exact retained source bytes, not a rendered page or a paraphrase. A `null` content hash means no source material has been captured; it is never a substitute for a hash. Source manifests must separately record the source locator, source type, language, provenance, retrieval/publication/observation timestamps, raw reference, license, and split.

Before release, a human reviewer must run `tools/freeze_hash.py verify`, review source/label completeness, run the structural validator, record the candidate root hash in `manifest.json`, and set `status` to `locked` with a real RFC 3339 `locked_at` value. A locked content mismatch is a new benchmark version, not an in-place edit.
