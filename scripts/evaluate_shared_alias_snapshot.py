#!/usr/bin/env python3
"""Evaluate snapshot isolation when two fields intentionally share one object."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_joint_compatibility as joint  # noqa: E402
from scripts.validate_expert_manifest import V2_SCHEMA  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_shared_alias_snapshot_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "prior_evaluator",
    "base_template", "reference_date", "artifacts", "consumers",
    "shared_fields", "shared_member", "scenarios", "expected_shared_correct",
    "expected_shallow_correct", "expected_deepcopy_correct",
    "expected_json_correct", "expected_deepcopy_source_isolations",
    "expected_json_source_isolations", "expected_json_alias_losses",
    "expected_decision",
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


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-shared-alias-snapshot-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-046-nested-catalog-descriptor-snapshot.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_nested_catalog_descriptor_snapshot_cases.json",
        ),
        "prior_evaluator": (
            {"path", "sha256"},
            "scripts/evaluate_nested_catalog_descriptor_snapshot.py",
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
    if fixture["prior_experiment"]["id"] != "EXP-046":
        raise ValueError("prior experiment changed")

    prior = json.loads(pinned["prior_fixture"])
    if (
        prior.get("expected_deep_correct") != 3
        or prior.get("expected_deep_drifts") != 0
    ):
        raise ValueError("EXP-046 snapshot evidence changed")
    if fixture["reference_date"] != prior.get("reference_date"):
        raise ValueError("reference date changed")
    if fixture["artifacts"] != prior.get("artifacts"):
        raise ValueError("EXP-046 artifact descriptors changed")
    if fixture["consumers"] != prior.get("consumers"):
        raise ValueError("EXP-046 consumer policies changed")
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

    if fixture["shared_fields"] != ["provenance", "verification"]:
        raise ValueError("shared field names changed")
    member = fixture["shared_member"]
    if (
        not isinstance(member, dict)
        or set(member) != {"source", "claim_ids", "attestations"}
        or not isinstance(member["source"], dict)
        or not isinstance(member["claim_ids"], list)
        or not isinstance(member["attestations"], dict)
    ):
        raise ValueError("shared member has unexpected structure")

    scenarios = fixture["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 3:
        raise ValueError("fixture must contain three scenarios")
    if [case.get("id") for case in scenarios] != [
        "ALIAS-047-A", "ALIAS-047-B", "ALIAS-047-C"
    ]:
        raise ValueError("scenario identities changed")
    if [case.get("path") for case in scenarios] != [
        ["source", "id"], ["claim_ids", 0], ["attestations", "reviewed"]
    ]:
        raise ValueError("scenario mutation paths changed")
    for case in scenarios:
        if not isinstance(case, dict) or set(case) != {
            "id", "path", "replacement"
        }:
            raise ValueError("scenario has unexpected structure")

    if (
        fixture["expected_shared_correct"] != 3
        or fixture["expected_shallow_correct"] != 3
        or fixture["expected_deepcopy_correct"] != 3
        or fixture["expected_json_correct"] != 0
        or fixture["expected_deepcopy_source_isolations"] != 3
        or fixture["expected_json_source_isolations"] != 3
        or fixture["expected_json_alias_losses"] != 3
        or fixture["expected_decision"]
        != "retain-default-and-quarantine-topology-aware-deepcopy"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def _fresh_selection(fixture: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = copy.deepcopy(fixture["artifacts"])
    consumers = copy.deepcopy(fixture["consumers"])
    selection = joint.joint_highest_select(catalog, consumers)
    matches = [item for item in catalog if joint._selected_result(item) == selection]
    if len(matches) != 1:
        raise ValueError("joint selection did not identify one descriptor")
    selected = matches[0]
    shared_member = copy.deepcopy(fixture["shared_member"])
    first, second = fixture["shared_fields"]
    selected[first] = shared_member
    selected[second] = shared_member
    return catalog, selected


def _strategy_result(
    fixture: dict[str, Any],
    scenario: dict[str, Any],
    snapshotter: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    catalog, selected = _fresh_selection(fixture)
    first, second = fixture["shared_fields"]
    catalog_before = _canonical_payload(catalog)
    handoff = snapshotter(selected)
    payload_before = _canonical_payload(handoff)
    aliases_before = handoff[first] is handoff[second]
    source_isolated_before = handoff[first] is not selected[first]

    _set_path(handoff[first], scenario["path"], scenario["replacement"])
    expected_second = copy.deepcopy(fixture["shared_member"])
    _set_path(expected_second, scenario["path"], scenario["replacement"])
    alias_behavior_correct = handoff[second] == expected_second
    aliases_after = handoff[first] is handoff[second]
    source_isolated_after = _canonical_payload(catalog) == catalog_before
    only_locked_leaf_changed = handoff[first] == expected_second
    pre_payload_locked = payload_before == _canonical_payload({
        **fixture["artifacts"][1],
        first: fixture["shared_member"],
        second: fixture["shared_member"],
    })
    return {
        "correct": alias_behavior_correct and aliases_after,
        "alias_preserved": aliases_before and aliases_after,
        "source_isolated": source_isolated_before and source_isolated_after,
        "only_locked_leaf_changed": only_locked_leaf_changed,
        "pre_payload_locked": pre_payload_locked,
        "selection_correct": catalog.index(selected) == 1,
    }


def _shared(value: dict[str, Any]) -> dict[str, Any]:
    return value


def _shallow(value: dict[str, Any]) -> dict[str, Any]:
    return copy.copy(value)


def _deepcopy(value: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(value)


def _json_roundtrip(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(_canonical_payload(value))


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    strategies = {
        "shared": _shared,
        "shallow": _shallow,
        "deepcopy": _deepcopy,
        "json": _json_roundtrip,
    }
    results: dict[str, list[dict[str, Any]]] = {
        name: [
            _strategy_result(fixture, scenario, snapshotter)
            for scenario in fixture["scenarios"]
        ]
        for name, snapshotter in strategies.items()
    }
    return {
        "scenario_count": len(fixture["scenarios"]),
        "shared_correct": sum(item["correct"] for item in results["shared"]),
        "shallow_correct": sum(item["correct"] for item in results["shallow"]),
        "deepcopy_correct": sum(item["correct"] for item in results["deepcopy"]),
        "json_correct": sum(item["correct"] for item in results["json"]),
        "shared_alias_preservations": sum(
            item["alias_preserved"] for item in results["shared"]
        ),
        "shallow_alias_preservations": sum(
            item["alias_preserved"] for item in results["shallow"]
        ),
        "deepcopy_alias_preservations": sum(
            item["alias_preserved"] for item in results["deepcopy"]
        ),
        "json_alias_losses": sum(
            not item["alias_preserved"] for item in results["json"]
        ),
        "shared_source_isolations": sum(
            item["source_isolated"] for item in results["shared"]
        ),
        "shallow_source_isolations": sum(
            item["source_isolated"] for item in results["shallow"]
        ),
        "deepcopy_source_isolations": sum(
            item["source_isolated"] for item in results["deepcopy"]
        ),
        "json_source_isolations": sum(
            item["source_isolated"] for item in results["json"]
        ),
        "only_locked_leaves_changed": all(
            item["only_locked_leaf_changed"]
            for strategy in results.values()
            for item in strategy
        ),
        "pre_payloads_locked": all(
            item["pre_payload_locked"]
            for strategy in results.values()
            for item in strategy
        ),
        "pre_mutation_selection_correct": all(
            item["selection_correct"]
            for strategy in results.values()
            for item in strategy
        ),
        "artifact_load_attempts": 0,
        "repository_writes": 0,
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["scenario_count"] == 3
        and summary["shared_correct"]
        == fixture["expected_shared_correct"] == 3
        and summary["shallow_correct"]
        == fixture["expected_shallow_correct"] == 3
        and summary["deepcopy_correct"]
        == fixture["expected_deepcopy_correct"] == 3
        and summary["json_correct"]
        == fixture["expected_json_correct"] == 0
        and summary["shared_alias_preservations"] == 3
        and summary["shallow_alias_preservations"] == 3
        and summary["deepcopy_alias_preservations"] == 3
        and summary["json_alias_losses"]
        == fixture["expected_json_alias_losses"] == 3
        and summary["shared_source_isolations"] == 0
        and summary["shallow_source_isolations"] == 0
        and summary["deepcopy_source_isolations"]
        == fixture["expected_deepcopy_source_isolations"] == 3
        and summary["json_source_isolations"]
        == fixture["expected_json_source_isolations"] == 3
        and summary["only_locked_leaves_changed"]
        and summary["pre_payloads_locked"]
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
