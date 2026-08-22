#!/usr/bin/env python3
"""Evaluate exclusion cardinality transitions among three tied expert candidates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from itertools import permutations
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_equal_specificity_exclusion_isolation import (  # noqa: E402
    PreExclusionAmbiguityKernel,
)
from scripts.evaluate_exclusion_scope_routing import _matches_pattern  # noqa: E402
from scripts.evaluate_expert_composition import _validated_package_records  # noqa: E402
from scripts.evaluate_hierarchical_scope_routing import _scope_segments  # noqa: E402
from scripts.evaluate_specificity_floor_exclusion_routing import (  # noqa: E402
    SpecificityFloorExclusionRoutingKernel,
)
from scripts.evaluate_wildcard_scope_routing import _pattern_segments, _validated_cases  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_multi_candidate_exclusion_cases.json"


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "packages", "compatible_package_ids",
        "held_out_target", "held_out_regression", "boundary_probe", "absent_scope_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-multi-candidate-exclusion-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    packages = fixture["packages"]
    if not isinstance(packages, list) or len(packages) != 4:
        raise ValueError("fixture must contain exactly four packages")
    package_ids: list[str] = []
    for package in packages:
        package_id, _ = _validated_package_records(package, reference_date=reference_date)
        if package_id in package_ids:
            raise ValueError("package ids must be unique")
        package_ids.append(package_id)
        for name in ("include", "exclude"):
            for pattern in package["manifest"]["scope"][name]:
                _pattern_segments(pattern)

    if fixture["compatible_package_ids"] != package_ids:
        raise ValueError("compatible_package_ids must preserve package fixture order")

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 8:
        raise ValueError("fixture must contain exactly eight target cases")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise ValueError("fixture must contain exactly three regression cases")
    target_keys = {
        "id", "policy", "request", "expected_top_candidates",
        "expected_eligible_candidates", "expected_baseline", "expected_candidate",
        "expected_unloaded",
    }
    target_ids: list[str] = []
    for case in targets:
        if not isinstance(case, dict) or set(case) != target_keys:
            raise ValueError("target case has unexpected structure")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in target_ids:
            raise ValueError("target ids must be non-empty and unique")
        target_ids.append(case_id)
        if not isinstance(case["request"], dict):
            raise ValueError("target request must be an object")
        for key in ("policy", "expected_baseline", "expected_candidate", "expected_unloaded"):
            if not isinstance(case[key], str):
                raise ValueError("target labels and responses must be strings")
        for key in ("expected_top_candidates", "expected_eligible_candidates"):
            if not isinstance(case[key], int) or isinstance(case[key], bool):
                raise ValueError("target cardinalities must be integers")
    policies = [case["policy"] for case in targets]
    expected_policies = {
        "three-to-one-exact": 1,
        "three-to-one-wildcard": 1,
        "three-to-two-exact": 1,
        "three-to-two-wildcard": 1,
        "three-to-zero-exact": 1,
        "three-to-zero-wildcard": 1,
        "floor-exact": 1,
        "floor-wildcard": 1,
    }
    if any(policies.count(policy) != count for policy, count in expected_policies.items()):
        raise ValueError("target policies do not match the locked protocol")
    expected_counts = {
        "three-to-one-": (3, 1),
        "three-to-two-": (3, 2),
        "three-to-zero-": (3, 0),
        "floor-": (1, 0),
    }
    for case in targets:
        prefix = next(prefix for prefix in expected_counts if case["policy"].startswith(prefix))
        observed = (case["expected_top_candidates"], case["expected_eligible_candidates"])
        if observed != expected_counts[prefix]:
            raise ValueError("target cardinalities do not match the locked protocol")

    regression_ids = _validated_cases(regressions, {"id", "request", "expected"})
    declared_targets: list[str] = []
    for package in packages:
        manifest = package["manifest"]
        declared_targets.extend(manifest["tests"]["target"])
        if manifest["tests"]["held_out_regression"] != regression_ids:
            raise ValueError("regression ids must match package manifests")
    if declared_targets != target_ids:
        raise ValueError("target ids must match package manifests in fixture order")

    for probe_name in ("boundary_probe", "absent_scope_probe"):
        probe = fixture[probe_name]
        if not isinstance(probe, dict) or set(probe) != {"request", "expected"}:
            raise ValueError(f"{probe_name} has unexpected structure")
        if not isinstance(probe["request"], dict) or not isinstance(probe["expected"], str):
            raise ValueError(f"invalid {probe_name}")


def _packages_by_id(fixture: dict[str, Any]) -> dict[str, Any]:
    return {package["manifest"]["package_id"]: package for package in fixture["packages"]}


def _cardinality(
    kernel: SpecificityFloorExclusionRoutingKernel, request: dict[str, Any]
) -> tuple[int, int]:
    request_segments = _scope_segments(request["scope"])
    matching: list[tuple[tuple[int, int], str]] = []
    for pattern, package_id in kernel._package_by_scope.items():
        pattern_segments = _pattern_segments(pattern)
        if len(request_segments) < len(pattern_segments):
            continue
        if all(
            declared == "*" or declared == actual
            for declared, actual in zip(pattern_segments, request_segments)
        ):
            matching.append((
                (
                    len(pattern_segments),
                    sum(segment != "*" for segment in pattern_segments),
                ),
                package_id,
            ))
    if not matching:
        return 0, 0
    floor = max(score for score, _ in matching)
    top = [candidate for candidate in matching if candidate[0] == floor]
    eligible = [
        candidate
        for candidate in top
        if not any(
            _matches_pattern(exclusion, request_segments)
            for exclusion in kernel._exclusions_by_package[candidate[1]]
        )
    ]
    return len(top), len(eligible)


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _packages_by_id(fixture)
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    orders = [list(order) for order in permutations(fixture["compatible_package_ids"])]

    order_runs: list[dict[str, Any]] = []
    for order in orders:
        packages = [by_id[package_id] for package_id in order]

        baseline = PreExclusionAmbiguityKernel()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        baseline_target = [baseline.answer(case["request"]) for case in targets]

        candidate = SpecificityFloorExclusionRoutingKernel()
        unloaded_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(packages, reference_date=reference_date)
        cardinalities = [_cardinality(candidate, case["request"]) for case in targets]
        candidate_target = [candidate.answer(case["request"]) for case in targets]
        candidate_regression = [candidate.answer(case["request"]) for case in regressions]
        boundary = candidate.answer(fixture["boundary_probe"]["request"])
        absent = candidate.answer(fixture["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        order_runs.append({
            "baseline_target": baseline_target,
            "unloaded_regression": unloaded_regression,
            "cardinalities": cardinalities,
            "candidate_target": candidate_target,
            "candidate_regression": candidate_regression,
            "boundary": boundary,
            "absent": absent,
            "post_unload_target": post_unload_target,
        })
    return {"orders": orders, "order_runs": order_runs}


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    targets = fixture["held_out_target"]
    expected_baseline = [case["expected_baseline"] for case in targets]
    expected_candidate = [case["expected_candidate"] for case in targets]
    expected_unloaded = [case["expected_unloaded"] for case in targets]
    expected_cardinalities = [
        (case["expected_top_candidates"], case["expected_eligible_candidates"])
        for case in targets
    ]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first = trial["order_runs"][0]
    indexes = {
        prefix: [
            index for index, case in enumerate(targets) if case["policy"].startswith(prefix)
        ]
        for prefix in ("three-to-one-", "three-to-two-", "three-to-zero-", "floor-")
    }
    baseline_correct = sum(
        actual == expected
        for actual, expected in zip(first["baseline_target"], expected_candidate)
    )
    candidate_correct = sum(
        actual == expected
        for actual, expected in zip(first["candidate_target"], expected_candidate)
    )
    target_count = len(targets)
    order_count = len(trial["orders"])
    return {
        "target_count": target_count,
        "order_count": order_count,
        "baseline_policy_outputs_correct": all(
            run["baseline_target"] == expected_baseline for run in trial["order_runs"]
        ),
        "baseline_target_correct": baseline_correct,
        "baseline_pre_exclusion_ambiguities": sum(
            response == "route-error:ambiguous-specificity"
            for response in first["baseline_target"]
        ),
        "cardinality_expectations_correct": all(
            run["cardinalities"] == expected_cardinalities for run in trial["order_runs"]
        ),
        "candidate_target_correct": candidate_correct,
        "target_accuracy_gain": round((candidate_correct - baseline_correct) / target_count, 6),
        "candidate_three_to_one_selections": sum(
            first["candidate_target"][index] == expected_candidate[index]
            for index in indexes["three-to-one-"]
        ),
        "candidate_three_to_two_ambiguities": sum(
            first["candidate_target"][index] == "route-error:ambiguous-specificity"
            for index in indexes["three-to-two-"]
        ),
        "candidate_three_to_zero_denials": sum(
            first["candidate_target"][index] == "route-error:scope-excluded"
            for index in indexes["three-to-zero-"]
        ),
        "candidate_floor_denials": sum(
            first["candidate_target"][index] == "route-error:scope-excluded"
            for index in indexes["floor-"]
        ),
        "regression_count": len(expected_regression),
        "unloaded_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["unloaded_regression"], expected_regression)
        ),
        "candidate_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["candidate_regression"], expected_regression)
        ),
        "baseline_order_invariant": all(
            run["baseline_target"] == first["baseline_target"]
            for run in trial["order_runs"]
        ),
        "candidate_order_invariant": all(
            run["candidate_target"] == first["candidate_target"]
            and run["candidate_regression"] == first["candidate_regression"]
            and run["cardinalities"] == first["cardinalities"]
            for run in trial["order_runs"]
        ),
        "boundary_rejections": sum(
            run["boundary"] == fixture["boundary_probe"]["expected"]
            for run in trial["order_runs"]
        ),
        "absent_scope_rejections": sum(
            run["absent"] == fixture["absent_scope_probe"]["expected"]
            for run in trial["order_runs"]
        ),
        "rollback_matches_baseline": sum(
            actual == expected
            for run in trial["order_runs"]
            for actual, expected in zip(run["post_unload_target"], expected_unloaded)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first = run_trial(fixture)
    repeated = run_trial(fixture)
    elapsed_seconds = perf_counter() - started
    summary = summarize(fixture, first)
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": args.fixture.stat().st_size,
        "evaluation_seconds": round(elapsed_seconds, 6),
        "external_calls": 0,
    })
    summary["accepted"] = (
        summary["baseline_policy_outputs_correct"]
        and summary["baseline_target_correct"] == 4
        and summary["baseline_pre_exclusion_ambiguities"] == 6
        and summary["cardinality_expectations_correct"]
        and summary["candidate_target_correct"] == summary["target_count"] == 8
        and summary["target_accuracy_gain"] == 0.5
        and summary["candidate_three_to_one_selections"] == 2
        and summary["candidate_three_to_two_ambiguities"] == 2
        and summary["candidate_three_to_zero_denials"] == 2
        and summary["candidate_floor_denials"] == 2
        and summary["unloaded_regression_correct"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["order_count"] == 24
        and summary["baseline_order_invariant"]
        and summary["candidate_order_invariant"]
        and summary["boundary_rejections"] == summary["order_count"]
        and summary["absent_scope_rejections"] == summary["order_count"]
        and summary["rollback_matches_baseline"]
        == summary["target_count"] * summary["order_count"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
