#!/usr/bin/env python3
"""Evaluate package-owned root declarations for wildcard expert routing."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_exclusion_scope_routing import _matches_pattern  # noqa: E402
from scripts.evaluate_hierarchical_scope_routing import _scope_segments  # noqa: E402
from scripts.evaluate_specificity_floor_exclusion_routing import (  # noqa: E402
    SpecificityFloorExclusionRoutingKernel,
)
from scripts.evaluate_wildcard_scope_routing import (  # noqa: E402
    _pattern_segments,
    _validated_cases,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_package_root_ownership_cases.json"


def _entry_id(entry: Any) -> str:
    if not isinstance(entry, dict) or set(entry) != {"root", "package"}:
        raise ValueError("package entry must contain only root and package")
    package = entry["package"]
    if not isinstance(package, dict) or not isinstance(package.get("manifest"), dict):
        raise ValueError("package entry must contain a manifest")
    package_id = package["manifest"].get("package_id")
    if not isinstance(package_id, str):
        raise ValueError("package entry must contain a package id")
    return package_id


def _validated_root(entry: dict[str, Any]) -> tuple[str, str]:
    package_id = _entry_id(entry)
    root = entry["root"]
    try:
        segments = _scope_segments(root)
    except ValueError as exc:
        raise ValueError(f"invalid-package-root:{package_id}") from exc
    if len(segments) != 1 or segments[0] == "*":
        raise ValueError(f"invalid-package-root:{package_id}")
    for name in ("include", "exclude"):
        for pattern in entry["package"]["manifest"]["scope"][name]:
            pattern_segments = _pattern_segments(pattern)
            if pattern_segments[0] != "*" and pattern_segments[0] != root:
                raise ValueError(
                    f"scope-root-mismatch:{package_id}:{name}:{pattern}"
                )
    return package_id, root


class PackageRootOwnershipKernel(SpecificityFloorExclusionRoutingKernel):
    """Constrain every package's scope patterns to its declared literal root."""

    def __init__(self) -> None:
        super().__init__()
        self._root_by_package: dict[str, str] = {}

    def compose_quarantined_experts(
        self, entries: Any, *, reference_date: date
    ) -> None:
        if (
            self._knowledge_by_package
            or self._package_by_scope
            or self._exclusions_by_package
            or self._root_by_package
        ):
            raise ValueError("experts are already loaded")
        if not isinstance(entries, list) or len(entries) < 2:
            raise ValueError("composition requires at least two package entries")

        proposed_roots: dict[str, str] = {}
        packages: list[Any] = []
        for entry in entries:
            package_id, root = _validated_root(entry)
            if package_id in proposed_roots:
                raise ValueError(f"duplicate-package-id:{package_id}")
            proposed_roots[package_id] = root
            packages.append(entry["package"])

        super().compose_quarantined_experts(packages, reference_date=reference_date)
        self._root_by_package = proposed_roots

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
                if request_segments[0] != self._root_by_package[package_id]:
                    continue
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

    def unload_experts(self) -> None:
        super().unload_experts()
        self._root_by_package = {}


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "packages", "compatible_package_ids",
        "held_out_target", "held_out_regression", "cross_root_probe",
        "absent_scope_probe", "invalid_declarations", "clean_state_probe",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-package-root-ownership-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    entries = fixture["packages"]
    if not isinstance(entries, list) or len(entries) != 2:
        raise ValueError("fixture must contain exactly two package entries")
    package_ids: list[str] = []
    roots: list[str] = []
    for entry in entries:
        package_id, root = _validated_root(entry)
        if package_id in package_ids:
            raise ValueError("package ids must be unique")
        package_ids.append(package_id)
        roots.append(root)
    if len(set(roots)) != 2:
        raise ValueError("fixture must contain exactly two distinct roots")
    if fixture["compatible_package_ids"] != package_ids:
        raise ValueError("compatible_package_ids must preserve package fixture order")

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 8:
        raise ValueError("fixture must contain exactly eight target cases")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise ValueError("fixture must contain exactly three regression cases")
    target_ids = _validated_cases(
        targets,
        {
            "id", "policy", "request", "expected_baseline",
            "expected_candidate", "expected_unloaded",
        },
    )
    policies = [case["policy"] for case in targets]
    if sum(policy.startswith("own-root-") for policy in policies) != 4:
        raise ValueError("fixture must lock exactly four own-root targets")
    if sum(policy.startswith("cross-root-") for policy in policies) != 4:
        raise ValueError("fixture must lock exactly four cross-root targets")
    regression_ids = _validated_cases(regressions, {"id", "request", "expected"})
    declared_targets: list[str] = []
    for entry in entries:
        manifest = entry["package"]["manifest"]
        declared_targets.extend(manifest["tests"]["target"])
        if manifest["tests"]["held_out_regression"] != regression_ids:
            raise ValueError("regression ids must match package manifests")
    if declared_targets != target_ids:
        raise ValueError("target ids must match package manifests in fixture order")

    cross_root_probe = fixture["cross_root_probe"]
    if not isinstance(cross_root_probe, dict) or set(cross_root_probe) != {
        "request", "expected_baseline", "expected_candidate"
    }:
        raise ValueError("cross_root_probe has unexpected structure")
    absent_probe = fixture["absent_scope_probe"]
    if not isinstance(absent_probe, dict) or set(absent_probe) != {"request", "expected"}:
        raise ValueError("absent_scope_probe has unexpected structure")

    invalid = fixture["invalid_declarations"]
    invalid_keys = {"id", "package_id", "field", "index", "value", "expected_error"}
    if not isinstance(invalid, list) or len(invalid) != 4:
        raise ValueError("fixture must contain exactly four invalid declarations")
    seen: set[str] = set()
    for case in invalid:
        if not isinstance(case, dict) or set(case) != invalid_keys:
            raise ValueError("invalid declaration case has unexpected structure")
        if case["id"] in seen or case["package_id"] not in package_ids:
            raise ValueError("invalid declaration ids and packages must be locked")
        seen.add(case["id"])
        if case["field"] not in {"root", "include", "exclude"}:
            raise ValueError("invalid declaration field is unsupported")
        if not isinstance(case["value"], str) or not isinstance(case["expected_error"], str):
            raise ValueError("invalid declaration values must be strings")
        if case["field"] == "root" and case["index"] is not None:
            raise ValueError("root mutation index must be null")
        if case["field"] != "root" and not isinstance(case["index"], int):
            raise ValueError("scope mutation index must be an integer")
    if not isinstance(fixture["clean_state_probe"], dict):
        raise ValueError("clean_state_probe must be an object")


def _entries_by_id(fixture: dict[str, Any]) -> dict[str, Any]:
    return {_entry_id(entry): entry for entry in fixture["packages"]}


def _mutated_entries(
    fixture: dict[str, Any], mutation: dict[str, Any]
) -> list[dict[str, Any]]:
    entries = copy.deepcopy(fixture["packages"])
    entry = next(
        item for item in entries if _entry_id(item) == mutation["package_id"]
    )
    if mutation["field"] == "root":
        entry["root"] = mutation["value"]
    else:
        entry["package"]["manifest"]["scope"][mutation["field"]][
            mutation["index"]
        ] = mutation["value"]
    return entries


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    by_id = _entries_by_id(fixture)
    orders = [
        fixture["compatible_package_ids"],
        list(reversed(fixture["compatible_package_ids"])),
    ]
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    order_runs: list[dict[str, Any]] = []
    for order in orders:
        entries = [by_id[package_id] for package_id in order]
        baseline = SpecificityFloorExclusionRoutingKernel()
        baseline.compose_quarantined_experts(
            [entry["package"] for entry in entries], reference_date=reference_date
        )
        baseline_target = [baseline.answer(case["request"]) for case in targets]
        baseline_cross_root = baseline.answer(fixture["cross_root_probe"]["request"])

        candidate = PackageRootOwnershipKernel()
        unloaded_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate.compose_quarantined_experts(entries, reference_date=reference_date)
        candidate_target = [candidate.answer(case["request"]) for case in targets]
        candidate_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate_cross_root = candidate.answer(fixture["cross_root_probe"]["request"])
        absent = candidate.answer(fixture["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        order_runs.append({
            "baseline_target": baseline_target,
            "baseline_cross_root": baseline_cross_root,
            "unloaded_regression": unloaded_regression,
            "candidate_target": candidate_target,
            "candidate_regression": candidate_regression,
            "candidate_cross_root": candidate_cross_root,
            "absent": absent,
            "post_unload_target": post_unload_target,
        })

    invalid_runs: list[dict[str, Any]] = []
    for mutation in fixture["invalid_declarations"]:
        mutated = _mutated_entries(fixture, mutation)
        for entries in (mutated, list(reversed(mutated))):
            baseline = SpecificityFloorExclusionRoutingKernel()
            baseline_accepted = True
            try:
                baseline.compose_quarantined_experts(
                    [entry["package"] for entry in entries],
                    reference_date=reference_date,
                )
            except ValueError:
                baseline_accepted = False

            candidate = PackageRootOwnershipKernel()
            error = ""
            try:
                candidate.compose_quarantined_experts(
                    entries, reference_date=reference_date
                )
            except ValueError as exc:
                error = str(exc)
            invalid_runs.append({
                "case_id": mutation["id"],
                "baseline_accepted": baseline_accepted,
                "candidate_error": error,
                "expected_error": mutation["expected_error"],
                "clean_state": candidate.answer(fixture["clean_state_probe"]),
            })
    return {"orders": orders, "order_runs": order_runs, "invalid_runs": invalid_runs}


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    targets = fixture["held_out_target"]
    expected_baseline = [case["expected_baseline"] for case in targets]
    expected_candidate = [case["expected_candidate"] for case in targets]
    expected_unloaded = [case["expected_unloaded"] for case in targets]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    first = trial["order_runs"][0]
    baseline_correct = sum(
        actual == expected
        for actual, expected in zip(first["baseline_target"], expected_candidate)
    )
    candidate_correct = sum(
        actual == expected
        for actual, expected in zip(first["candidate_target"], expected_candidate)
    )
    return {
        "target_count": len(targets),
        "order_count": len(trial["orders"]),
        "baseline_policy_outputs_correct": all(
            run["baseline_target"] == expected_baseline for run in trial["order_runs"]
        ),
        "baseline_target_correct": baseline_correct,
        "baseline_cross_root_false_accepts": sum(
            first["baseline_target"][index] != expected_candidate[index]
            for index, case in enumerate(targets)
            if case["policy"].startswith("cross-root-")
        ),
        "candidate_target_correct": candidate_correct,
        "target_accuracy_gain": round(
            (candidate_correct - baseline_correct) / len(targets), 6
        ),
        "candidate_own_root_routes": sum(
            first["candidate_target"][index] == expected_candidate[index]
            for index, case in enumerate(targets)
            if case["policy"].startswith("own-root-")
        ),
        "candidate_cross_root_rejections": sum(
            first["candidate_target"][index] == expected_candidate[index]
            for index, case in enumerate(targets)
            if case["policy"].startswith("cross-root-")
        ),
        "unloaded_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["unloaded_regression"], expected_regression)
        ),
        "candidate_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["candidate_regression"], expected_regression)
        ),
        "candidate_order_invariant": all(
            run["candidate_target"] == first["candidate_target"]
            and run["candidate_regression"] == first["candidate_regression"]
            for run in trial["order_runs"]
        ),
        "baseline_probe_false_accepts": sum(
            run["baseline_cross_root"] == fixture["cross_root_probe"]["expected_baseline"]
            for run in trial["order_runs"]
        ),
        "candidate_probe_rejections": sum(
            run["candidate_cross_root"] == fixture["cross_root_probe"]["expected_candidate"]
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
        "invalid_order_count": len(trial["invalid_runs"]),
        "baseline_invalid_declarations_accepted": sum(
            run["baseline_accepted"] for run in trial["invalid_runs"]
        ),
        "candidate_invalid_declarations_rejected": sum(
            run["candidate_error"] == run["expected_error"]
            for run in trial["invalid_runs"]
        ),
        "candidate_invalid_states_clean": sum(
            run["clean_state"] == "route-error:scope-not-found"
            for run in trial["invalid_runs"]
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
        and summary["baseline_cross_root_false_accepts"] == 4
        and summary["candidate_target_correct"] == summary["target_count"] == 8
        and summary["target_accuracy_gain"] == 0.5
        and summary["candidate_own_root_routes"] == 4
        and summary["candidate_cross_root_rejections"] == 4
        and summary["unloaded_regression_correct"]
        == summary["candidate_regression_correct"]
        == 3
        and summary["order_count"] == 2
        and summary["candidate_order_invariant"]
        and summary["baseline_probe_false_accepts"] == 2
        and summary["candidate_probe_rejections"] == 2
        and summary["absent_scope_rejections"] == 2
        and summary["rollback_matches_baseline"] == 16
        and summary["invalid_order_count"] == 8
        and summary["baseline_invalid_declarations_accepted"] == 8
        and summary["candidate_invalid_declarations_rejected"] == 8
        and summary["candidate_invalid_states_clean"] == 8
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
