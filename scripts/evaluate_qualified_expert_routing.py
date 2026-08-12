#!/usr/bin/env python3
"""Evaluate package-qualified routing for colliding local expert identifiers."""

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


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_qualified_routing_cases.json"


class QualifiedExpertKernel:
    """A fixed kernel with package-qualified, unloadable exact-match knowledge."""

    def __init__(self) -> None:
        self._knowledge_by_package: dict[str, dict[str, str]] = {}

    def answer(self, request: Any) -> str:
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        operation = request.get("operation")
        if operation == "echo" and set(request) == {"operation", "value"}:
            value = request["value"]
            if not isinstance(value, str):
                raise ValueError("echo value must be a string")
            return value
        if operation == "qualified_recall" and set(request) == {
            "operation",
            "package_id",
            "local_id",
        }:
            package_id = request["package_id"]
            local_id = request["local_id"]
            if not isinstance(package_id, str) or not package_id:
                raise ValueError("package_id must be a non-empty string")
            if not isinstance(local_id, str) or not local_id:
                raise ValueError("local_id must be a non-empty string")
            return self._knowledge_by_package.get(package_id, {}).get(local_id, "unknown")
        raise ValueError("unsupported request")

    def unload_experts(self) -> None:
        self._knowledge_by_package = {}

    def _validated_packages(
        self, packages: Any, *, reference_date: date
    ) -> list[tuple[str, dict[str, str]]]:
        if self._knowledge_by_package:
            raise ValueError("experts are already loaded")
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")
        validated: list[tuple[str, dict[str, str]]] = []
        package_ids: set[str] = set()
        for package in packages:
            package_id, records = _validated_package_records(
                package, reference_date=reference_date
            )
            if package_id in package_ids:
                raise ValueError(f"duplicate-package-id:{package_id}")
            package_ids.add(package_id)
            validated.append((package_id, records))
        return validated


class CollisionRejectingQualifiedKernel(QualifiedExpertKernel):
    """EXP-013 policy baseline: reject repeated local IDs across packages."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        validated = self._validated_packages(packages, reference_date=reference_date)
        owners: dict[str, str] = {}
        proposed: dict[str, dict[str, str]] = {}
        for package_id, records in validated:
            for local_id in records:
                if local_id in owners:
                    raise ValueError(
                        "cross-package-knowledge-collision:"
                        f"{local_id}:{owners[local_id]}:{package_id}"
                    )
                owners[local_id] = package_id
            proposed[package_id] = records
        self._knowledge_by_package = proposed


class PackageQualifiedExpertKernel(QualifiedExpertKernel):
    """Candidate policy: route by the tuple (package_id, local_id)."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        validated = self._validated_packages(packages, reference_date=reference_date)
        proposed = {package_id: records for package_id, records in validated}
        # State changes only after every package is valid and package IDs are unique.
        self._knowledge_by_package = proposed


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema",
        "reference_date",
        "packages",
        "composition_orders",
        "shared_local_id",
        "held_out_target",
        "held_out_regression",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-qualified-routing-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    packages = fixture["packages"]
    if not isinstance(packages, list) or len(packages) != 2:
        raise ValueError("fixture must contain exactly two packages")
    package_ids: list[str] = []
    records_by_package: dict[str, dict[str, str]] = {}
    for package in packages:
        package_id, records = _validated_package_records(
            package, reference_date=reference_date
        )
        if package_id in package_ids:
            raise ValueError("package ids must be unique")
        package_ids.append(package_id)
        records_by_package[package_id] = records

    orders = fixture["composition_orders"]
    if (
        not isinstance(orders, list)
        or len(orders) != 2
        or orders[0] != package_ids
        or orders[1] != list(reversed(package_ids))
    ):
        raise ValueError("composition_orders must contain package order and its reversal")

    shared_local_id = fixture["shared_local_id"]
    if not isinstance(shared_local_id, str) or not shared_local_id:
        raise ValueError("shared_local_id must be a non-empty string")
    if any(shared_local_id not in records for records in records_by_package.values()):
        raise ValueError("shared_local_id must occur in both packages")

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 4:
        raise ValueError("fixture must contain exactly four target cases")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise ValueError("fixture must contain exactly three regression cases")
    target_ids = _validate_cases(
        targets, {"id", "request", "expected_unloaded", "expected_loaded"}
    )
    regression_ids = _validate_cases(regressions, {"id", "request", "expected"})

    declared_target_ids: list[str] = []
    for package in packages:
        declared_target_ids.extend(package["manifest"]["tests"]["target"])
        if package["manifest"]["tests"]["held_out_regression"] != regression_ids:
            raise ValueError("regression case ids must match every package manifest")
    if declared_target_ids != target_ids:
        raise ValueError("target case ids must match package manifests in fixture order")

    shared_requests = [
        case["request"]
        for case in targets
        if case["request"].get("local_id") == shared_local_id
    ]
    if len(shared_requests) != 2 or {
        request.get("package_id") for request in shared_requests
    } != set(package_ids):
        raise ValueError("targets must route the shared local id to both packages")


def _validate_cases(cases: list[Any], keys: set[str]) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != keys:
            raise ValueError("case has unexpected structure")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("case ids must be non-empty and unique")
        seen.add(case_id)
        ids.append(case_id)
        if not isinstance(case["request"], dict):
            raise ValueError("case request must be an object")
        if any(not isinstance(case[key], str) for key in keys - {"id", "request"}):
            raise ValueError("expected responses must be strings")
    return ids


def _packages_by_id(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        package["manifest"]["package_id"]: package for package in fixture["packages"]
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _packages_by_id(fixture)
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]

    baseline_rejections: list[bool] = []
    baseline_targets: list[list[str]] = []
    for order in fixture["composition_orders"]:
        baseline = CollisionRejectingQualifiedKernel()
        try:
            baseline.compose_quarantined_experts(
                [by_id[package_id] for package_id in order],
                reference_date=reference_date,
            )
        except ValueError as exc:
            baseline_rejections.append(
                str(exc).startswith("cross-package-knowledge-collision:")
            )
        else:
            baseline_rejections.append(False)
        baseline_targets.append([baseline.answer(case["request"]) for case in targets])

    candidate_runs: list[dict[str, list[str]]] = []
    for order in fixture["composition_orders"]:
        candidate = PackageQualifiedExpertKernel()
        baseline_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(
            [by_id[package_id] for package_id in order], reference_date=reference_date
        )
        loaded_target = [candidate.answer(case["request"]) for case in targets]
        loaded_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        candidate_runs.append(
            {
                "baseline_regression": baseline_regression,
                "loaded_target": loaded_target,
                "loaded_regression": loaded_regression,
                "post_unload_target": post_unload_target,
            }
        )

    return {
        "baseline_rejections": baseline_rejections,
        "baseline_targets": baseline_targets,
        "candidate_runs": candidate_runs,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    expected_loaded = [case["expected_loaded"] for case in fixture["held_out_target"]]
    expected_unloaded = [case["expected_unloaded"] for case in fixture["held_out_target"]]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first_candidate = trial["candidate_runs"][0]
    second_candidate = trial["candidate_runs"][1]
    target_count = len(expected_loaded)
    regression_count = len(expected_regression)
    baseline_target_correct = sum(
        actual == expected
        for actual, expected in zip(trial["baseline_targets"][0], expected_loaded)
    )
    candidate_target_correct = sum(
        actual == expected
        for actual, expected in zip(first_candidate["loaded_target"], expected_loaded)
    )
    shared_outputs = [
        actual
        for case, actual in zip(fixture["held_out_target"], first_candidate["loaded_target"])
        if case["request"].get("local_id") == fixture["shared_local_id"]
    ]
    baseline_regression_correct = sum(
        actual == expected
        for actual, expected in zip(
            first_candidate["baseline_regression"], expected_regression
        )
    )
    candidate_regression_correct = sum(
        actual == expected
        for actual, expected in zip(first_candidate["loaded_regression"], expected_regression)
    )
    return {
        "target_count": target_count,
        "baseline_target_correct": baseline_target_correct,
        "candidate_target_correct": candidate_target_correct,
        "target_accuracy_gain": round(
            (candidate_target_correct - baseline_target_correct) / target_count, 6
        ),
        "regression_count": regression_count,
        "baseline_regression_correct": baseline_regression_correct,
        "candidate_regression_correct": candidate_regression_correct,
        "regression_accuracy_drop": round(
            (baseline_regression_correct - candidate_regression_correct) / regression_count,
            6,
        ),
        "baseline_collision_rejections": sum(trial["baseline_rejections"]),
        "baseline_clean_states": sum(
            outputs == expected_unloaded for outputs in trial["baseline_targets"]
        ),
        "shared_local_id_distinct_routes": len(set(shared_outputs)),
        "candidate_order_invariant": first_candidate["loaded_target"]
        == second_candidate["loaded_target"]
        and first_candidate["loaded_regression"]
        == second_candidate["loaded_regression"],
        "rollback_matches_baseline": sum(
            actual == expected
            for actual, expected in zip(
                first_candidate["post_unload_target"], expected_unloaded
            )
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
        summary["baseline_target_correct"] == 0
        and summary["candidate_target_correct"] == summary["target_count"] == 4
        and summary["target_accuracy_gain"] == 1.0
        and summary["baseline_regression_correct"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["regression_accuracy_drop"] == 0.0
        and summary["baseline_collision_rejections"] == 2
        and summary["baseline_clean_states"] == 2
        and summary["shared_local_id_distinct_routes"] == 2
        and summary["candidate_order_invariant"]
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
