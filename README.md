# Rock Supply Intelligence

Local-model-first supply-chain disruption intelligence for a Taiwan→U.S. importer shadow POC.

The system may ingest, normalize, correlate, calculate, summarize, and recommend. It must not autonomously reroute freight, place orders, write to NetSuite or Salesforce, or send customer communications.

## Current stage

Benchmark construction and validation. The 420-sample atomic corpus is **not** complete. Canonical contracts exist; the intelligence engine and dashboard do not.

## Layout

- `Rock_Supply_Intelligence_Canonical_Data_Contract_v0_1.docx` — canonical record contract
- `rock_supply_intelligence_benchmark/` — frozen-later evaluation assets
- `rock_supply_intelligence/` — typed Python package (schemas, provider interface, bakeoff harness)
- `rock_supply_intelligence/tracking/` — observation-only vessel tracking contracts, replay, geofences, and provenance storage
- `SHIP-TRACKING.md` — ship-tracking safety boundary and live-provider gate
- `tests/` — deterministic unit tests

## Commands

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 rock_supply_intelligence_benchmark/tools/validate_scaffold.py
python3 rock_supply_intelligence_benchmark/tools/validate_corpus.py
python3 rock_supply_intelligence_benchmark/tools/run_e2e.py
python3 rock_supply_intelligence_benchmark/tools/freeze_hash.py verify
python3 rock_supply_intelligence_benchmark/tools/run_atomic_bakeoff.py --provider ollama --model llama3.1:8b
# Holdout (authorized evaluation only):
RSI_HOLDOUT_EVAL=1 python3 rock_supply_intelligence_benchmark/tools/run_e2e.py --allow-holdout
RSI_HOLDOUT_EVAL=1 python3 rock_supply_intelligence_benchmark/tools/run_atomic_bakeoff.py --provider ollama --model llama3.1:8b --allow-holdout
```

The atomic corpus is not frozen and is not 420/420. Cloud comparison is prohibited until a frozen local bakeoff exists.

`rock_supply_intelligence_benchmark/holdout_sealed/` is only a local workflow
guardrail, not real access control. Official holdout evaluation requires a
separately permissioned environment; see `rock_supply_intelligence_benchmark/ANTIGRAVITY_REMEDIATION.md`.
