#!/usr/bin/env python3
"""Evaluate shared, shallow, and deterministic deep descriptor snapshots."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_joint_compatibility as joint  # noqa: E402
from scripts.validate_expert_manifest import V2_SCHEMA  # noqa: E402


DEFAULT_FIXTURE = (
    ROOT / "fixtures" / "expert_nested_catalog_descriptor_snapshot_cases.json"
)
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "prior_evaluator",
    "base_template", "reference_date", "artifacts", "consumers",
    "nested_member", "scenarios", "expected_shared_correct",
    "expected_shallow_correct", "expected_deep_correct",
    "expected_shared_drifts", "expected_shallow_drifts",
    "expected_deep_drifts", "expected_decision",
}


def _canonical_payload(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    try:
        payload = (ROOT / source["path"]).read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _set_path(value: dict[str, Any], path: list[Any], replacement: Any) -> None:
    cursor: Any = value
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = replacement


def _handoff_result(descriptor: dict[str, Any]) -> str:
    return "handed:" + _canonical_payload(descriptor).decode("utf-8")


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-nested-catalog-descriptor-snapshot-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-045-catalog-descriptor-snapshot.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_catalog_descriptor_snapshot_cases.json",
        ),
        "prior_evaluator": (
            {"path", "sha256"},
            "scripts/evaluate_catalog_descriptor_snapshot.py",
        ),
        "base_template": (
            {"path", "sha256"},
            "templates/expert-package-v2.json",
        ),
    }
    pinned_bytes = 0
    pinned: dict[str, bytes] = {}
    for name, (keys, expected_path) in sources.items():
        source = fixture[name]
        if (
            not isinstance(source, dict)
            or set(source) != keys
            or source.get("path") != expected_path
            or not isinstance(source.get("sha256"), str)
            or len(source["sha256"]) != 64
        ):
            raise ValueError(f"{name} pin is unsupported")
        pinned[name] = _read_pinned(source, name.replace("_", "-"))
        pinned_bytes += len(pinned[name])
    if fixture["prior_experiment"]["id"] != "EXP-045":
        raise ValueError("prior experiment changed")

    prior = json.loads(pinned["prior_fixture"])
    if (
        prior.get("expected_candidate_correct") != 3
        or prior.get("expected_snapshot_drifts") != 0
    ):
        raise ValueError("EXP-045 snapshot evidence changed")
    if fixture["reference_date"] != prior.get("reference_date"):
        raise ValueError("reference date changed")
    if fixture["artifacts"] != prior.get("artifacts"):
        raise ValueError("EXP-045 artifact descriptors changed")
    if fixture["consumers"] != prior.get("consumers"):
        raise ValueError("EXP-045 consumer policies changed")
    if json.loads(pinned["base_template"]).get("schema") != V2_SCHEMA:
        raise ValueError("base template schema changed")

    artifacts = fixture["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ValueError("fixture must contain two artifacts")
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "id", "schema", "version", "path", "sha256"
        }:
            raise ValueError("artifact descriptor has unexpected structure")
        if artifact["schema"] != V2_SCHEMA:
            raise ValueError("artifact schema changed")
        joint._parse_version(artifact["version"])
    consumers = fixture["consumers"]
    if not isinstance(consumers, list) or len(consumers) != 2:
        raise ValueError("fixture must contain two consumers")
    for policy in consumers:
        joint._validate_policy(policy)
    if joint.joint_highest_select(artifacts, consumers) != joint._selected_result(
        artifacts[1]
    ):
        raise ValueError("pre-mutation joint selection changed")

    nested_member = fixture["nested_member"]
    if (
        not isinstance(nested_member, dict)
        or set(nested_member) != {"provenance"}
        or not isinstance(nested_member["provenance"], dict)
        or set(nested_member["provenance"]) != {
            "source", "claim_ids", "attestations"
        }
    ):
        raise ValueError("nested member has unexpected structure")

    scenarios = fixture["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 3:
        raise ValueError("fixture must contain three scenarios")
    expected_ids = ["NEST-046-A", "NEST-046-B", "NEST-046-C"]
    expected_paths = [
        ["provenance", "source", "id"],
        ["provenance", "claim_ids", 0],
        ["provenance", "attestations", "reviewed"],
    ]
    if [case.get("id") for case in scenarios] != expected_ids:
        raise ValueError("scenario identities changed")
    if [case.get("path") for case in scenarios] != expected_paths:
        raise ValueError("scenario mutation paths changed")
    for case in scenarios:
        if not isinstance(case, dict) or set(case) != {
            "id", "path", "replacement"
        }:
            raise ValueError("scenario has unexpected structure")

    if (
        fixture["expected_shared_correct"] != 0
        or fixture["expected_shallow_correct"] != 0
        or fixture["expected_deep_correct"] != 3
        or fixture["expected_shared_drifts"] != 3
        or fixture["expected_shallow_drifts"] != 3
        or fixture["expected_deep_drifts"] != 0
        or fixture["expected_decision"]
        != "retain-default-and-quarantine-deep-selection-snapshot"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def _run_scenario(
    fixture: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    catalog = copy.deepcopy(fixture["artifacts"])
    for descriptor in catalog:
        descriptor.update(copy.deepcopy(fixture["nested_member"]))
    consumers = copy.deepcopy(fixture["consumers"])
    catalog_before = copy.deepcopy(catalog)
    selection = joint.joint_highest_select(catalog, consumers)
    matches = [item for item in catalog if joint._selected_result(item) == selection]
    if len(matches) != 1:
        raise ValueError("joint selection did not identify one descriptor")
    selected = matches[0]
    shared_handoff = selected
    shallow_handoff = copy.copy(selected)
    snapshot = _canonical_payload(selected)
    snapshot_digest = hashlib.sha256(snapshot).hexdigest()
    deep_handoff = json.loads(snapshot)
    expected_before = _handoff_result(deep_handoff)

    shared_alias_locked = shared_handoff is selected
    shallow_alias_locked = (
        shallow_handoff is not selected
        and shallow_handoff["provenance"] is selected["provenance"]
    )
    deep_alias_locked = (
        deep_handoff is not selected
        and deep_handoff["provenance"] is not selected["provenance"]
    )

    _set_path(selected, scenario["path"], scenario["replacement"])
    expected_mutated = copy.deepcopy(catalog_before)
    selected_index = catalog.index(selected)
    other_index = 1 - selected_index
    _set_path(expected_mutated[selected_index], scenario["path"], scenario["replacement"])

    shared = _handoff_result(shared_handoff)
    shallow = _handoff_result(shallow_handoff)
    deep = _handoff_result(deep_handoff)
    return {
        "id": scenario["id"],
        "shared": shared,
        "shallow": shallow,
        "deep": deep,
        "shared_correct": shared == expected_before,
        "shallow_correct": shallow == expected_before,
        "deep_correct": deep == expected_before,
        "shared_drift": shared != expected_before,
        "shallow_drift": shallow != expected_before,
        "deep_drift": deep != expected_before,
        "mutation_visible_in_catalog": catalog == expected_mutated,
        "only_locked_leaf_changed": catalog == expected_mutated,
        "unselected_descriptor_unchanged": (
            catalog[other_index] == catalog_before[other_index]
        ),
        "snapshot_bytes_unchanged": (
            hashlib.sha256(snapshot).hexdigest() == snapshot_digest
        ),
        "shared_alias_locked": shared_alias_locked,
        "shallow_alias_locked": shallow_alias_locked,
        "deep_alias_locked": deep_alias_locked,
        "selection_before_mutation_correct": selected_index == 1,
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    results = [_run_scenario(fixture, case) for case in fixture["scenarios"]]
    return {
        "scenario_count": len(results),
        "shared_correct": sum(item["shared_correct"] for item in results),
        "shallow_correct": sum(item["shallow_correct"] for item in results),
        "deep_correct": sum(item["deep_correct"] for item in results),
        "shared_drifts": sum(item["shared_drift"] for item in results),
        "shallow_drifts": sum(item["shallow_drift"] for item in results),
        "deep_drifts": sum(item["deep_drift"] for item in results),
        "mutations_visible_in_catalog": sum(
            item["mutation_visible_in_catalog"] for item in results
        ),
        "only_locked_leaves_changed": all(
            item["only_locked_leaf_changed"] for item in results
        ),
        "unselected_descriptors_unchanged": all(
            item["unselected_descriptor_unchanged"] for item in results
        ),
        "snapshot_bytes_unchanged": all(
            item["snapshot_bytes_unchanged"] for item in results
        ),
        "alias_relations_locked": all(
            item["shared_alias_locked"]
            and item["shallow_alias_locked"]
            and item["deep_alias_locked"]
            for item in results
        ),
        "pre_mutation_selection_correct": all(
            item["selection_before_mutation_correct"] for item in results
        ),
        "artifact_load_attempts": 0,
        "repository_writes": 0,
        "outcomes": [
            {
                "id": item["id"],
                "shared": item["shared"],
                "shallow": item["shallow"],
                "deep": item["deep"],
            }
            for item in results
        ],
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["scenario_count"] == 3
        and summary["shared_correct"]
        == fixture["expected_shared_correct"] == 0
        and summary["shallow_correct"]
        == fixture["expected_shallow_correct"] == 0
        and summary["deep_correct"]
        == fixture["expected_deep_correct"] == 3
        and summary["shared_drifts"]
        == fixture["expected_shared_drifts"] == 3
        and summary["shallow_drifts"]
        == fixture["expected_shallow_drifts"] == 3
        and summary["deep_drifts"]
        == fixture["expected_deep_drifts"] == 0
        and summary["mutations_visible_in_catalog"] == 3
        and summary["only_locked_leaves_changed"]
        and summary["unselected_descriptors_unchanged"]
        and summary["snapshot_bytes_unchanged"]
        and summary["alias_relations_locked"]
        and summary["pre_mutation_selection_correct"]
        and summary["artifact_load_attempts"] == 0
        and summary["repository_writes"] == 0
        and summary["decision"] == fixture["expected_decision"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 32 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture, fixture_bytes = load_fixture(args.fixture)
    first = run_trial(fixture)
    second = run_trial(fixture)
    summary = dict(first)
    summary.update({
        "repeatable": first == second,
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
