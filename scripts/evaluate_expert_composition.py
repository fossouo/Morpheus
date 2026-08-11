#!/usr/bin/env python3
"""Evaluate transactional composition of quarantined synthetic experts."""

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

from scripts.evaluate_expert_lookup import (  # noqa: E402
    StableKernel,
    _validate_knowledge_records,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_composition_cases.json"


def _validated_package_records(
    package: Any, *, reference_date: date
) -> tuple[str, dict[str, str]]:
    if not isinstance(package, dict) or set(package) != {"manifest", "knowledge_records"}:
        raise ValueError("package must contain only manifest and knowledge_records")
    manifest = package["manifest"]
    errors = validate_manifest(manifest, reference_date=reference_date)
    if errors:
        raise ValueError(f"invalid expert manifest: {errors}")
    if any(source["kind"] != "synthetic" for source in manifest["provenance"]):
        raise ValueError("this evaluator permits synthetic provenance only")
    records = _validate_knowledge_records(package["knowledge_records"])
    if set(records) != set(manifest["layers"]["knowledge"]):
        raise ValueError("knowledge records must exactly match declared knowledge ids")
    return manifest["package_id"], records


class TransactionalExpertKernel(StableKernel):
    """A stable kernel that atomically composes collision-free expert knowledge."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if self._knowledge:
            raise ValueError("experts are already loaded")
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")

        package_ids: set[str] = set()
        merged: dict[str, str] = {}
        owners: dict[str, str] = {}
        for package in packages:
            package_id, records = _validated_package_records(
                package, reference_date=reference_date
            )
            if package_id in package_ids:
                raise ValueError(f"duplicate-package-id:{package_id}")
            package_ids.add(package_id)
            for record_id, value in records.items():
                if record_id in owners:
                    raise ValueError(
                        "cross-package-knowledge-collision:"
                        f"{record_id}:{owners[record_id]}:{package_id}"
                    )
                owners[record_id] = package_id
                merged[record_id] = value

        # State changes only after every package and cross-package identifier passes.
        self._knowledge = merged


class LastWriteWinsKernel(StableKernel):
    """Frozen baseline that sequentially overwrites colliding knowledge IDs."""

    def load_sequentially(self, packages: list[Any], *, reference_date: date) -> None:
        for package in packages:
            _, records = _validated_package_records(package, reference_date=reference_date)
            self._knowledge.update(records)


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema",
        "reference_date",
        "packages",
        "compatible_package_ids",
        "held_out_target",
        "held_out_regression",
        "conflict_orders",
        "conflict_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-composition-cases-v1":
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

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 4:
        raise ValueError("fixture must contain exactly four target cases")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise ValueError("fixture must contain exactly three regression cases")
    _validate_cases(targets, {"id", "request", "expected_unloaded", "expected_loaded"})
    _validate_cases(regressions, {"id", "request", "expected"})

    orders = fixture["conflict_orders"]
    if not isinstance(orders, list) or len(orders) != 2:
        raise ValueError("fixture must contain exactly two conflict orders")
    normalized_orders: list[list[str]] = []
    for order in orders:
        if not isinstance(order, dict) or set(order) != {"package_ids", "expected_baseline"}:
            raise ValueError("conflict order has unexpected structure")
        ids = order["package_ids"]
        if (
            not isinstance(ids, list)
            or len(ids) != 2
            or len(set(ids)) != 2
            or any(package_id not in package_ids for package_id in ids)
            or not isinstance(order["expected_baseline"], str)
        ):
            raise ValueError("invalid conflict order")
        normalized_orders.append(ids)
    if normalized_orders[1] != list(reversed(normalized_orders[0])):
        raise ValueError("conflict orders must be exact reversals")

    probe = fixture["conflict_probe"]
    if not isinstance(probe, dict) or set(probe) != {"request", "expected_candidate"}:
        raise ValueError("conflict_probe has unexpected structure")
    if not isinstance(probe["request"], dict) or not isinstance(
        probe["expected_candidate"], str
    ):
        raise ValueError("invalid conflict_probe")


def _validate_cases(cases: list[Any], keys: set[str]) -> None:
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != keys:
            raise ValueError("case has unexpected structure")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("case ids must be non-empty and unique")
        seen.add(case_id)
        if not isinstance(case["request"], dict):
            raise ValueError("case request must be an object")
        if any(not isinstance(case[key], str) for key in keys - {"id", "request"}):
            raise ValueError("expected responses must be strings")


def _packages_by_id(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        package["manifest"]["package_id"]: package for package in fixture["packages"]
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _packages_by_id(fixture)
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]

    unloaded = TransactionalExpertKernel()
    baseline_target = [unloaded.answer(case["request"]) for case in targets]
    baseline_regression = [unloaded.answer(case["request"]) for case in regressions]

    compatible_ids = fixture["compatible_package_ids"]
    compatible = [by_id[package_id] for package_id in compatible_ids]
    candidate = TransactionalExpertKernel()
    candidate.compose_quarantined_experts(compatible, reference_date=reference_date)
    composed_target = [candidate.answer(case["request"]) for case in targets]
    composed_regression = [candidate.answer(case["request"]) for case in regressions]
    candidate.unload_expert()
    post_unload_target = [candidate.answer(case["request"]) for case in targets]

    reversed_candidate = TransactionalExpertKernel()
    reversed_candidate.compose_quarantined_experts(
        list(reversed(compatible)), reference_date=reference_date
    )
    reversed_target = [reversed_candidate.answer(case["request"]) for case in targets]
    reversed_regression = [
        reversed_candidate.answer(case["request"]) for case in regressions
    ]

    candidate_rejections: list[bool] = []
    candidate_after_conflict: list[str] = []
    baseline_conflict_outputs: list[str] = []
    probe = fixture["conflict_probe"]["request"]
    for order in fixture["conflict_orders"]:
        packages = [by_id[package_id] for package_id in order["package_ids"]]
        conflict_candidate = TransactionalExpertKernel()
        try:
            conflict_candidate.compose_quarantined_experts(
                packages, reference_date=reference_date
            )
        except ValueError as exc:
            candidate_rejections.append(
                str(exc).startswith("cross-package-knowledge-collision:")
            )
        else:
            candidate_rejections.append(False)
        candidate_after_conflict.append(conflict_candidate.answer(probe))

        baseline = LastWriteWinsKernel()
        baseline.load_sequentially(packages, reference_date=reference_date)
        baseline_conflict_outputs.append(baseline.answer(probe))

    return {
        "baseline_target": baseline_target,
        "baseline_regression": baseline_regression,
        "composed_target": composed_target,
        "composed_regression": composed_regression,
        "post_unload_target": post_unload_target,
        "reversed_target": reversed_target,
        "reversed_regression": reversed_regression,
        "candidate_rejections": candidate_rejections,
        "candidate_after_conflict": candidate_after_conflict,
        "baseline_conflict_outputs": baseline_conflict_outputs,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    expected_loaded = [case["expected_loaded"] for case in fixture["held_out_target"]]
    expected_unloaded = [case["expected_unloaded"] for case in fixture["held_out_target"]]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    expected_baseline_conflicts = [
        order["expected_baseline"] for order in fixture["conflict_orders"]
    ]
    expected_candidate = fixture["conflict_probe"]["expected_candidate"]
    target_count = len(expected_loaded)
    regression_count = len(expected_regression)
    baseline_target_correct = sum(
        actual == expected
        for actual, expected in zip(trial["baseline_target"], expected_loaded)
    )
    composed_target_correct = sum(
        actual == expected
        for actual, expected in zip(trial["composed_target"], expected_loaded)
    )
    baseline_regression_correct = sum(
        actual == expected
        for actual, expected in zip(trial["baseline_regression"], expected_regression)
    )
    composed_regression_correct = sum(
        actual == expected
        for actual, expected in zip(trial["composed_regression"], expected_regression)
    )
    return {
        "target_count": target_count,
        "baseline_target_correct": baseline_target_correct,
        "composed_target_correct": composed_target_correct,
        "target_accuracy_gain": round(
            (composed_target_correct - baseline_target_correct) / target_count, 6
        ),
        "regression_count": regression_count,
        "baseline_regression_correct": baseline_regression_correct,
        "composed_regression_correct": composed_regression_correct,
        "regression_accuracy_drop": round(
            (baseline_regression_correct - composed_regression_correct) / regression_count,
            6,
        ),
        "rollback_matches_baseline": sum(
            actual == expected
            for actual, expected in zip(trial["post_unload_target"], expected_unloaded)
        ),
        "compatible_order_invariant": trial["composed_target"]
        == trial["reversed_target"]
        and trial["composed_regression"] == trial["reversed_regression"],
        "candidate_conflict_rejections": sum(trial["candidate_rejections"]),
        "candidate_conflict_state_clean": sum(
            actual == expected_candidate
            for actual in trial["candidate_after_conflict"]
        ),
        "baseline_conflict_outputs_correct": trial["baseline_conflict_outputs"]
        == expected_baseline_conflicts,
        "baseline_distinct_conflict_outputs": len(
            set(trial["baseline_conflict_outputs"])
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
        and summary["composed_target_correct"] == summary["target_count"] == 4
        and summary["target_accuracy_gain"] == 1.0
        and summary["baseline_regression_correct"]
        == summary["composed_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["regression_accuracy_drop"] == 0.0
        and summary["rollback_matches_baseline"] == summary["target_count"]
        and summary["compatible_order_invariant"]
        and summary["candidate_conflict_rejections"] == 2
        and summary["candidate_conflict_state_clean"] == 2
        and summary["baseline_conflict_outputs_correct"]
        and summary["baseline_distinct_conflict_outputs"] == 2
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
