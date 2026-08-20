#!/usr/bin/env python3
"""Evaluate a fail-closed specificity floor for package-owned exclusions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_exclusion_scope_routing import _matches_pattern  # noqa: E402
from scripts.evaluate_expert_composition import _validated_package_records  # noqa: E402
from scripts.evaluate_hierarchical_scope_routing import _scope_segments  # noqa: E402
from scripts.evaluate_package_owned_exclusion_routing import (  # noqa: E402
    PackageOwnedExclusionRoutingKernel,
)
from scripts.evaluate_wildcard_scope_routing import (  # noqa: E402
    _pattern_segments,
    _validate_reversed_orders,
    _validated_cases,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_specificity_floor_exclusion_cases.json"


class SpecificityFloorExclusionRoutingKernel(PackageOwnedExclusionRoutingKernel):
    """Keep routing at the best pre-exclusion include score or fail closed."""

    def answer(self, request: Any) -> str:
        if isinstance(request, dict) and request.get("operation") == "scope_recall":
            if set(request) != {"operation", "scope", "local_id"}:
                raise ValueError("unsupported request")
            request_segments = _scope_segments(request["scope"])
            local_id = request["local_id"]
            if not isinstance(local_id, str) or not local_id:
                raise ValueError("local_id must be a non-empty string")

            matching: list[tuple[tuple[int, int], str, str]] = []
            for pattern, package_id in self._package_by_scope.items():
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
                        pattern,
                        package_id,
                    ))

            if not matching:
                return "route-error:scope-not-found"
            specificity_floor = max(score for score, _, _ in matching)
            eligible = [
                candidate
                for candidate in matching
                if candidate[0] == specificity_floor
                and not any(
                    _matches_pattern(exclusion, request_segments)
                    for exclusion in self._exclusions_by_package[candidate[2]]
                )
            ]
            if not eligible:
                return "route-error:scope-excluded"
            if len(eligible) != 1:
                return "route-error:ambiguous-specificity"
            package_id = eligible[0][2]
            return self._knowledge_by_package[package_id].get(local_id, "unknown")
        return super().answer(request)


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "packages", "compatible_package_ids",
        "compatible_orders", "specificity_orders", "tie_orders", "held_out_target",
        "held_out_regression", "specificity_probe", "tie_probe", "tie_control_probe",
        "boundary_probe", "absent_scope_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-specificity-floor-exclusion-cases-v1":
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

    compatible_ids = fixture["compatible_package_ids"]
    if (
        not isinstance(compatible_ids, list)
        or len(compatible_ids) != 2
        or len(set(compatible_ids)) != 2
        or any(package_id not in package_ids for package_id in compatible_ids)
    ):
        raise ValueError("compatible_package_ids must name two distinct packages")
    if fixture["compatible_orders"] != [compatible_ids, list(reversed(compatible_ids))]:
        raise ValueError("compatible_orders must contain the pair and its reversal")
    _validate_reversed_orders("specificity_orders", fixture["specificity_orders"], package_ids)
    _validate_reversed_orders("tie_orders", fixture["tie_orders"], package_ids)

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 8:
        raise ValueError("fixture must contain exactly eight target cases")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise ValueError("fixture must contain exactly three regression cases")
    target_ids = _validated_cases(
        targets,
        {
            "id", "policy", "request", "expected_baseline", "expected_candidate",
            "expected_unloaded",
        },
    )
    policies = [case["policy"] for case in targets]
    expected_policies = {
        "allow": 2,
        "delegate-exact": 1,
        "delegate-wildcard": 1,
        "floor-exact": 1,
        "floor-wildcard": 1,
        "all-excluded-exact": 1,
        "all-excluded-wildcard": 1,
    }
    if any(policies.count(policy) != count for policy, count in expected_policies.items()):
        raise ValueError("target policies do not match the locked protocol")
    regression_ids = _validated_cases(regressions, {"id", "request", "expected"})
    by_id = {package["manifest"]["package_id"]: package for package in packages}
    declared_targets: list[str] = []
    for package_id in compatible_ids:
        manifest = by_id[package_id]["manifest"]
        declared_targets.extend(manifest["tests"]["target"])
        if manifest["tests"]["held_out_regression"] != regression_ids:
            raise ValueError("regression ids must match compatible package manifests")
    if declared_targets != target_ids:
        raise ValueError("target ids must match compatible manifests in fixture order")

    for probe_name in (
        "specificity_probe", "tie_probe", "tie_control_probe", "boundary_probe",
        "absent_scope_probe",
    ):
        probe = fixture[probe_name]
        if not isinstance(probe, dict) or set(probe) != {"request", "expected"}:
            raise ValueError(f"{probe_name} has unexpected structure")
        if not isinstance(probe["request"], dict) or not isinstance(probe["expected"], str):
            raise ValueError(f"invalid {probe_name}")


def _packages_by_id(fixture: dict[str, Any]) -> dict[str, Any]:
    return {package["manifest"]["package_id"]: package for package in fixture["packages"]}


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _packages_by_id(fixture)
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]

    candidate_runs: list[dict[str, Any]] = []
    baseline_target: list[str] = []
    for index, order in enumerate(fixture["compatible_orders"]):
        packages = [by_id[package_id] for package_id in order]
        baseline = PackageOwnedExclusionRoutingKernel()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        if index == 0:
            baseline_target = [baseline.answer(case["request"]) for case in targets]

        candidate = SpecificityFloorExclusionRoutingKernel()
        baseline_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(packages, reference_date=reference_date)
        loaded_target = [candidate.answer(case["request"]) for case in targets]
        loaded_regression = [candidate.answer(case["request"]) for case in regressions]
        boundary = candidate.answer(fixture["boundary_probe"]["request"])
        absent = candidate.answer(fixture["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        candidate_runs.append({
            "baseline_regression": baseline_regression,
            "loaded_target": loaded_target,
            "loaded_regression": loaded_regression,
            "boundary": boundary,
            "absent": absent,
            "post_unload_target": post_unload_target,
        })

    specificity_responses: list[str] = []
    for order in fixture["specificity_orders"]:
        candidate = SpecificityFloorExclusionRoutingKernel()
        candidate.compose_quarantined_experts(
            [by_id[package_id] for package_id in order], reference_date=reference_date
        )
        specificity_responses.append(candidate.answer(fixture["specificity_probe"]["request"]))

    tie_responses: list[str] = []
    tie_control_responses: list[str] = []
    for order in fixture["tie_orders"]:
        candidate = SpecificityFloorExclusionRoutingKernel()
        candidate.compose_quarantined_experts(
            [by_id[package_id] for package_id in order], reference_date=reference_date
        )
        tie_responses.append(candidate.answer(fixture["tie_probe"]["request"]))
        tie_control_responses.append(candidate.answer(fixture["tie_control_probe"]["request"]))

    return {
        "baseline_target": baseline_target,
        "candidate_runs": candidate_runs,
        "specificity_responses": specificity_responses,
        "tie_responses": tie_responses,
        "tie_control_responses": tie_control_responses,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    targets = fixture["held_out_target"]
    expected_baseline = [case["expected_baseline"] for case in targets]
    expected_candidate = [case["expected_candidate"] for case in targets]
    expected_unloaded = [case["expected_unloaded"] for case in targets]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first, second = trial["candidate_runs"]
    floor_indexes = [
        index for index, case in enumerate(targets) if case["policy"].startswith("floor-")
    ]
    delegation_indexes = [
        index for index, case in enumerate(targets) if case["policy"].startswith("delegate-")
    ]
    all_excluded_indexes = [
        index
        for index, case in enumerate(targets)
        if case["policy"].startswith("all-excluded-")
    ]
    baseline_correct = sum(
        actual == expected
        for actual, expected in zip(trial["baseline_target"], expected_candidate)
    )
    candidate_correct = sum(
        actual == expected for actual, expected in zip(first["loaded_target"], expected_candidate)
    )
    target_count = len(targets)
    return {
        "target_count": target_count,
        "baseline_policy_outputs_correct": trial["baseline_target"] == expected_baseline,
        "baseline_target_correct": baseline_correct,
        "baseline_broader_fallbacks": sum(
            trial["baseline_target"][index] == expected_baseline[index]
            and trial["baseline_target"][index] != expected_candidate[index]
            for index in floor_indexes
        ),
        "candidate_target_correct": candidate_correct,
        "target_accuracy_gain": round((candidate_correct - baseline_correct) / target_count, 6),
        "candidate_specificity_floor_denials": sum(
            first["loaded_target"][index] == "route-error:scope-excluded"
            for index in floor_indexes
        ),
        "candidate_delegations_preserved": sum(
            first["loaded_target"][index] == expected_candidate[index]
            for index in delegation_indexes
        ),
        "candidate_all_excluded_denials": sum(
            first["loaded_target"][index] == "route-error:scope-excluded"
            for index in all_excluded_indexes
        ),
        "regression_count": len(expected_regression),
        "baseline_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["baseline_regression"], expected_regression)
        ),
        "candidate_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["loaded_regression"], expected_regression)
        ),
        "candidate_order_invariant": first == second,
        "literal_specificity_selections": sum(
            response == fixture["specificity_probe"]["expected"]
            for response in trial["specificity_responses"]
        ),
        "equal_specificity_rejections": sum(
            response == fixture["tie_probe"]["expected"] for response in trial["tie_responses"]
        ),
        "post_ambiguity_controls": sum(
            response == fixture["tie_control_probe"]["expected"]
            for response in trial["tie_control_responses"]
        ),
        "boundary_rejections": sum(
            run["boundary"] == fixture["boundary_probe"]["expected"]
            for run in trial["candidate_runs"]
        ),
        "absent_scope_rejections": sum(
            run["absent"] == fixture["absent_scope_probe"]["expected"]
            for run in trial["candidate_runs"]
        ),
        "rollback_matches_baseline": sum(
            actual == expected
            for actual, expected in zip(first["post_unload_target"], expected_unloaded)
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
        and summary["baseline_target_correct"] == 6
        and summary["baseline_broader_fallbacks"] == 2
        and summary["candidate_target_correct"] == summary["target_count"] == 8
        and summary["target_accuracy_gain"] == 0.25
        and summary["candidate_specificity_floor_denials"] == 2
        and summary["candidate_delegations_preserved"] == 2
        and summary["candidate_all_excluded_denials"] == 2
        and summary["baseline_regression_correct"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["candidate_order_invariant"]
        and summary["literal_specificity_selections"] == 2
        and summary["equal_specificity_rejections"] == 2
        and summary["post_ambiguity_controls"] == 2
        and summary["boundary_rejections"] == 2
        and summary["absent_scope_rejections"] == 2
        and summary["rollback_matches_baseline"] == summary["target_count"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
