#!/usr/bin/env python3
"""Evaluate exclusion isolation among equal-specificity expert candidates."""

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
from scripts.evaluate_specificity_floor_exclusion_routing import (  # noqa: E402
    SpecificityFloorExclusionRoutingKernel,
)
from scripts.evaluate_wildcard_scope_routing import (  # noqa: E402
    _pattern_segments,
    _validated_cases,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_equal_specificity_exclusion_cases.json"


class PreExclusionAmbiguityKernel(SpecificityFloorExclusionRoutingKernel):
    """Fail on a top-score tie before package-owned exclusions are evaluated."""

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
            top = [candidate for candidate in matching if candidate[0] == specificity_floor]
            if len(top) != 1:
                return "route-error:ambiguous-specificity"
            package_id = top[0][2]
            if any(
                _matches_pattern(exclusion, request_segments)
                for exclusion in self._exclusions_by_package[package_id]
            ):
                return "route-error:scope-excluded"
            return self._knowledge_by_package[package_id].get(local_id, "unknown")
        return super().answer(request)


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "packages", "compatible_package_ids",
        "compatible_orders", "held_out_target", "held_out_regression",
        "boundary_probe", "absent_scope_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-equal-specificity-exclusion-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    packages = fixture["packages"]
    if not isinstance(packages, list) or len(packages) != 3:
        raise ValueError("fixture must contain exactly three packages")
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
    if compatible_ids != package_ids:
        raise ValueError("compatible_package_ids must preserve package fixture order")
    if fixture["compatible_orders"] != [compatible_ids, list(reversed(compatible_ids))]:
        raise ValueError("compatible_orders must contain the package list and its reversal")

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
        "isolate-exact": 1,
        "isolate-wildcard": 1,
        "two-eligible-exact": 1,
        "two-eligible-wildcard": 1,
        "all-excluded-exact": 1,
        "all-excluded-wildcard": 1,
        "floor-exact": 1,
        "floor-wildcard": 1,
    }
    if any(policies.count(policy) != count for policy, count in expected_policies.items()):
        raise ValueError("target policies do not match the locked protocol")
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


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _packages_by_id(fixture)
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]

    order_runs: list[dict[str, Any]] = []
    for order in fixture["compatible_orders"]:
        packages = [by_id[package_id] for package_id in order]

        baseline = PreExclusionAmbiguityKernel()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        baseline_target = [baseline.answer(case["request"]) for case in targets]

        candidate = SpecificityFloorExclusionRoutingKernel()
        unloaded_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(packages, reference_date=reference_date)
        candidate_target = [candidate.answer(case["request"]) for case in targets]
        candidate_regression = [candidate.answer(case["request"]) for case in regressions]
        boundary = candidate.answer(fixture["boundary_probe"]["request"])
        absent = candidate.answer(fixture["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        order_runs.append({
            "baseline_target": baseline_target,
            "unloaded_regression": unloaded_regression,
            "candidate_target": candidate_target,
            "candidate_regression": candidate_regression,
            "boundary": boundary,
            "absent": absent,
            "post_unload_target": post_unload_target,
        })
    return {"order_runs": order_runs}


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    targets = fixture["held_out_target"]
    expected_baseline = [case["expected_baseline"] for case in targets]
    expected_candidate = [case["expected_candidate"] for case in targets]
    expected_unloaded = [case["expected_unloaded"] for case in targets]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first, second = trial["order_runs"]
    indexes = {
        prefix: [
            index for index, case in enumerate(targets) if case["policy"].startswith(prefix)
        ]
        for prefix in ("isolate-", "two-eligible-", "all-excluded-", "floor-")
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
    return {
        "target_count": target_count,
        "baseline_policy_outputs_correct": all(
            run["baseline_target"] == expected_baseline for run in trial["order_runs"]
        ),
        "baseline_target_correct": baseline_correct,
        "baseline_pre_exclusion_ambiguities": sum(
            response == "route-error:ambiguous-specificity"
            for response in first["baseline_target"]
        ),
        "candidate_target_correct": candidate_correct,
        "target_accuracy_gain": round((candidate_correct - baseline_correct) / target_count, 6),
        "candidate_isolated_selections": sum(
            first["candidate_target"][index] == expected_candidate[index]
            for index in indexes["isolate-"]
        ),
        "candidate_two_eligible_ambiguities": sum(
            first["candidate_target"][index] == "route-error:ambiguous-specificity"
            for index in indexes["two-eligible-"]
        ),
        "candidate_all_excluded_denials": sum(
            first["candidate_target"][index] == "route-error:scope-excluded"
            for index in indexes["all-excluded-"]
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
        "baseline_order_invariant": first["baseline_target"] == second["baseline_target"],
        "candidate_order_invariant": first["candidate_target"] == second["candidate_target"]
        and first["candidate_regression"] == second["candidate_regression"],
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
        and summary["baseline_target_correct"] == 4
        and summary["baseline_pre_exclusion_ambiguities"] == 6
        and summary["candidate_target_correct"] == summary["target_count"] == 8
        and summary["target_accuracy_gain"] == 0.5
        and summary["candidate_isolated_selections"] == 2
        and summary["candidate_two_eligible_ambiguities"] == 2
        and summary["candidate_all_excluded_denials"] == 2
        and summary["candidate_floor_denials"] == 2
        and summary["unloaded_regression_correct"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["baseline_order_invariant"]
        and summary["candidate_order_invariant"]
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
