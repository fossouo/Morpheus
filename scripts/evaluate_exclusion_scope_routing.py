#!/usr/bin/env python3
"""Evaluate exclusion precedence for quarantined wildcard-routed experts."""

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

from scripts.evaluate_expert_composition import _validated_package_records  # noqa: E402
from scripts.evaluate_hierarchical_scope_routing import _scope_segments  # noqa: E402
from scripts.evaluate_wildcard_scope_routing import (  # noqa: E402
    WildcardScopeRoutingKernel,
    _pattern_segments,
    _validate_reversed_orders,
    _validated_cases,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_exclusion_scope_routing_cases.json"


def _matches_pattern(pattern: str, request_segments: tuple[str, ...]) -> bool:
    pattern_segments = _pattern_segments(pattern)
    return len(request_segments) >= len(pattern_segments) and all(
        declared == "*" or declared == actual
        for declared, actual in zip(pattern_segments, request_segments)
    )


class ExclusionScopeRoutingKernel(WildcardScopeRoutingKernel):
    """A fixed wildcard router that evaluates loaded exclusions before lookup."""

    def __init__(self) -> None:
        super().__init__()
        self._exclusion_patterns: list[str] = []

    def answer(self, request: Any) -> str:
        if isinstance(request, dict) and request.get("operation") == "scope_recall":
            if set(request) != {"operation", "scope", "local_id"}:
                raise ValueError("unsupported request")
            request_segments = _scope_segments(request["scope"])
            local_id = request["local_id"]
            if not isinstance(local_id, str) or not local_id:
                raise ValueError("local_id must be a non-empty string")
            if any(
                _matches_pattern(pattern, request_segments)
                for pattern in self._exclusion_patterns
            ):
                return "route-error:scope-excluded"
        return super().answer(request)

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if self._knowledge_by_package or self._package_by_scope or self._exclusion_patterns:
            raise ValueError("experts are already loaded")
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")

        proposed_knowledge: dict[str, dict[str, str]] = {}
        proposed_patterns: dict[str, str] = {}
        proposed_exclusions: list[str] = []
        for package in packages:
            package_id, records = _validated_package_records(
                package, reference_date=reference_date
            )
            if package_id in proposed_knowledge:
                raise ValueError(f"duplicate-package-id:{package_id}")
            for pattern in package["manifest"]["scope"]["include"]:
                _pattern_segments(pattern)
                if pattern in proposed_patterns:
                    raise ValueError(
                        f"duplicate-scope-pattern:{pattern}:"
                        f"{proposed_patterns[pattern]}:{package_id}"
                    )
                proposed_patterns[pattern] = package_id
            for pattern in package["manifest"]["scope"]["exclude"]:
                _pattern_segments(pattern)
                proposed_exclusions.append(pattern)
            proposed_knowledge[package_id] = records

        self._knowledge_by_package = proposed_knowledge
        self._package_by_scope = proposed_patterns
        self._exclusion_patterns = proposed_exclusions

    def unload_experts(self) -> None:
        super().unload_experts()
        self._exclusion_patterns = []


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "packages", "compatible_package_ids",
        "compatible_orders", "specificity_orders", "tie_orders", "held_out_target",
        "held_out_regression", "specificity_probe", "tie_probe", "tie_control_probe",
        "tie_exclusion_probe", "boundary_probe", "absent_scope_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-exclusion-scope-routing-cases-v1":
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
    if policies.count("allow") != 3 or policies.count("exact-exclude") != 3 or policies.count(
        "wildcard-exclude"
    ) != 2:
        raise ValueError("target policies must lock three allows and five exclusions")
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
        "specificity_probe", "tie_probe", "tie_control_probe", "tie_exclusion_probe",
        "boundary_probe", "absent_scope_probe",
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
        baseline = WildcardScopeRoutingKernel()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        if index == 0:
            baseline_target = [baseline.answer(case["request"]) for case in targets]

        candidate = ExclusionScopeRoutingKernel()
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
        candidate = ExclusionScopeRoutingKernel()
        candidate.compose_quarantined_experts(
            [by_id[package_id] for package_id in order], reference_date=reference_date
        )
        specificity_responses.append(candidate.answer(fixture["specificity_probe"]["request"]))

    tie_responses: list[str] = []
    tie_control_responses: list[str] = []
    tie_exclusion_responses: list[str] = []
    for order in fixture["tie_orders"]:
        candidate = ExclusionScopeRoutingKernel()
        candidate.compose_quarantined_experts(
            [by_id[package_id] for package_id in order], reference_date=reference_date
        )
        tie_responses.append(candidate.answer(fixture["tie_probe"]["request"]))
        tie_control_responses.append(candidate.answer(fixture["tie_control_probe"]["request"]))
        tie_exclusion_responses.append(
            candidate.answer(fixture["tie_exclusion_probe"]["request"])
        )

    return {
        "baseline_target": baseline_target,
        "candidate_runs": candidate_runs,
        "specificity_responses": specificity_responses,
        "tie_responses": tie_responses,
        "tie_control_responses": tie_control_responses,
        "tie_exclusion_responses": tie_exclusion_responses,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    targets = fixture["held_out_target"]
    expected_baseline = [case["expected_baseline"] for case in targets]
    expected_candidate = [case["expected_candidate"] for case in targets]
    expected_unloaded = [case["expected_unloaded"] for case in targets]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first, second = trial["candidate_runs"]
    target_count = len(expected_candidate)
    regression_count = len(expected_regression)
    baseline_target_correct = sum(
        actual == expected for actual, expected in zip(trial["baseline_target"], expected_candidate)
    )
    candidate_target_correct = sum(
        actual == expected for actual, expected in zip(first["loaded_target"], expected_candidate)
    )
    excluded_indexes = [index for index, case in enumerate(targets) if case["policy"] != "allow"]
    exact_indexes = [index for index, case in enumerate(targets) if case["policy"] == "exact-exclude"]
    wildcard_indexes = [
        index for index, case in enumerate(targets) if case["policy"] == "wildcard-exclude"
    ]
    return {
        "target_count": target_count,
        "baseline_policy_outputs_correct": trial["baseline_target"] == expected_baseline,
        "baseline_target_correct": baseline_target_correct,
        "baseline_excluded_values_returned": sum(
            trial["baseline_target"][index] not in {
                "route-error:scope-excluded", "route-error:scope-not-found"
            }
            for index in excluded_indexes
        ),
        "candidate_target_correct": candidate_target_correct,
        "target_accuracy_gain": round(
            (candidate_target_correct - baseline_target_correct) / target_count, 6
        ),
        "candidate_exact_exclusion_denials": sum(
            first["loaded_target"][index] == "route-error:scope-excluded"
            for index in exact_indexes
        ),
        "candidate_wildcard_exclusion_denials": sum(
            first["loaded_target"][index] == "route-error:scope-excluded"
            for index in wildcard_indexes
        ),
        "regression_count": regression_count,
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
        "exclusion_over_tie_denials": sum(
            response == fixture["tie_exclusion_probe"]["expected"]
            for response in trial["tie_exclusion_responses"]
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
        and summary["baseline_target_correct"] == 3
        and summary["baseline_excluded_values_returned"] == 5
        and summary["candidate_target_correct"] == summary["target_count"] == 8
        and summary["target_accuracy_gain"] == 0.625
        and summary["candidate_exact_exclusion_denials"] == 3
        and summary["candidate_wildcard_exclusion_denials"] == 2
        and summary["baseline_regression_correct"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["candidate_order_invariant"]
        and summary["literal_specificity_selections"] == 2
        and summary["equal_specificity_rejections"] == 2
        and summary["post_ambiguity_controls"] == 2
        and summary["exclusion_over_tie_denials"] == 2
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
