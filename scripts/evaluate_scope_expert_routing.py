#!/usr/bin/env python3
"""Evaluate exact declared-scope routing without caller package identity."""

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


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_scope_routing_cases.json"


class ScopeRoutingKernel:
    """A fixed kernel that routes exact scopes to unloadable package knowledge."""

    def __init__(self) -> None:
        self._knowledge_by_package: dict[str, dict[str, str]] = {}
        self._package_by_scope: dict[str, str] = {}

    def answer(self, request: Any) -> str:
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        operation = request.get("operation")
        if operation == "echo" and set(request) == {"operation", "value"}:
            value = request["value"]
            if not isinstance(value, str):
                raise ValueError("echo value must be a string")
            return value
        if operation == "scope_recall" and set(request) == {
            "operation",
            "scope",
            "local_id",
        }:
            scope = request["scope"]
            local_id = request["local_id"]
            if not isinstance(scope, str) or not scope:
                raise ValueError("scope must be a non-empty string")
            if not isinstance(local_id, str) or not local_id:
                raise ValueError("local_id must be a non-empty string")
            package_id = self._package_by_scope.get(scope)
            if package_id is None:
                return "route-error:scope-not-found"
            return self._knowledge_by_package[package_id].get(local_id, "unknown")
        raise ValueError("unsupported request")

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if self._knowledge_by_package or self._package_by_scope:
            raise ValueError("experts are already loaded")
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")

        proposed_knowledge: dict[str, dict[str, str]] = {}
        proposed_scopes: dict[str, str] = {}
        for package in packages:
            package_id, records = _validated_package_records(
                package, reference_date=reference_date
            )
            if package_id in proposed_knowledge:
                raise ValueError(f"duplicate-package-id:{package_id}")
            include = package["manifest"]["scope"]["include"]
            for scope in include:
                if scope in proposed_scopes:
                    raise ValueError(
                        f"ambiguous-scope:{scope}:{proposed_scopes[scope]}:{package_id}"
                    )
                proposed_scopes[scope] = package_id
            proposed_knowledge[package_id] = records

        # Commit only after every package and scope has passed preflight.
        self._knowledge_by_package = proposed_knowledge
        self._package_by_scope = proposed_scopes

    def unload_experts(self) -> None:
        self._knowledge_by_package = {}
        self._package_by_scope = {}


class ExplicitQualificationBaseline(ScopeRoutingKernel):
    """EXP-014 policy baseline: a scope-only request cannot select a package."""

    def answer(self, request: Any) -> str:
        if isinstance(request, dict) and request.get("operation") == "scope_recall":
            if set(request) != {"operation", "scope", "local_id"}:
                raise ValueError("unsupported request")
            return "route-error:package-id-required"
        return super().answer(request)


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def _validated_cases(cases: Any, keys: set[str]) -> list[str]:
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    ids: list[str] = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != keys:
            raise ValueError("case has unexpected structure")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("case ids must be non-empty and unique")
        ids.append(case_id)
        if not isinstance(case["request"], dict):
            raise ValueError("case request must be an object")
        if any(not isinstance(case[key], str) for key in keys - {"id", "request"}):
            raise ValueError("expected responses must be strings")
    return ids


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema",
        "reference_date",
        "packages",
        "compatible_package_ids",
        "compatible_orders",
        "conflict_orders",
        "held_out_target",
        "held_out_regression",
        "absent_scope_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-scope-routing-cases-v1":
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

    conflict_orders = fixture["conflict_orders"]
    if (
        not isinstance(conflict_orders, list)
        or len(conflict_orders) != 2
        or any(not isinstance(order, list) or len(order) != 2 for order in conflict_orders)
        or conflict_orders[1] != list(reversed(conflict_orders[0]))
        or any(package_id not in package_ids for order in conflict_orders for package_id in order)
    ):
        raise ValueError("conflict_orders must contain a package pair and its reversal")

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 4:
        raise ValueError("fixture must contain exactly four target cases")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise ValueError("fixture must contain exactly three regression cases")
    target_ids = _validated_cases(
        targets, {"id", "request", "expected_baseline", "expected_candidate", "expected_unloaded"}
    )
    regression_ids = _validated_cases(regressions, {"id", "request", "expected"})
    declared_targets: list[str] = []
    by_id = {package["manifest"]["package_id"]: package for package in packages}
    for package_id in compatible_ids:
        manifest = by_id[package_id]["manifest"]
        declared_targets.extend(manifest["tests"]["target"])
        if manifest["tests"]["held_out_regression"] != regression_ids:
            raise ValueError("regression ids must match compatible package manifests")
    if declared_targets != target_ids:
        raise ValueError("target ids must match compatible manifests in fixture order")

    probe = fixture["absent_scope_probe"]
    if not isinstance(probe, dict) or set(probe) != {"request", "expected"}:
        raise ValueError("absent_scope_probe has unexpected structure")
    if not isinstance(probe["request"], dict) or not isinstance(probe["expected"], str):
        raise ValueError("invalid absent_scope_probe")


def _packages_by_id(fixture: dict[str, Any]) -> dict[str, Any]:
    return {package["manifest"]["package_id"]: package for package in fixture["packages"]}


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _packages_by_id(fixture)
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]

    candidate_runs: list[dict[str, list[str] | str]] = []
    baseline_target: list[str] = []
    for index, order in enumerate(fixture["compatible_orders"]):
        packages = [by_id[package_id] for package_id in order]
        baseline = ExplicitQualificationBaseline()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        if index == 0:
            baseline_target = [baseline.answer(case["request"]) for case in targets]

        candidate = ScopeRoutingKernel()
        baseline_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(packages, reference_date=reference_date)
        loaded_target = [candidate.answer(case["request"]) for case in targets]
        loaded_regression = [candidate.answer(case["request"]) for case in regressions]
        absent_scope = candidate.answer(fixture["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        candidate_runs.append(
            {
                "baseline_regression": baseline_regression,
                "loaded_target": loaded_target,
                "loaded_regression": loaded_regression,
                "absent_scope": absent_scope,
                "post_unload_target": post_unload_target,
            }
        )

    conflict_rejections: list[bool] = []
    conflict_clean_states: list[bool] = []
    for order in fixture["conflict_orders"]:
        candidate = ScopeRoutingKernel()
        try:
            candidate.compose_quarantined_experts(
                [by_id[package_id] for package_id in order],
                reference_date=reference_date,
            )
        except ValueError as exc:
            conflict_rejections.append(str(exc).startswith("ambiguous-scope:"))
        else:
            conflict_rejections.append(False)
        conflict_clean_states.append(
            candidate.answer(fixture["held_out_target"][0]["request"])
            == "route-error:scope-not-found"
        )

    return {
        "baseline_target": baseline_target,
        "candidate_runs": candidate_runs,
        "conflict_rejections": conflict_rejections,
        "conflict_clean_states": conflict_clean_states,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    expected_baseline = [case["expected_baseline"] for case in fixture["held_out_target"]]
    expected_candidate = [case["expected_candidate"] for case in fixture["held_out_target"]]
    expected_unloaded = [case["expected_unloaded"] for case in fixture["held_out_target"]]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first = trial["candidate_runs"][0]
    second = trial["candidate_runs"][1]
    target_count = len(expected_candidate)
    regression_count = len(expected_regression)
    baseline_target_correct = sum(
        actual == expected for actual, expected in zip(trial["baseline_target"], expected_candidate)
    )
    candidate_target_correct = sum(
        actual == expected for actual, expected in zip(first["loaded_target"], expected_candidate)
    )
    return {
        "target_count": target_count,
        "baseline_policy_outputs_correct": trial["baseline_target"] == expected_baseline,
        "baseline_target_correct": baseline_target_correct,
        "candidate_target_correct": candidate_target_correct,
        "target_accuracy_gain": round((candidate_target_correct - baseline_target_correct) / target_count, 6),
        "regression_count": regression_count,
        "baseline_regression_correct": sum(
            actual == expected for actual, expected in zip(first["baseline_regression"], expected_regression)
        ),
        "candidate_regression_correct": sum(
            actual == expected for actual, expected in zip(first["loaded_regression"], expected_regression)
        ),
        "candidate_order_invariant": first["loaded_target"] == second["loaded_target"]
        and first["loaded_regression"] == second["loaded_regression"],
        "ambiguous_scope_rejections": sum(trial["conflict_rejections"]),
        "ambiguous_scope_clean_states": sum(trial["conflict_clean_states"]),
        "absent_scope_rejections": sum(
            run["absent_scope"] == fixture["absent_scope_probe"]["expected"]
            for run in trial["candidate_runs"]
        ),
        "rollback_matches_baseline": sum(
            actual == expected for actual, expected in zip(first["post_unload_target"], expected_unloaded)
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
    summary.update(
        {
            "repeatable": first == repeated,
            "fixture_bytes": args.fixture.stat().st_size,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["baseline_policy_outputs_correct"]
        and summary["baseline_target_correct"] == 0
        and summary["candidate_target_correct"] == summary["target_count"] == 4
        and summary["target_accuracy_gain"] == 1.0
        and summary["baseline_regression_correct"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["candidate_order_invariant"]
        and summary["ambiguous_scope_rejections"] == 2
        and summary["ambiguous_scope_clean_states"] == 2
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
