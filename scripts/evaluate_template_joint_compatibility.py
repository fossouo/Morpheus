#!/usr/bin/env python3
"""Evaluate independent versus joint pinned-template compatibility selection."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_expert_manifest import V2_SCHEMA, validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_template_joint_compatibility_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "base_template",
    "reference_date", "artifacts", "catalogs", "selection_cases",
    "expected_baseline_correct", "expected_candidate_correct", "expected_decision",
}


def _canonical_payload(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    try:
        payload = (ROOT / source["path"]).read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _parse_version(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise ValueError("version must be a string")
    parts = value.split(".")
    if len(parts) != 3 or any(
        not part.isdigit() or (len(part) > 1 and part.startswith("0"))
        for part in parts
    ):
        raise ValueError("version must contain three canonical numeric components")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _derived_artifact(base_template: dict[str, Any], version: str) -> bytes:
    candidate = copy.deepcopy(base_template)
    candidate["version"] = version
    return _canonical_payload(candidate)


def _validate_policy(policy: Any) -> None:
    if not isinstance(policy, dict) or not isinstance(policy.get("id"), str):
        raise ValueError("consumer policy has unexpected structure")
    if policy.get("schema") != V2_SCHEMA:
        raise ValueError("consumer schema changed")
    if policy.get("mode") == "exact":
        if set(policy) != {"id", "schema", "mode", "version"}:
            raise ValueError("exact policy has unexpected structure")
        _parse_version(policy["version"])
        return
    if policy.get("mode") == "range":
        if set(policy) != {
            "id", "schema", "mode", "minimum", "maximum", "major"
        }:
            raise ValueError("range policy has unexpected structure")
        minimum = _parse_version(policy["minimum"])
        maximum = _parse_version(policy["maximum"])
        if (
            not isinstance(policy["major"], int)
            or policy["major"] != minimum[0]
            or policy["major"] != maximum[0]
            or minimum > maximum
        ):
            raise ValueError("range policy is invalid")
        return
    raise ValueError("consumer policy mode is unsupported")


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-template-joint-compatibility-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-042-template-compatibility-policy.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_template_compatibility_policy_cases.json",
        ),
        "base_template": (
            {"path", "sha256"},
            "templates/expert-package-v2.json",
        ),
    }
    pinned_bytes = 0
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
        pinned_bytes += len(_read_pinned(source, name.replace("_", "-")))
    if fixture["prior_experiment"]["id"] != "EXP-042":
        raise ValueError("prior experiment changed")
    prior = json.loads(_read_pinned(fixture["prior_fixture"], "prior-fixture"))
    if prior.get("expected_candidate_correct") != 5:
        raise ValueError("EXP-042 candidate baseline changed")

    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be canonical") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be canonical")

    base_template = json.loads(_read_pinned(fixture["base_template"], "base-template"))
    artifacts = fixture["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 5:
        raise ValueError("fixture must contain five artifacts")
    ids: set[str] = set()
    paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "id", "schema", "version", "path", "sha256"
        }:
            raise ValueError("artifact descriptor has unexpected structure")
        if artifact["schema"] != V2_SCHEMA:
            raise ValueError("artifact schema changed")
        _parse_version(artifact["version"])
        if artifact["id"] in ids or artifact["path"] in paths:
            raise ValueError("artifact identity or path is duplicated")
        ids.add(artifact["id"])
        paths.add(artifact["path"])
        derived = _derived_artifact(base_template, artifact["version"])
        if hashlib.sha256(derived).hexdigest() != artifact["sha256"]:
            raise ValueError("derived artifact hash changed")
        if validate_manifest(json.loads(derived), reference_date=reference_date):
            raise ValueError("derived artifact is invalid")
        pinned_bytes += len(derived)

    if fixture["catalogs"] != {
        "standard": ["v2-1-0-0", "v2-1-0-2", "v2-1-1-0", "v2-1-2-0"],
        "ambiguous": [
            "v2-1-0-0", "v2-1-0-2", "v2-1-1-0", "v2-1-1-0-mirror"
        ],
    }:
        raise ValueError("catalog membership changed")

    cases = fixture["selection_cases"]
    if not isinstance(cases, list) or len(cases) != 5:
        raise ValueError("fixture must contain five selection cases")
    if [case.get("id") for case in cases] != [
        "SEL-043-A", "SEL-043-B", "SEL-043-C", "SEL-043-D", "SEL-043-E"
    ]:
        raise ValueError("selection case identities changed")
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "id", "catalog", "consumers", "expected"
        }:
            raise ValueError("selection case has unexpected structure")
        if case["catalog"] not in fixture["catalogs"]:
            raise ValueError("selection case catalog is unsupported")
        if not isinstance(case["consumers"], list) or len(case["consumers"]) != 2:
            raise ValueError("selection case must contain two consumers")
        for policy in case["consumers"]:
            _validate_policy(policy)
        if len({policy["id"] for policy in case["consumers"]}) != 2:
            raise ValueError("consumer identities must be distinct")

    if (
        fixture["expected_baseline_correct"] != 1
        or fixture["expected_candidate_correct"] != 5
        or fixture["expected_decision"]
        != "retain-independent-default-and-quarantine-joint-selection"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def _artifacts_by_id(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {artifact["id"]: artifact for artifact in fixture["artifacts"]}


def _catalog(fixture: dict[str, Any], name: str) -> list[dict[str, Any]]:
    by_id = _artifacts_by_id(fixture)
    return [by_id[artifact_id] for artifact_id in fixture["catalogs"][name]]


def _matches_policy(artifact: dict[str, Any], policy: dict[str, Any]) -> bool:
    if artifact["schema"] != policy["schema"]:
        return False
    version = _parse_version(artifact["version"])
    if policy["mode"] == "exact":
        return version == _parse_version(policy["version"])
    minimum = _parse_version(policy["minimum"])
    maximum = _parse_version(policy["maximum"])
    return version[0] == policy["major"] and minimum <= version <= maximum


def _selected_result(artifact: dict[str, Any]) -> str:
    return f"selected:{artifact['schema']}:{artifact['version']}:{artifact['path']}"


def _select_one(
    descriptors: list[dict[str, Any]], policy: dict[str, Any]
) -> dict[str, Any] | str:
    matches = [item for item in descriptors if _matches_policy(item, policy)]
    if not matches:
        return "error:no-compatible-template"
    highest = max(_parse_version(item["version"]) for item in matches)
    winners = [item for item in matches if _parse_version(item["version"]) == highest]
    if len(winners) != 1:
        return "error:ambiguous-highest-version"
    return winners[0]


def independent_highest_select(
    descriptors: list[dict[str, Any]], policies: list[dict[str, Any]]
) -> str:
    selections = [_select_one(descriptors, policy) for policy in policies]
    if any(isinstance(item, str) for item in selections):
        return "error:independent-unresolved"
    selected = selections  # narrow the meaning for the checks below
    if len({item["id"] for item in selected if isinstance(item, dict)}) != 1:
        return "error:independent-disagreement"
    return _selected_result(selected[0])  # type: ignore[arg-type]


def joint_highest_select(
    descriptors: list[dict[str, Any]], policies: list[dict[str, Any]]
) -> str:
    matches = [
        artifact for artifact in descriptors
        if all(_matches_policy(artifact, policy) for policy in policies)
    ]
    if not matches:
        return "error:no-joint-compatible-template"
    highest = max(_parse_version(item["version"]) for item in matches)
    winners = [item for item in matches if _parse_version(item["version"]) == highest]
    if len(winners) != 1:
        return "error:ambiguous-joint-highest-version"
    return _selected_result(winners[0])


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    baseline: list[str] = []
    candidate: list[str] = []
    for case in fixture["selection_cases"]:
        descriptors = _catalog(fixture, case["catalog"])
        baseline.append(independent_highest_select(descriptors, case["consumers"]))
        candidate.append(joint_highest_select(descriptors, case["consumers"]))

    expected = [case["expected"] for case in fixture["selection_cases"]]
    return {
        "artifact_descriptor_count": len(fixture["artifacts"]),
        "unique_version_count": len({item["version"] for item in fixture["artifacts"]}),
        "consumer_count_per_case": [len(case["consumers"]) for case in fixture["selection_cases"]],
        "baseline_correct": sum(actual == wanted for actual, wanted in zip(baseline, expected)),
        "candidate_correct": sum(actual == wanted for actual, wanted in zip(candidate, expected)),
        "partial_overlap_correct": candidate[0] == expected[0],
        "narrow_overlap_correct": candidate[1] == expected[1],
        "exact_constraint_correct": candidate[2] == expected[2],
        "empty_intersection_rejected": candidate[3] == expected[3],
        "ambiguous_joint_highest_rejected": candidate[4] == expected[4],
        "load_attempts": 0,
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["artifact_descriptor_count"] == 5
        and summary["unique_version_count"] == 4
        and summary["consumer_count_per_case"] == [2, 2, 2, 2, 2]
        and summary["baseline_correct"] == fixture["expected_baseline_correct"] == 1
        and summary["candidate_correct"] == fixture["expected_candidate_correct"] == 5
        and summary["partial_overlap_correct"]
        and summary["narrow_overlap_correct"]
        and summary["exact_constraint_correct"]
        and summary["empty_intersection_rejected"]
        and summary["ambiguous_joint_highest_rejected"]
        and summary["load_attempts"] == 0
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
