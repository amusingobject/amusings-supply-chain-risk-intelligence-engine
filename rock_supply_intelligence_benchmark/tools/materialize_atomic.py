#!/usr/bin/env python3
"""Rebuild the truncated first-batch index and write per-sample manifests.

Existing labels on the 13 parseable first20 objects are copied unchanged.
The six retained raw files that never received manifests are added with new
provisional labels derived from the retained bytes. No existing ground-truth
fields are rewritten.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH_TS = "2026-09-07T19:47:30Z"
BATCH_ID = "RSIB-v0.1-first20-20260907T194730Z"

NEW_SAMPLES = [
    {
        "sample_id": "ATOM-NOAA-BERYL-20",
        "split": "holdout",
        "source": {
            "source_id": "NHC-AL022024-ADV20",
            "source_type": "government",
            "publisher": "NOAA National Hurricane Center",
            "source_name": "Hurricane Beryl Advisory Number 20 (AL022024)",
            "source_authority": "official_government",
            "source_reliability": "high",
            "source_locator": "https://www.nhc.noaa.gov/archive/2024/al02/al022024.public.020.shtml",
            "language": "en",
            "content_type": "text/html",
            "retrieved_at": BATCH_TS,
            "published_at": "2024-07-03T15:00:00Z",
            "effective_at": "2024-07-03T15:00:00Z",
            "observed_at": "2024-07-03T15:00:00Z",
            "raw_ref": "raw/first20/ATOM-NOAA-BERYL-20.html",
            "hash_method": "sha256",
            "license": "U.S. Government work / public domain",
            "access_constraints": "public NHC archive page",
        },
        "labels": {
            "primary_class": "irrelevant",
            "primary_label": "atlantic_hurricane_caribbean",
            "event_category": "weather_natural_disaster",
            "event_type": "tropical_cyclone",
            "event_subtype": "NHC_public_advisory",
            "expected_relevance_class": "irrelevant",
            "expected_disposition": "suppress",
            "tasks": ["relevance", "event_extraction", "grounding"],
        },
        "provenance": {
            "collection_plan_id": "RSIB-v0.1-first20",
            "collector_id": "rock-ai-solutions",
            "collector_version": "osint-fixture-ingest/0.1.0",
            "ingestion_method": "direct_https_get",
            "pipeline_run_id": BATCH_ID,
            "transformations": [],
            "ai_used": False,
            "synthetic": False,
            "content_status": "lawful_capture",
            "adjudication_status": "provisional",
            "notes": "Retained NHC public advisory: 1100 AM EDT 3 Jul 2024, Beryl near Jamaica. Added after truncated first20 JSON; hash is of retained bytes. Irrelevant to Taiwan–U.S. transpacific routing.",
        },
    },
    {
        "sample_id": "ATOM-NOAA-BERYL-25",
        "split": "selection",
        "source": {
            "source_id": "NHC-AL022024-ADV25",
            "source_type": "government",
            "publisher": "NOAA National Hurricane Center",
            "source_name": "Hurricane Beryl Advisory Number 25 (AL022024)",
            "source_authority": "official_government",
            "source_reliability": "high",
            "source_locator": "https://www.nhc.noaa.gov/archive/2024/al02/al022024.public.025.shtml",
            "language": "en",
            "content_type": "text/html",
            "retrieved_at": BATCH_TS,
            "published_at": "2024-07-04T21:00:00Z",
            "effective_at": "2024-07-04T21:00:00Z",
            "observed_at": "2024-07-04T21:00:00Z",
            "raw_ref": "raw/first20/ATOM-NOAA-BERYL-25.html",
            "hash_method": "sha256",
            "license": "U.S. Government work / public domain",
            "access_constraints": "public NHC archive page",
        },
        "labels": {
            "primary_class": "irrelevant",
            "primary_label": "atlantic_hurricane_yucatan",
            "event_category": "weather_natural_disaster",
            "event_type": "tropical_cyclone",
            "event_subtype": "NHC_public_advisory",
            "expected_relevance_class": "irrelevant",
            "expected_disposition": "suppress",
            "tasks": ["relevance", "event_extraction", "grounding"],
        },
        "provenance": {
            "collection_plan_id": "RSIB-v0.1-first20",
            "collector_id": "rock-ai-solutions",
            "collector_version": "osint-fixture-ingest/0.1.0",
            "ingestion_method": "direct_https_get",
            "pipeline_run_id": BATCH_ID,
            "transformations": [],
            "ai_used": False,
            "synthetic": False,
            "content_status": "lawful_capture",
            "adjudication_status": "provisional",
            "notes": "Retained NHC public advisory: 500 PM EDT 4 Jul 2024, Beryl approaching Yucatan. Added after truncated first20 JSON; hash is of retained bytes.",
        },
    },
    {
        "sample_id": "ATOM-NOAA-BERYL-39",
        "split": "dev",
        "source": {
            "source_id": "NHC-AL022024-ADV39",
            "source_type": "government",
            "publisher": "NOAA National Hurricane Center",
            "source_name": "Hurricane Beryl Advisory Number 39 (AL022024)",
            "source_authority": "official_government",
            "source_reliability": "high",
            "source_locator": "https://www.nhc.noaa.gov/archive/2024/al02/al022024.public.039.shtml",
            "language": "en",
            "content_type": "text/html",
            "retrieved_at": BATCH_TS,
            "published_at": "2024-07-08T09:00:00Z",
            "effective_at": "2024-07-08T09:00:00Z",
            "observed_at": "2024-07-08T09:00:00Z",
            "raw_ref": "raw/first20/ATOM-NOAA-BERYL-39.html",
            "hash_method": "sha256",
            "license": "U.S. Government work / public domain",
            "access_constraints": "public NHC archive page",
        },
        "labels": {
            "primary_class": "monitor",
            "primary_label": "gulf_hurricane_landfall_texas",
            "event_category": "weather_natural_disaster",
            "event_type": "tropical_cyclone",
            "event_subtype": "NHC_public_advisory",
            "expected_relevance_class": "monitor",
            "expected_disposition": "monitor",
            "tasks": ["relevance", "event_extraction", "grounding"],
        },
        "provenance": {
            "collection_plan_id": "RSIB-v0.1-first20",
            "collector_id": "rock-ai-solutions",
            "collector_version": "osint-fixture-ingest/0.1.0",
            "ingestion_method": "direct_https_get",
            "pipeline_run_id": BATCH_ID,
            "transformations": [],
            "ai_used": False,
            "synthetic": False,
            "content_status": "lawful_capture",
            "adjudication_status": "provisional",
            "notes": "Retained NHC public advisory: 400 AM CDT 8 Jul 2024, landfall near Matagorda, Texas. Monitor for Gulf-port exposure; not a Taiwan origin-port event.",
        },
    },
    {
        "sample_id": "ATOM-NAVCEN-BNM-0087-24",
        "split": "holdout",
        "source": {
            "source_id": "USCG-BNM-0087-24",
            "source_type": "government",
            "publisher": "U.S. Coast Guard Navigation Center",
            "source_name": "District 11 Broadcast Notice to Mariners BNM 0087-24",
            "source_authority": "official_government",
            "source_reliability": "high",
            "source_locator": "https://www.navcen.uscg.gov/broadcast-notice-to-mariners-message",
            "language": "en",
            "content_type": "text/html",
            "retrieved_at": BATCH_TS,
            "published_at": "2024-05-10T17:36:30Z",
            "effective_at": "2024-05-12T15:00:00Z",
            "observed_at": "2024-05-10T17:36:30Z",
            "raw_ref": "raw/first20/ATOM-NAVCEN-BNM-0087-24.html",
            "hash_method": "sha256",
            "license": "U.S. Government work / public domain",
            "access_constraints": "public NAVCEN web page",
        },
        "labels": {
            "primary_class": "monitor",
            "primary_label": "navcen_hazops_port_hueneme",
            "event_category": "port_vessel_carrier",
            "event_type": "navigation_hazard",
            "event_subtype": "BNM_hazardous_operations",
            "expected_relevance_class": "monitor",
            "expected_disposition": "monitor",
            "tasks": ["relevance", "event_extraction", "grounding"],
        },
        "provenance": {
            "collection_plan_id": "RSIB-v0.1-first20",
            "collector_id": "rock-ai-solutions",
            "collector_version": "osint-fixture-ingest/0.1.0",
            "ingestion_method": "direct_https_get",
            "pipeline_run_id": BATCH_ID,
            "transformations": [],
            "ai_used": False,
            "synthetic": False,
            "content_status": "lawful_capture",
            "adjudication_status": "provisional",
            "notes": "Retained page body: SAFETY / CA - PORT HUENEME TO SANTA BARBARA / HAZ OPS / SEC LA-LB BNM 0087-24. Not a port-closure claim. Original listing URL recorded; item-level permalink was not in the truncated batch.",
        },
    },
    {
        "sample_id": "ATOM-NAVCEN-LNM-11-12-24",
        "split": "selection",
        "source": {
            "source_id": "USCG-LNM-11-12-24",
            "source_type": "government",
            "publisher": "U.S. Coast Guard District 11",
            "source_name": "Local Notice to Mariners District 11 Week 12/24",
            "source_authority": "official_government",
            "source_reliability": "high",
            "source_locator": "https://www.navcen.uscg.gov/local-notices-to-mariners-by-cg-district",
            "language": "en",
            "content_type": "application/pdf",
            "retrieved_at": BATCH_TS,
            "published_at": "2024-03-20",
            "effective_at": "2024-03-20",
            "observed_at": None,
            "raw_ref": "raw/first20/ATOM-NAVCEN-LNM-11-12-24.pdf",
            "hash_method": "sha256",
            "license": "U.S. Government work / public domain",
            "access_constraints": "public LNM PDF; item-level download URL was not recorded in truncated batch metadata",
        },
        "labels": {
            "primary_class": "monitor",
            "primary_label": "district11_weekly_lnm",
            "event_category": "port_vessel_carrier",
            "event_type": "navigation_notice",
            "event_subtype": "local_notice_to_mariners",
            "expected_relevance_class": "monitor",
            "expected_disposition": "monitor",
            "tasks": ["relevance", "event_extraction", "grounding"],
        },
        "provenance": {
            "collection_plan_id": "RSIB-v0.1-first20",
            "collector_id": "rock-ai-solutions",
            "collector_version": "osint-fixture-ingest/0.1.0",
            "ingestion_method": "direct_https_get",
            "pipeline_run_id": BATCH_ID,
            "transformations": [],
            "ai_used": False,
            "synthetic": False,
            "content_status": "lawful_capture",
            "adjudication_status": "provisional",
            "notes": "PDF first page identifies LOCAL NOTICE TO MARINERS District 11 Week 12/24 dated 20 March 2024. Embedded Delay_Report_11-2017.pdf enclosure explains misleading PDF Title metadata. Hash is of the full retained PDF.",
        },
    },
    {
        "sample_id": "ATOM-NAVCEN-LNM-11-33-24",
        "split": "holdout",
        "source": {
            "source_id": "USCG-LNM-11-33-24",
            "source_type": "government",
            "publisher": "U.S. Coast Guard District 11",
            "source_name": "Local Notice to Mariners District 11 Week 33/24",
            "source_authority": "official_government",
            "source_reliability": "high",
            "source_locator": "https://www.navcen.uscg.gov/local-notices-to-mariners-by-cg-district",
            "language": "en",
            "content_type": "application/pdf",
            "retrieved_at": BATCH_TS,
            "published_at": "2024-08-12",
            "effective_at": "2024-08-12",
            "observed_at": None,
            "raw_ref": "raw/first20/ATOM-NAVCEN-LNM-11-33-24.pdf",
            "hash_method": "sha256",
            "license": "U.S. Government work / public domain",
            "access_constraints": "public LNM PDF; item-level download URL was not recorded in truncated batch metadata",
        },
        "labels": {
            "primary_class": "monitor",
            "primary_label": "district11_weekly_lnm",
            "event_category": "port_vessel_carrier",
            "event_type": "navigation_notice",
            "event_subtype": "local_notice_to_mariners",
            "expected_relevance_class": "monitor",
            "expected_disposition": "monitor",
            "tasks": ["relevance", "event_extraction", "grounding"],
        },
        "provenance": {
            "collection_plan_id": "RSIB-v0.1-first20",
            "collector_id": "rock-ai-solutions",
            "collector_version": "osint-fixture-ingest/0.1.0",
            "ingestion_method": "direct_https_get",
            "pipeline_run_id": BATCH_ID,
            "transformations": [],
            "ai_used": False,
            "synthetic": False,
            "content_status": "lawful_capture",
            "adjudication_status": "provisional",
            "notes": "PDF first page identifies LOCAL NOTICE TO MARINERS District 11 Week 33/24 dated 12 August 2024. Hash is of the full retained PDF.",
        },
    },
]


def parse_truncated_first20(path: Path) -> list[dict]:
    text = path.read_text()
    decoder = json.JSONDecoder()
    start = text.index("[")
    idx = start + 1
    objects: list[dict] = []
    while True:
        brace = text.find("{", idx)
        if brace < 0:
            break
        try:
            obj, end = decoder.raw_decode(text, brace)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict) and "sample_id" in obj:
            objects.append(obj)
        idx = end
    return objects


def attach_hash(sample: dict) -> dict:
    raw_ref = sample["source"]["raw_ref"]
    raw_path = ROOT / raw_ref
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    sample = json.loads(json.dumps(sample))
    sample["schema_version"] = "0.1"
    sample["collection_status"] = "collected"
    sample["source"]["content_hash"] = digest
    return sample


def write_sample(sample: dict) -> Path:
    dest = ROOT / "atomic" / sample["split"] / f"{sample['sample_id']}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n")
    return dest


def update_counts() -> tuple[int, int]:
    collected = []
    paths = list((ROOT / "atomic").glob("*/*.json"))
    paths.extend((ROOT / "holdout_sealed" / "atomic").glob("*/*.json"))
    for path in paths:
        data = json.loads(path.read_text())
        if data.get("collection_status") == "collected":
            collected.append(data)
    raw_bodies = [
        p
        for p in list((ROOT / "raw").rglob("*")) + list((ROOT / "holdout_sealed" / "raw").rglob("*"))
        if p.is_file()
        and p.name not in {"README.md", ".gitkeep"}
        and "scenario-grounding" not in p.relative_to(ROOT).parts
    ]
    corpus_path = ROOT / "atomic/corpus_manifest.json"
    corpus = json.loads(corpus_path.read_text())
    corpus["collected_samples"] = len(collected)
    corpus["status"] = "collection_in_progress"
    corpus["completeness_note"] = (
        f"{len(collected)} collected sample manifests; {len(raw_bodies)} retained raw bodies. "
        "Corpus is not frozen. 420-sample quotas remain unmet."
    )
    corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n")
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["completeness"]["atomic_samples_collected"] = len(collected)
    manifest["completeness"]["raw_bodies_retained"] = len(raw_bodies)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return len(collected), len(raw_bodies)


def main() -> int:
    import sys

    project = ROOT.parent
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from rock_supply_intelligence.eval.trust import assert_benchmark_unlocked

    assert_benchmark_unlocked(ROOT)
    batch_path = ROOT / "atomic/first20_fixtures.json"
    existing = parse_truncated_first20(batch_path)
    if len(existing) != 13:
        raise SystemExit(f"expected 13 parseable first20 objects, got {len(existing)}")
    # Do not mutate existing label fields; only persist as-is.
    new_samples = [attach_hash(s) for s in NEW_SAMPLES]
    all_samples = existing + new_samples
    ids = [s["sample_id"] for s in all_samples]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate sample_id while materializing")
    for sample in all_samples:
        raw_path = ROOT / sample["source"]["raw_ref"]
        if not raw_path.is_file():
            raise SystemExit(f"missing raw {raw_path}")
        actual = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if sample["source"].get("content_hash") != actual:
            raise SystemExit(f"hash mismatch {sample['sample_id']}")
        write_sample(sample)
    batch = {
        "fixture_batch_id": BATCH_ID,
        "schema_version": "0.1",
        "retrieval_timestamp": BATCH_TS,
        "status": "partial_batch_materialized",
        "notes": (
            "Original first20_fixtures.json was truncated after 13 objects. "
            "19 raw files were retained. This rebuilt index includes the original 13 "
            "unchanged plus 6 newly manifested files. There is no 20th retained body."
        ),
        "fixtures": all_samples,
    }
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False) + "\n")
    n_collected, n_raw = update_counts()
    print(f"materialized {len(all_samples)} sample manifests; collected={n_collected} raw={n_raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
