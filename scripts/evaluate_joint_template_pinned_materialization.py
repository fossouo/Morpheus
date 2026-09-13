#!/usr/bin/env python3
"""Evaluate pinned loading after joint template selection and materialization."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_joint_compatibility as joint  # noqa: E402
from scripts.validate_expert_manifest import V2_SCHEMA, validate_manifest  # noqa: E402


DEFAULT_FIXTURE = (
    ROOT / "fixtures" / "expert_joint_template_pinned_materialization_cases.json"
)
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "prior_evaluator",
    "base_template", "reference_date", "artifacts", "consumers", "scenarios",
    "expected_baseline_correct", "expected_candidate_correct",
    "expected_baseline_silent_downgrades",
    "expected_candidate_silent_downgrades", "expected_decision",
}


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    try:
        payload = (ROOT / source["path"]).read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _loaded_result(artifact: dict[str, Any]) -> str:
    return (
        f"loaded:{artifact['schema']}:{artifact['version']}:{artifact['path']}"
    )


def _artifact_path(root: Path, artifact: dict[str, Any]) -> Path:
    path = root / artifact["path"]
    if root not in path.parents:
        raise ValueError("artifact path escaped temporary root")
    return path


def _load_exact(
    root: Path,
    artifact: dict[str, Any],
    reference_date: date,
) -> str:
    path = _artifact_path(root, artifact)
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return "error:pinned-artifact-missing"
    if hashlib.sha256(payload).hexdigest() != artifact["sha256"]:
        return "error:pinned-artifact-hash-mismatch"
    try:
        manifest = json.loads(payload)
    except json.JSONDecodeError:
        return "error:pinned-artifact-invalid"
    if (
        manifest.get("schema") != artifact["schema"]
        or manifest.get("version") != artifact["version"]
        or validate_manifest(manifest, reference_date=reference_date)
    ):
        return "error:pinned-artifact-invalid"
    return _loaded_result(artifact)


def _descriptor_from_selection(
    selection: str,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    matches = [item for item in artifacts if joint._selected_result(item) == selection]
    if len(matches) != 1:
        raise ValueError("joint selection did not identify one descriptor")
    return matches[0]


def _fallback_load(
    root: Path,
    artifacts: list[dict[str, Any]],
    consumers: list[dict[str, Any]],
    reference_date: date,
) -> str:
    loadable = []
    for artifact in artifacts:
        path = _artifact_path(root, artifact)
        if not path.is_file():
            continue
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() == artifact["sha256"]:
            loadable.append(artifact)
    selection = joint.joint_highest_select(loadable, consumers)
    if selection.startswith("error:"):
        return selection
    selected = _descriptor_from_selection(selection, loadable)
    return _load_exact(root, selected, reference_date)


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-joint-template-pinned-materialization-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-043-template-joint-compatibility.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_template_joint_compatibility_cases.json",
        ),
        "prior_evaluator": (
            {"path", "sha256"},
            "scripts/evaluate_template_joint_compatibility.py",
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
    if fixture["prior_experiment"]["id"] != "EXP-043":
        raise ValueError("prior experiment changed")
    prior_fixture = json.loads(_read_pinned(fixture["prior_fixture"], "prior-fixture"))
    if (
        prior_fixture.get("expected_candidate_correct") != 5
        or prior_fixture.get("selection_cases", [{}])[0].get("id") != "SEL-043-A"
    ):
        raise ValueError("EXP-043 joint-selection evidence changed")

    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be canonical") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be canonical")

    base_template = json.loads(_read_pinned(fixture["base_template"], "base-template"))
    artifacts = fixture["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ValueError("fixture must contain two artifacts")
    if [item.get("id") for item in artifacts] != ["v2-1-0-2", "v2-1-1-0"]:
        raise ValueError("artifact identities changed")
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "id", "schema", "version", "path", "sha256"
        }:
            raise ValueError("artifact descriptor has unexpected structure")
        if artifact["schema"] != V2_SCHEMA:
            raise ValueError("artifact schema changed")
        joint._parse_version(artifact["version"])
        derived = joint._derived_artifact(base_template, artifact["version"])
        if hashlib.sha256(derived).hexdigest() != artifact["sha256"]:
            raise ValueError("derived artifact hash changed")
        if validate_manifest(json.loads(derived), reference_date=reference_date):
            raise ValueError("derived artifact is invalid")
        pinned_bytes += len(derived)

    consumers = fixture["consumers"]
    if not isinstance(consumers, list) or len(consumers) != 2:
        raise ValueError("fixture must contain two consumers")
    for policy in consumers:
        joint._validate_policy(policy)
    if [policy["id"] for policy in consumers] != ["consumer-a", "consumer-b"]:
        raise ValueError("consumer identities changed")
    if consumers != prior_fixture["selection_cases"][0]["consumers"]:
        raise ValueError("EXP-043 consumer ranges changed")
    selected = joint.joint_highest_select(artifacts, consumers)
    if selected != joint._selected_result(artifacts[1]):
        raise ValueError("pre-fault joint selection changed")

    scenarios = fixture["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 3:
        raise ValueError("fixture must contain three scenarios")
    if [case.get("id") for case in scenarios] != [
        "MAT-044-A", "MAT-044-B", "MAT-044-C"
    ]:
        raise ValueError("scenario identities changed")
    if [case.get("fault") for case in scenarios] != [
        "none", "remove-selected", "mutate-selected"
    ]:
        raise ValueError("scenario faults changed")
    for case in scenarios:
        if not isinstance(case, dict) or set(case) != {
            "id", "fault", "expected_baseline", "expected_candidate"
        }:
            raise ValueError("scenario has unexpected structure")

    if (
        fixture["expected_baseline_correct"] != 1
        or fixture["expected_candidate_correct"] != 3
        or fixture["expected_baseline_silent_downgrades"] != 2
        or fixture["expected_candidate_silent_downgrades"] != 0
        or fixture["expected_decision"]
        != "retain-default-and-quarantine-pinned-joint-loader"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def _run_scenario(
    fixture: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    artifacts = fixture["artifacts"]
    lower, selected = artifacts
    reference_date = date.fromisoformat(fixture["reference_date"])
    base_template = json.loads(_read_pinned(fixture["base_template"], "base-template"))
    with tempfile.TemporaryDirectory(prefix="morpheus-exp-044-") as raw_root:
        root = Path(raw_root)
        for artifact in artifacts:
            path = _artifact_path(root, artifact)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(joint._derived_artifact(base_template, artifact["version"]))

        pre_fault = joint.joint_highest_select(artifacts, fixture["consumers"])
        pinned = _descriptor_from_selection(pre_fault, artifacts)
        selected_path = _artifact_path(root, selected)
        if scenario["fault"] == "remove-selected":
            selected_path.unlink()
        elif scenario["fault"] == "mutate-selected":
            selected_path.write_bytes(selected_path.read_bytes() + b" ")

        baseline = _fallback_load(
            root, artifacts, fixture["consumers"], reference_date
        )
        candidate = _load_exact(root, pinned, reference_date)
        lower_path = _artifact_path(root, lower)
        lower_exact = (
            lower_path.is_file()
            and hashlib.sha256(lower_path.read_bytes()).hexdigest() == lower["sha256"]
        )
        selected_is_pre_fault = pinned["id"] == selected["id"]

    return {
        "id": scenario["id"],
        "baseline": baseline,
        "candidate": candidate,
        "baseline_matches_locked": baseline == scenario["expected_baseline"],
        "baseline_correct": baseline == scenario["expected_candidate"],
        "candidate_correct": candidate == scenario["expected_candidate"],
        "baseline_silent_downgrade": (
            scenario["fault"] != "none" and baseline == _loaded_result(lower)
        ),
        "candidate_silent_downgrade": candidate == _loaded_result(lower),
        "lower_present_and_exact": lower_exact,
        "selected_is_pre_fault_joint_maximum": selected_is_pre_fault,
        "materialized_artifact_count": 2,
        "temporary_root_removed": not root.exists(),
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
        "baseline_silent_downgrades": sum(
            item["baseline_silent_downgrade"] for item in results
        ),
        "candidate_silent_downgrades": sum(
            item["candidate_silent_downgrade"] for item in results
        ),
        "pre_fault_selection_correct": all(
            item["selected_is_pre_fault_joint_maximum"] for item in results
        ),
        "lower_present_and_exact": sum(
            item["lower_present_and_exact"] for item in results
        ),
        "materialized_artifact_counts": [
            item["materialized_artifact_count"] for item in results
        ],
        "temporary_roots_removed": all(
            item["temporary_root_removed"] for item in results
        ),
        "removal_rejected": (
            results[1]["candidate"] == "error:pinned-artifact-missing"
        ),
        "mutation_rejected": (
            results[2]["candidate"] == "error:pinned-artifact-hash-mismatch"
        ),
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
        == fixture["expected_baseline_correct"] == 1
        and summary["candidate_correct"]
        == fixture["expected_candidate_correct"] == 3
        and summary["baseline_locked_outcomes"] == 3
        and summary["baseline_silent_downgrades"]
        == fixture["expected_baseline_silent_downgrades"] == 2
        and summary["candidate_silent_downgrades"]
        == fixture["expected_candidate_silent_downgrades"] == 0
        and summary["pre_fault_selection_correct"]
        and summary["lower_present_and_exact"] == 3
        and summary["materialized_artifact_counts"] == [2, 2, 2]
        and summary["temporary_roots_removed"]
        and summary["removal_rejected"]
        and summary["mutation_rejected"]
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
