#!/usr/bin/env python3
"""Evaluate a declared root fence for wildcard expert-scope routing."""

from __future__ import annotations

import argparse
import hashlib
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
from scripts.evaluate_hierarchical_scope_routing import _scope_segments  # noqa: E402
from scripts.evaluate_multi_candidate_exclusion_cardinality import (  # noqa: E402
    _cardinality,
    summarize as summarize_routing,
    validate_fixture as validate_routing_fixture,
)
from scripts.evaluate_specificity_floor_exclusion_routing import (  # noqa: E402
    SpecificityFloorExclusionRoutingKernel,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_declared_root_boundary_cases.json"


class DeclaredRootBoundaryKernel(SpecificityFloorExclusionRoutingKernel):
    """Reject requests outside an explicit root set before scope matching."""

    def __init__(self, allowed_roots: list[str]) -> None:
        super().__init__()
        if not isinstance(allowed_roots, list) or not allowed_roots:
            raise ValueError("allowed_roots must be a non-empty list")
        validated: set[str] = set()
        for root in allowed_roots:
            segments = _scope_segments(root)
            if len(segments) != 1 or segments[0] == "*":
                raise ValueError("allowed roots must be literal single segments")
            if root in validated:
                raise ValueError("allowed roots must be unique")
            validated.add(root)
        self._allowed_roots = frozenset(validated)

    def answer(self, request: Any) -> str:
        if (
            isinstance(request, dict)
            and request.get("operation") == "scope_recall"
            and set(request) == {"operation", "scope", "local_id"}
        ):
            request_segments = _scope_segments(request["scope"])
            if request_segments[0] not in self._allowed_roots:
                return "route-error:scope-not-found"
        return super().answer(request)


def _source_path(fixture: dict[str, Any]) -> Path:
    name = fixture["source_fixture"]
    if name != "expert_multi_candidate_exclusion_cases.json":
        raise ValueError("source_fixture must name the locked EXP-022 fixture")
    return ROOT / "fixtures" / name


def load_fixture(path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    source_path = _source_path(fixture)
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    validate_fixture(fixture, source, source_bytes)
    return fixture, source, source_path


def validate_fixture(
    fixture: Any, source: Any, source_bytes: bytes | None = None
) -> None:
    required = {
        "schema", "source_fixture", "source_sha256", "reference_date",
        "allowed_roots", "cross_root_cases",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-declared-root-boundary-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    validate_routing_fixture(source)
    encoded_source = source_bytes or json.dumps(source, indent=2).encode("utf-8")
    if hashlib.sha256(encoded_source).hexdigest() != fixture["source_sha256"]:
        raise ValueError("source fixture does not match its locked SHA-256")

    DeclaredRootBoundaryKernel(fixture["allowed_roots"])
    cases = fixture["cross_root_cases"]
    case_keys = {"id", "request", "expected_baseline", "expected_candidate"}
    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("fixture must contain exactly four cross-root cases")
    ids: set[str] = set()
    allowed = set(fixture["allowed_roots"])
    for case in cases:
        if not isinstance(case, dict) or set(case) != case_keys:
            raise ValueError("cross-root case has unexpected structure")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in ids:
            raise ValueError("cross-root case ids must be non-empty and unique")
        ids.add(case["id"])
        request = case["request"]
        if not isinstance(request, dict) or set(request) != {
            "operation", "scope", "local_id"
        }:
            raise ValueError("cross-root requests have unexpected structure")
        if request["operation"] != "scope_recall":
            raise ValueError("cross-root requests must use scope_recall")
        segments = _scope_segments(request["scope"])
        if segments[0] in allowed:
            raise ValueError("cross-root cases must use a disallowed root")
        for key in ("local_id", "expected_baseline", "expected_candidate"):
            if not isinstance(case[key] if key in case else request[key], str):
                raise ValueError("cross-root labels and responses must be strings")
        if case["expected_candidate"] != "route-error:scope-not-found":
            raise ValueError("cross-root candidate responses must fail closed")


def _routing_trial(
    fixture: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = {
        package["manifest"]["package_id"]: package for package in source["packages"]
    }
    targets = source["held_out_target"]
    regressions = source["held_out_regression"]
    cross_root = fixture["cross_root_cases"]
    orders = [
        list(order) for order in permutations(source["compatible_package_ids"])
    ]
    order_runs: list[dict[str, Any]] = []
    for order in orders:
        packages = [by_id[package_id] for package_id in order]

        baseline = PreExclusionAmbiguityKernel()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        baseline_target = [baseline.answer(case["request"]) for case in targets]

        unrestricted = SpecificityFloorExclusionRoutingKernel()
        unrestricted.compose_quarantined_experts(packages, reference_date=reference_date)
        unrestricted_cross_root = [
            unrestricted.answer(case["request"]) for case in cross_root
        ]

        candidate = DeclaredRootBoundaryKernel(fixture["allowed_roots"])
        unloaded_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(packages, reference_date=reference_date)
        cardinalities = [_cardinality(candidate, case["request"]) for case in targets]
        candidate_target = [candidate.answer(case["request"]) for case in targets]
        candidate_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate_cross_root = [
            candidate.answer(case["request"]) for case in cross_root
        ]
        boundary = candidate.answer(source["boundary_probe"]["request"])
        absent = candidate.answer(source["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        order_runs.append({
            "baseline_target": baseline_target,
            "unloaded_regression": unloaded_regression,
            "cardinalities": cardinalities,
            "candidate_target": candidate_target,
            "candidate_regression": candidate_regression,
            "unrestricted_cross_root": unrestricted_cross_root,
            "candidate_cross_root": candidate_cross_root,
            "boundary": boundary,
            "absent": absent,
            "post_unload_target": post_unload_target,
        })
    return {"orders": orders, "order_runs": order_runs}


def run_trial(fixture: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    return _routing_trial(fixture, source)


def summarize(
    fixture: dict[str, Any], source: dict[str, Any], trial: dict[str, Any]
) -> dict[str, Any]:
    summary = summarize_routing(source, trial)
    expected_baseline = [
        case["expected_baseline"] for case in fixture["cross_root_cases"]
    ]
    expected_candidate = [
        case["expected_candidate"] for case in fixture["cross_root_cases"]
    ]
    first = trial["order_runs"][0]
    summary.update({
        "cross_root_case_count": len(expected_candidate),
        "unrestricted_cross_root_correct": sum(
            actual == expected
            for actual, expected in zip(first["unrestricted_cross_root"], expected_baseline)
        ),
        "unrestricted_cross_root_false_accepts": sum(
            actual != expected
            for actual, expected in zip(first["unrestricted_cross_root"], expected_candidate)
        ),
        "candidate_cross_root_correct": sum(
            actual == expected
            for actual, expected in zip(first["candidate_cross_root"], expected_candidate)
        ),
        "candidate_cross_root_rejections": sum(
            run["candidate_cross_root"] == expected_candidate
            for run in trial["order_runs"]
        ),
        "unrestricted_cross_root_order_invariant": all(
            run["unrestricted_cross_root"] == first["unrestricted_cross_root"]
            for run in trial["order_runs"]
        ),
    })
    summary["cross_root_accuracy_gain"] = round(
        (
            summary["candidate_cross_root_correct"]
            - sum(
                actual == expected
                for actual, expected in zip(
                    first["unrestricted_cross_root"], expected_candidate
                )
            )
        )
        / summary["cross_root_case_count"],
        6,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture, source, source_path = load_fixture(args.fixture)
    first = run_trial(fixture, source)
    repeated = run_trial(fixture, source)
    elapsed_seconds = perf_counter() - started
    summary = summarize(fixture, source, first)
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": args.fixture.stat().st_size + source_path.stat().st_size,
        "evaluation_seconds": round(elapsed_seconds, 6),
        "external_calls": 0,
    })
    summary["accepted"] = (
        summary["cross_root_case_count"] == 4
        and summary["unrestricted_cross_root_correct"] == 4
        and summary["unrestricted_cross_root_false_accepts"] == 4
        and summary["candidate_cross_root_correct"] == 4
        and summary["candidate_cross_root_rejections"] == summary["order_count"] == 24
        and summary["cross_root_accuracy_gain"] == 1.0
        and summary["unrestricted_cross_root_order_invariant"]
        and summary["baseline_policy_outputs_correct"]
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
