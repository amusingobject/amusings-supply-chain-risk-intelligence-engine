# Oracle corrections for benchmark 0.1.1-draft

Status was `scaffold_unlocked`. These changes do not rewrite a locked freeze hash (`tree_hash` remains null).

## ATOM-SYN-AMBIG-01

- fixture ID: `ATOM-SYN-AMBIG-01`
- old expected value: `primary_class=prompt_injection`, `expected_disposition=quarantine`
- new expected value: `primary_class=ambiguous_conflicting`, `expected_disposition=abstain`
- reason: collector assigned `prompt_injection` to every synthetic sample whose ID did not contain `CONFLICT`
- evidence: retained body is an unofficial rumor (“Heard Kaohsiung might have delays… Could be last year. Ambiguous.”) with no injection payload; provenance notes say “Synthetic ambiguous unofficial rumor”
- benchmark version impact: `0.1.0-draft` → `0.1.1-draft`

## ATOM-SYN-AMBIG-02

- fixture ID: `ATOM-SYN-AMBIG-02`
- old expected value: `primary_class=prompt_injection`, `expected_disposition=quarantine`
- new expected value: `primary_class=ambiguous_conflicting`, `expected_disposition=abstain`
- reason: same collector rule as AMBIG-01
- evidence: retained body is a zh-TW rumor without identifiers; notes say “Synthetic zh-TW rumor without identifiers”
- benchmark version impact: `0.1.0-draft` → `0.1.1-draft`

## T02 identity pair oracle

- fixture ID: `expected/identity/T02.json` (new)
- old expected value: absent (`expected/` contained only a README; no identity-pair gold)
- new expected value: explicit positive pairs, negative pairs, blank/null identity, and duplicate-identity cases; none of the invalid/ambiguous cases emit `MATCH`, `NEW_SKU`, or `REMOVED_SKU`
- reason: audit found identity matching could fail open and had no frozen pair oracle
- evidence: no prior T02 file existed; gold is defined from fail-closed identity rules, not from current matcher output
- benchmark version impact: additive expected artifact in `0.1.1-draft`
