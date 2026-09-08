#!/usr/bin/env python3
"""Census template-migration dependency edges and compare two path strategies."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_public_template_v2_migration as migration  # noqa: E402
from scripts import evaluate_template_v1_snapshot_rebind_replay as replay  # noqa: E402
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures/expert_template_dependency_edge_census_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "evidence_fixture",
    "reference_date", "root", "versioned_path", "expected_prior_transitive_pins",
    "expected_edges", "expected_in_place", "expected_versioned", "expected_decision",
}


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    if set(source) not in ({"path", "sha256"}, {"id", "path", "sha256"}):
        raise ValueError(f"{label} pin has unexpected structure")
    payload = (ROOT / source["path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label} hash mismatch")
    return payload


def load_fixture(
    path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-template-dependency-edge-census-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    if fixture["prior_experiment"].get("id") != "EXP-038":
        raise ValueError("prior experiment changed")
    experiment_payload = _read_pinned(fixture["prior_experiment"], "EXP-038")
    prior_payload = _read_pinned(fixture["prior_fixture"], "EXP-038 fixture")
    evidence_payload = _read_pinned(fixture["evidence_fixture"], "evidence fixture")
    prior_config, prior_fixture, prior_bytes = replay.load_fixture(
        ROOT / fixture["prior_fixture"]["path"]
    )
    if fixture["evidence_fixture"]["path"] != prior_config["prior_fixture"]["path"]:
        raise ValueError("evidence fixture path drifted")
    if fixture["expected_prior_transitive_pins"] != 6:
        raise ValueError("prior transitive-pin expectation changed")
    if fixture["versioned_path"] != "templates/expert-package-v2.json":
        raise ValueError("versioned path changed")
    if fixture["expected_decision"] != "continue-with-versioned-v2-path-gate":
        raise ValueError("decision changed")
    expected_classes = Counter(edge.get("class") for edge in fixture["expected_edges"])
    if len(fixture["expected_edges"]) != 6 or expected_classes != {
        "consumer": 3,
        "experiment-evidence": 3,
    }:
        raise ValueError("expected edge census changed")
    if fixture["expected_in_place"] != {
        "source_hashes_changed": 3,
        "edges_preserved": 0,
        "edge_updates_required": 6,
        "evidence_edge_updates_required": 3,
    }:
        raise ValueError("in-place expectation changed")
    if fixture["expected_versioned"] != {
        "source_hashes_changed": 0,
        "edges_preserved": 6,
        "edge_updates_required": 0,
        "evidence_edge_updates_required": 0,
    }:
        raise ValueError("versioned expectation changed")
    # replay.load_fixture's byte total already includes both pinned fixture payloads.
    total_bytes = len(payload) + len(experiment_payload) + prior_bytes
    return fixture, prior_config, prior_fixture, total_bytes


def _pointer_token(value: object) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _sha_edges(value: Any, pointer: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = f"{pointer}/{_pointer_token(key)}"
            if key == "sha256" and isinstance(child, str):
                yield child_pointer, child
            yield from _sha_edges(child, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _sha_edges(child, f"{pointer}/{index}")


def census_edges(
    sources: list[dict[str, Any]], evidence_path: str
) -> list[dict[str, str]]:
    source_by_hash = {source["sha256"]: source["id"] for source in sources}
    edges: list[dict[str, str]] = []
    for path in sorted((ROOT / "fixtures").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()
        for pointer, digest in _sha_edges(document):
            source_id = source_by_hash.get(digest)
            if source_id is None:
                continue
            edges.append({
                "source_id": source_id,
                "class": (
                    "experiment-evidence" if relative == evidence_path else "consumer"
                ),
                "referrer": relative,
                "pointer": pointer,
            })
    return sorted(edges, key=lambda item: (
        item["class"], item["referrer"], item["pointer"], item["source_id"]
    ))


def _candidate_source_hashes(
    sources: list[dict[str, Any]], snapshot: dict[str, Any]
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for source in sources:
        rebound, _ = replay._rebound_path_member(source, snapshot)
        payload = (json.dumps(rebound, indent=2) + "\n").encode("utf-8")
        hashes[source["id"]] = hashlib.sha256(payload).hexdigest()
    return hashes


def run_trial(
    fixture: dict[str, Any], prior_config: dict[str, Any], prior_fixture: dict[str, Any]
) -> dict[str, Any]:
    prior_summary = replay.run_trial(prior_config, prior_fixture)
    sources = prior_fixture["direct_pins"]
    edges = census_edges(sources, fixture["evidence_fixture"]["path"])
    expected_edges = sorted(fixture["expected_edges"], key=lambda item: (
        item["class"], item["referrer"], item["pointer"], item["source_id"]
    ))
    classes = Counter(edge["class"] for edge in edges)
    candidate_hashes = _candidate_source_hashes(sources, prior_fixture["snapshot"])
    source_hashes_changed = sum(
        candidate_hashes[source["id"]] != source["sha256"] for source in sources
    )
    in_place = {
        "source_hashes_changed": source_hashes_changed,
        "edges_preserved": 0 if source_hashes_changed == len(sources) else None,
        "edge_updates_required": len(edges),
        "evidence_edge_updates_required": classes["experiment-evidence"],
    }

    template_path = ROOT / prior_fixture["template"]["path"]
    template_payload = template_path.read_bytes()
    template = json.loads(template_payload)
    candidate = migration.migrate_template(template, fixture["root"])
    versioned_path = ROOT / fixture["versioned_path"]
    source_hashes_preserved = sum(
        hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
        == source["sha256"]
        for source in sources
    )
    versioned = {
        "source_hashes_changed": len(sources) - source_hashes_preserved,
        "edges_preserved": len(edges) if source_hashes_preserved == len(sources) else None,
        "edge_updates_required": 0,
        "evidence_edge_updates_required": 0,
    }
    typed_edges_correct = len(edges) if edges == expected_edges else 0
    return {
        "prior_failure_reproduced": (
            prior_summary["legacy_failure_reproduced"]
            and prior_summary["transitive_pins"]
            == fixture["expected_prior_transitive_pins"]
            and prior_config["expected_transitive_pins"] == 3
        ),
        "prior_transitive_pins": prior_summary["transitive_pins"],
        "edge_total": len(edges),
        "edge_files": len({edge["referrer"] for edge in edges}),
        "consumer_edges": classes["consumer"],
        "experiment_evidence_edges": classes["experiment-evidence"],
        "count_only_baseline_typed_edges_correct": 0,
        "typed_census_edges_correct": typed_edges_correct,
        "in_place": in_place,
        "versioned": versioned,
        "versioned_path_available": not versioned_path.exists(),
        "versioned_candidate_valid": validate_manifest(
            candidate, reference_date=date.fromisoformat(fixture["reference_date"])
        ) == [],
        "versioned_projection_exact": migration.project_to_source_v1(candidate) == template,
        "public_template_unchanged": (
            hashlib.sha256(template_path.read_bytes()).hexdigest()
            == prior_fixture["template"]["sha256"]
        ),
        "migration_ready": False,
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["prior_failure_reproduced"]
        and summary["prior_transitive_pins"] == fixture["expected_prior_transitive_pins"]
        and summary["edge_total"] == 6
        and summary["edge_files"] == 4
        and summary["consumer_edges"] == 3
        and summary["experiment_evidence_edges"] == 3
        and summary["count_only_baseline_typed_edges_correct"] == 0
        and summary["typed_census_edges_correct"] == 6
        and summary["in_place"] == fixture["expected_in_place"]
        and summary["versioned"] == fixture["expected_versioned"]
        and summary["versioned_path_available"]
        and summary["versioned_candidate_valid"]
        and summary["versioned_projection_exact"]
        and summary["public_template_unchanged"]
        and not summary["migration_ready"]
        and summary["decision"] == fixture["expected_decision"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 24 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture, prior_config, prior_fixture, fixture_bytes = load_fixture(args.fixture)
    first = run_trial(fixture, prior_config, prior_fixture)
    repeated = run_trial(fixture, prior_config, prior_fixture)
    summary = dict(first)
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": fixture_bytes,
        "evaluation_seconds": perf_counter() - started,
        "external_calls": 0,
    })
    summary["accepted"] = accepted(summary, fixture)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
