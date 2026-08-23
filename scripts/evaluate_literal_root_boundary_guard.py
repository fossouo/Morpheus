#!/usr/bin/env python3
"""Evaluate a literal first-segment guard for expert scope patterns."""

from __future__ import annotations

import argparse
import copy
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
from scripts.evaluate_multi_candidate_exclusion_cardinality import (  # noqa: E402
    _cardinality,
    summarize as summarize_routing,
    validate_fixture as validate_routing_fixture,
)
from scripts.evaluate_specificity_floor_exclusion_routing import (  # noqa: E402
    SpecificityFloorExclusionRoutingKernel,
)
from scripts.evaluate_wildcard_scope_routing import _pattern_segments  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_literal_root_boundary_cases.json"


def _literal_root_segments(pattern: str) -> tuple[str, ...]:
    segments = _pattern_segments(pattern)
    if segments[0] == "*":
        raise ValueError("scope patterns require a literal first segment")
    return segments


class LiteralRootBoundaryKernel(SpecificityFloorExclusionRoutingKernel):
    """Reject a leading wildcard before any expert composition state is installed."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if not isinstance(packages, list):
            raise ValueError("packages must be a list")
        for package in packages:
            scope = package["manifest"]["scope"]
            for name in ("include", "exclude"):
                for pattern in scope[name]:
                    _literal_root_segments(pattern)
        super().compose_quarantined_experts(packages, reference_date=reference_date)


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
        "literal_root_replacements", "grammar_cases", "unsafe_boundary_expected",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-literal-root-boundary-cases-v1":
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

    replacements = fixture["literal_root_replacements"]
    replacement_keys = {"package_id", "scope_list", "index", "before", "after"}
    if not isinstance(replacements, list) or len(replacements) != 8:
        raise ValueError("fixture must contain exactly eight literal-root replacements")
    coordinates: set[tuple[str, str, int]] = set()
    for replacement in replacements:
        if not isinstance(replacement, dict) or set(replacement) != replacement_keys:
            raise ValueError("replacement has unexpected structure")
        coordinate = (
            replacement["package_id"], replacement["scope_list"], replacement["index"]
        )
        if coordinate in coordinates:
            raise ValueError("replacement coordinates must be unique")
        coordinates.add(coordinate)
        if replacement["scope_list"] not in {"include", "exclude"}:
            raise ValueError("replacement scope_list must be include or exclude")
        before = _pattern_segments(replacement["before"])
        after = _literal_root_segments(replacement["after"])
        if before[0] != "*" or after[1:] != before[1:]:
            raise ValueError("replacement must change only the leading wildcard")

    cases = fixture["grammar_cases"]
    case_keys = {"id", "kind", "pattern", "expected_valid"}
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("fixture must contain exactly six grammar cases")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != case_keys:
            raise ValueError("grammar case has unexpected structure")
        if case["id"] in ids or not isinstance(case["id"], str) or not case["id"]:
            raise ValueError("grammar case ids must be non-empty and unique")
        ids.add(case["id"])
        if case["kind"] not in {"include", "exclude"}:
            raise ValueError("grammar case kind must be include or exclude")
        if not isinstance(case["expected_valid"], bool):
            raise ValueError("expected_valid must be boolean")
        _pattern_segments(case["pattern"])
    if sum(not case["expected_valid"] for case in cases) != 2:
        raise ValueError("grammar cases must contain exactly two invalid patterns")
    if not isinstance(fixture["unsafe_boundary_expected"], str):
        raise ValueError("unsafe boundary response must be a string")


def repaired_routing_fixture(
    fixture: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    repaired = copy.deepcopy(source)
    by_id = {
        package["manifest"]["package_id"]: package for package in repaired["packages"]
    }
    for replacement in fixture["literal_root_replacements"]:
        patterns = by_id[replacement["package_id"]]["manifest"]["scope"][
            replacement["scope_list"]
        ]
        index = replacement["index"]
        if patterns[index] != replacement["before"]:
            raise ValueError("replacement before value does not match source fixture")
        patterns[index] = replacement["after"]
    repaired["reference_date"] = fixture["reference_date"]
    for package in repaired["packages"]:
        for name in ("include", "exclude"):
            for pattern in package["manifest"]["scope"][name]:
                _literal_root_segments(pattern)
    return repaired


def _grammar_trial(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for case in fixture["grammar_cases"]:
        baseline_valid = True
        candidate_valid = True
        try:
            _pattern_segments(case["pattern"])
        except ValueError:
            baseline_valid = False
        try:
            _literal_root_segments(case["pattern"])
        except ValueError:
            candidate_valid = False
        decisions.append({
            "id": case["id"],
            "expected_valid": case["expected_valid"],
            "baseline_valid": baseline_valid,
            "candidate_valid": candidate_valid,
        })
    return decisions


def _unsafe_composition_trial(
    fixture: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    boundary_request = source["boundary_probe"]["request"]
    orders = list(permutations(source["compatible_package_ids"]))
    by_id = {
        package["manifest"]["package_id"]: package for package in source["packages"]
    }

    baseline = SpecificityFloorExclusionRoutingKernel()
    baseline.compose_quarantined_experts(
        [by_id[package_id] for package_id in orders[0]], reference_date=reference_date
    )
    baseline_boundary = baseline.answer(boundary_request)

    guarded_runs: list[dict[str, Any]] = []
    for order in orders:
        candidate = LiteralRootBoundaryKernel()
        rejected = False
        try:
            candidate.compose_quarantined_experts(
                [by_id[package_id] for package_id in order], reference_date=reference_date
            )
        except ValueError as exc:
            rejected = str(exc) == "scope patterns require a literal first segment"
        guarded_runs.append({
            "rejected": rejected,
            "state_clean": (
                candidate._knowledge_by_package == {}
                and candidate._package_by_scope == {}
                and candidate._exclusions_by_package == {}
            ),
            "boundary": candidate.answer(boundary_request),
        })
    return {
        "baseline_boundary": baseline_boundary,
        "guarded_runs": guarded_runs,
    }


def _routing_trial(routing: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(routing["reference_date"])
    by_id = {
        package["manifest"]["package_id"]: package for package in routing["packages"]
    }
    targets = routing["held_out_target"]
    regressions = routing["held_out_regression"]
    orders = [list(order) for order in permutations(routing["compatible_package_ids"])]
    order_runs: list[dict[str, Any]] = []
    for order in orders:
        packages = [by_id[package_id] for package_id in order]
        baseline = PreExclusionAmbiguityKernel()
        baseline.compose_quarantined_experts(packages, reference_date=reference_date)
        baseline_target = [baseline.answer(case["request"]) for case in targets]

        candidate = LiteralRootBoundaryKernel()
        unloaded_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(packages, reference_date=reference_date)
        cardinalities = [_cardinality(candidate, case["request"]) for case in targets]
        candidate_target = [candidate.answer(case["request"]) for case in targets]
        candidate_regression = [candidate.answer(case["request"]) for case in regressions]
        boundary = candidate.answer(routing["boundary_probe"]["request"])
        absent = candidate.answer(routing["absent_scope_probe"]["request"])
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


def run_trial(
    fixture: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    routing = repaired_routing_fixture(fixture, source)
    return {
        "grammar": _grammar_trial(fixture),
        "unsafe": _unsafe_composition_trial(fixture, source),
        "routing": _routing_trial(routing),
    }


def summarize(
    fixture: dict[str, Any], source: dict[str, Any], trial: dict[str, Any]
) -> dict[str, Any]:
    routing = repaired_routing_fixture(fixture, source)
    summary = summarize_routing(routing, trial["routing"])
    grammar = trial["grammar"]
    unsafe = trial["unsafe"]
    summary.update({
        "grammar_case_count": len(grammar),
        "baseline_grammar_correct": sum(
            case["baseline_valid"] == case["expected_valid"] for case in grammar
        ),
        "baseline_grammar_false_accepts": sum(
            case["baseline_valid"] and not case["expected_valid"] for case in grammar
        ),
        "candidate_grammar_correct": sum(
            case["candidate_valid"] == case["expected_valid"] for case in grammar
        ),
        "candidate_grammar_false_accepts": sum(
            case["candidate_valid"] and not case["expected_valid"] for case in grammar
        ),
        "unsafe_baseline_boundary": unsafe["baseline_boundary"],
        "unsafe_guard_rejections": sum(run["rejected"] for run in unsafe["guarded_runs"]),
        "unsafe_guard_clean_states": sum(
            run["state_clean"] for run in unsafe["guarded_runs"]
        ),
        "unsafe_guard_boundary_rejections": sum(
            run["boundary"] == source["boundary_probe"]["expected"]
            for run in unsafe["guarded_runs"]
        ),
    })
    summary["grammar_accuracy_gain"] = round(
        (summary["candidate_grammar_correct"] - summary["baseline_grammar_correct"])
        / summary["grammar_case_count"],
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
        summary["grammar_case_count"] == 6
        and summary["baseline_grammar_correct"] == 4
        and summary["baseline_grammar_false_accepts"] == 2
        and summary["candidate_grammar_correct"] == 6
        and summary["candidate_grammar_false_accepts"] == 0
        and summary["grammar_accuracy_gain"] == 0.333333
        and summary["unsafe_baseline_boundary"] == fixture["unsafe_boundary_expected"]
        and summary["unsafe_guard_rejections"] == 24
        and summary["unsafe_guard_clean_states"] == 24
        and summary["unsafe_guard_boundary_rejections"] == 24
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
        and summary["order_count"] == 24
        and summary["baseline_order_invariant"]
        and summary["candidate_order_invariant"]
        and summary["boundary_rejections"] == 24
        and summary["absent_scope_rejections"] == 24
        and summary["rollback_matches_baseline"] == 192
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
