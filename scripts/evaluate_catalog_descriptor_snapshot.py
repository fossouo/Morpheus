#!/usr/bin/env python3
"""Evaluate shared-reference versus immutable catalog descriptor handoff."""

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


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_catalog_descriptor_snapshot_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "prior_evaluator",
    "base_template", "reference_date", "artifacts", "consumers", "scenarios",
    "expected_baseline_correct", "expected_candidate_correct",
    "expected_shared_reference_drifts", "expected_snapshot_drifts",
    "expected_decision",
}


def _canonical_payload(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    try:
        payload = (ROOT / source["path"]).read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _handoff_result(descriptor: dict[str, Any]) -> str:
    return (
        f"handed:{descriptor['schema']}:{descriptor['version']}:"
        f"{descriptor['path']}:{descriptor['sha256']}"
    )


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-catalog-descriptor-snapshot-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-044-joint-template-pinned-materialization.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_joint_template_pinned_materialization_cases.json",
        ),
        "prior_evaluator": (
            {"path", "sha256"},
            "scripts/evaluate_joint_template_pinned_materialization.py",
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
    if fixture["prior_experiment"]["id"] != "EXP-044":
        raise ValueError("prior experiment changed")

    prior = json.loads(pinned["prior_fixture"])
    if (
        prior.get("expected_candidate_correct") != 3
        or prior.get("expected_candidate_silent_downgrades") != 0
    ):
        raise ValueError("EXP-044 materialization evidence changed")
    if fixture["reference_date"] != prior.get("reference_date"):
        raise ValueError("reference date changed")
    if fixture["artifacts"] != prior.get("artifacts"):
        raise ValueError("EXP-044 artifact descriptors changed")
    if fixture["consumers"] != prior.get("consumers"):
        raise ValueError("EXP-044 consumer policies changed")
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

    scenarios = fixture["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 3:
        raise ValueError("fixture must contain three scenarios")
    if [case.get("id") for case in scenarios] != [
        "SNAP-045-A", "SNAP-045-B", "SNAP-045-C"
    ]:
        raise ValueError("scenario identities changed")
    if [case.get("field") for case in scenarios] != ["path", "sha256", "version"]:
        raise ValueError("scenario mutation fields changed")
    for case in scenarios:
        if not isinstance(case, dict) or set(case) != {
            "id", "field", "replacement", "expected_baseline", "expected_candidate"
        }:
            raise ValueError("scenario has unexpected structure")
        if not isinstance(case["replacement"], str):
            raise ValueError("scenario replacement must be a string")

    if (
        fixture["expected_baseline_correct"] != 0
        or fixture["expected_candidate_correct"] != 3
        or fixture["expected_shared_reference_drifts"] != 3
        or fixture["expected_snapshot_drifts"] != 0
        or fixture["expected_decision"]
        != "retain-default-and-quarantine-immutable-selection-snapshot"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def _run_scenario(
    fixture: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    catalog = copy.deepcopy(fixture["artifacts"])
    consumers = copy.deepcopy(fixture["consumers"])
    catalog_before = _canonical_payload({"artifacts": catalog})
    selection = joint.joint_highest_select(catalog, consumers)
    matches = [item for item in catalog if joint._selected_result(item) == selection]
    if len(matches) != 1:
        raise ValueError("joint selection did not identify one descriptor")
    selected = matches[0]
    baseline_handoff = selected
    snapshot = _canonical_payload(selected)
    snapshot_digest = hashlib.sha256(snapshot).hexdigest()
    expected_before = scenario["expected_candidate"]

    selected[scenario["field"]] = scenario["replacement"]

    baseline = _handoff_result(baseline_handoff)
    candidate = _handoff_result(json.loads(snapshot))
    selected_index = catalog.index(selected)
    other_index = 1 - selected_index
    original_catalog = json.loads(catalog_before)["artifacts"]
    changed_fields = [
        key for key in selected
        if selected[key] != original_catalog[selected_index][key]
    ]
    return {
        "id": scenario["id"],
        "baseline": baseline,
        "candidate": candidate,
        "baseline_matches_locked": baseline == scenario["expected_baseline"],
        "baseline_correct": baseline == expected_before,
        "candidate_correct": candidate == expected_before,
        "shared_reference_drift": baseline != expected_before,
        "snapshot_drift": candidate != expected_before,
        "mutation_visible_in_catalog": (
            catalog[selected_index][scenario["field"]] == scenario["replacement"]
        ),
        "only_locked_field_changed": changed_fields == [scenario["field"]],
        "unselected_descriptor_unchanged": (
            catalog[other_index] == original_catalog[other_index]
        ),
        "snapshot_bytes_unchanged": (
            hashlib.sha256(snapshot).hexdigest() == snapshot_digest
        ),
        "selection_before_mutation_correct": selected_index == 1,
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    results = [_run_scenario(fixture, case) for case in fixture["scenarios"]]
    return {
        "scenario_count": len(results),
        "baseline_correct": sum(item["baseline_correct"] for item in results),
        "candidate_correct": sum(item["candidate_correct"] for item in results),
        "baseline_locked_outcomes": sum(
            item["baseline_matches_locked"] for item in results
        ),
        "shared_reference_drifts": sum(
            item["shared_reference_drift"] for item in results
        ),
        "snapshot_drifts": sum(item["snapshot_drift"] for item in results),
        "mutations_visible_in_catalog": sum(
            item["mutation_visible_in_catalog"] for item in results
        ),
        "only_locked_fields_changed": all(
            item["only_locked_field_changed"] for item in results
        ),
        "unselected_descriptors_unchanged": all(
            item["unselected_descriptor_unchanged"] for item in results
        ),
        "snapshot_bytes_unchanged": all(
            item["snapshot_bytes_unchanged"] for item in results
        ),
        "pre_mutation_selection_correct": all(
            item["selection_before_mutation_correct"] for item in results
        ),
        "artifact_load_attempts": 0,
        "repository_writes": 0,
        "outcomes": [
            {"id": item["id"], "baseline": item["baseline"], "candidate": item["candidate"]}
            for item in results
        ],
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["scenario_count"] == 3
        and summary["baseline_correct"]
        == fixture["expected_baseline_correct"] == 0
        and summary["candidate_correct"]
        == fixture["expected_candidate_correct"] == 3
        and summary["baseline_locked_outcomes"] == 3
        and summary["shared_reference_drifts"]
        == fixture["expected_shared_reference_drifts"] == 3
        and summary["snapshot_drifts"]
        == fixture["expected_snapshot_drifts"] == 0
        and summary["mutations_visible_in_catalog"] == 3
        and summary["only_locked_fields_changed"]
        and summary["unselected_descriptors_unchanged"]
        and summary["snapshot_bytes_unchanged"]
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
