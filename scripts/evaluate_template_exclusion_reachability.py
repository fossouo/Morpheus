#!/usr/bin/env python3
"""Contrast disjoint and reachable nested exclusions on two routing paths."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_package_root_ownership import (  # noqa: E402
    PackageRootOwnershipKernel,
)
from scripts.evaluate_public_template_v2_migration import (  # noqa: E402
    migrate_template,
)
from scripts.evaluate_public_template_v2_migration_replay import (  # noqa: E402
    repaired_packages,
)
from scripts.evaluate_stable_validator_integration import (  # noqa: E402
    StableValidatorManifestKernel,
)
from scripts.validate_expert_manifest import SCHEMA, validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures/expert_template_exclusion_reachability_cases.json"


def _read_pinned_template(source: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError("public template hash mismatch")
    return json.loads(payload), payload


def literal_prefix_match(pattern: str, scope: str) -> bool:
    """Independent literal-segment oracle, separate from the routing kernels."""
    prefix, request = pattern.split("/"), scope.split("/")
    if any(segment in {"", "*", ".", ".."} for segment in prefix + request):
        raise ValueError("oracle requires nonempty literal segments")
    return request[:len(prefix)] == prefix


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema", "reference_date", "root", "template", "cases", "allowed",
        "absent", "unloaded_expected",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-template-exclusion-reachability-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    reference_date = date.fromisoformat(fixture["reference_date"])
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be canonical")
    if not isinstance(fixture["root"], str) or "/" in fixture["root"]:
        raise ValueError("root must be one literal segment")
    source = fixture["template"]
    if set(source) != {"path", "sha256"} or source["path"] != "templates/expert-package.json":
        raise ValueError("template pin is unsupported")
    _read_pinned_template(source)
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 2:
        raise ValueError("fixture must contain exactly two cases")
    expected_topologies = ["disjoint", "nested"]
    for case, topology in zip(cases, expected_topologies):
        if set(case) != {
            "id", "topology", "include", "exclude", "request",
            "expected_include_matches", "expected_exclude_matches", "expected",
        } or case["topology"] != topology:
            raise ValueError("case topology or structure changed")
        if len(case["include"]) != 1 or len(case["exclude"]) != 1:
            raise ValueError("each case must contain one include and one exclude")
        if set(case["request"]) != {"operation", "scope", "local_id"}:
            raise ValueError("case request structure changed")
    for name in ("allowed", "absent"):
        if set(fixture[name]) != {"operation", "scope", "local_id", "expected"}:
            raise ValueError(f"{name} request structure changed")
    return fixture


def _candidate(template: dict[str, Any], root: str, case: dict[str, Any]) -> dict[str, Any]:
    candidate = migrate_template(template, root)
    candidate["scope"] = {
        name: [f"{root}/{pattern}" for pattern in case[name]]
        for name in ("include", "exclude")
    }
    return candidate


def _routing_v1(manifest: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)
    projected.pop("root")
    projected["schema"] = SCHEMA
    return projected


def _query(request: dict[str, Any]) -> dict[str, Any]:
    return {key: request[key] for key in ("operation", "scope", "local_id")}


def _case_trial(
    fixture: dict[str, Any], template: dict[str, Any], case: dict[str, Any]
) -> dict[str, Any]:
    root = fixture["root"]
    reference_date = date.fromisoformat(fixture["reference_date"])
    candidate = _candidate(template, root, case)
    packages = repaired_packages(candidate)
    package_ids = [package["manifest"]["package_id"] for package in packages]
    by_id = {package["manifest"]["package_id"]: package for package in packages}
    orders = [package_ids, list(reversed(package_ids))]
    request = case["request"]
    rooted_include = candidate["scope"]["include"]
    rooted_exclude = candidate["scope"]["exclude"]
    include_matches = sum(
        literal_prefix_match(pattern, request["scope"]) for pattern in rooted_include
    )
    exclude_matches = sum(
        literal_prefix_match(pattern, request["scope"]) for pattern in rooted_exclude
    )
    exclude_only_prediction = (
        "route-error:scope-excluded" if exclude_matches else "route-error:scope-not-found"
    )
    reachable_prediction = (
        "route-error:scope-excluded"
        if include_matches and exclude_matches
        else "route-error:scope-not-found"
    )

    runs: list[dict[str, Any]] = []
    for order in orders:
        ordered = [by_id[package_id] for package_id in order]
        baseline = PackageRootOwnershipKernel()
        baseline.compose_quarantined_experts([
            {
                "root": package["manifest"]["root"],
                "package": {
                    "manifest": _routing_v1(package["manifest"]),
                    "knowledge_records": copy.deepcopy(package["knowledge_records"]),
                },
            }
            for package in ordered
        ], reference_date=reference_date)
        stable = StableValidatorManifestKernel()
        stable.compose_quarantined_experts(ordered, reference_date=reference_date)
        run = {
            "baseline_case": baseline.answer(request),
            "stable_case": stable.answer(request),
            "baseline_allowed": baseline.answer(_query(fixture["allowed"])),
            "stable_allowed": stable.answer(_query(fixture["allowed"])),
            "baseline_absent": baseline.answer(_query(fixture["absent"])),
            "stable_absent": stable.answer(_query(fixture["absent"])),
        }
        baseline.unload_experts()
        stable.unload_experts()
        run["baseline_unloaded"] = baseline.answer(request)
        run["stable_unloaded"] = stable.answer(request)
        runs.append(run)

    return {
        "case_id": case["id"],
        "topology": case["topology"],
        "expected": case["expected"],
        "include_matches": include_matches,
        "exclude_matches": exclude_matches,
        "exclude_only_prediction": exclude_only_prediction,
        "reachable_prediction": reachable_prediction,
        "manifest_errors": validate_manifest(candidate, reference_date=reference_date),
        "orders": orders,
        "runs": runs,
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    template, _ = _read_pinned_template(fixture["template"])
    return {
        "template_errors": validate_manifest(
            template, reference_date=date.fromisoformat(fixture["reference_date"])
        ),
        "cases": [_case_trial(fixture, template, case) for case in fixture["cases"]],
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    pair_parity = pair_correct = allowed_correct = absent_correct = rollback_correct = 0
    order_invariant = True
    for case, result in zip(fixture["cases"], trial["cases"]):
        first = result["runs"][0]
        order_invariant &= all(run == first for run in result["runs"])
        for run in result["runs"]:
            pair_parity += run["baseline_case"] == run["stable_case"]
            pair_correct += run["baseline_case"] == case["expected"]
            pair_correct += run["stable_case"] == case["expected"]
            allowed_correct += run["baseline_allowed"] == fixture["allowed"]["expected"]
            allowed_correct += run["stable_allowed"] == fixture["allowed"]["expected"]
            absent_correct += run["baseline_absent"] == fixture["absent"]["expected"]
            absent_correct += run["stable_absent"] == fixture["absent"]["expected"]
            rollback_correct += run["baseline_unloaded"] == fixture["unloaded_expected"]
            rollback_correct += run["stable_unloaded"] == fixture["unloaded_expected"]
    return {
        "template_valid": trial["template_errors"] == [],
        "candidate_manifests_valid": sum(
            result["manifest_errors"] == [] for result in trial["cases"]
        ),
        "oracle_counts_correct": sum(
            result["include_matches"] == case["expected_include_matches"]
            and result["exclude_matches"] == case["expected_exclude_matches"]
            for case, result in zip(fixture["cases"], trial["cases"])
        ),
        "exclude_only_baseline_correct": sum(
            result["exclude_only_prediction"] == case["expected"]
            for case, result in zip(fixture["cases"], trial["cases"])
        ),
        "reachable_oracle_correct": sum(
            result["reachable_prediction"] == case["expected"]
            for case, result in zip(fixture["cases"], trial["cases"])
        ),
        "pair_path_parity": pair_parity,
        "pair_path_correct": pair_correct,
        "allowed_path_correct": allowed_correct,
        "absent_path_correct": absent_correct,
        "rollback_correct": rollback_correct,
        "order_invariant": order_invariant,
    }


def accepted(summary: dict[str, Any]) -> bool:
    return (
        summary["template_valid"]
        and summary["candidate_manifests_valid"] == 2
        and summary["oracle_counts_correct"] == 2
        and summary["exclude_only_baseline_correct"] == 1
        and summary["reachable_oracle_correct"] == 2
        and summary["pair_path_parity"] == 4
        and summary["pair_path_correct"] == 8
        and summary["allowed_path_correct"] == 8
        and summary["absent_path_correct"] == 8
        and summary["rollback_correct"] == 8
        and summary["order_invariant"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first = run_trial(fixture)
    repeated = run_trial(fixture)
    summary = summarize(fixture, first)
    _, template_bytes = _read_pinned_template(fixture["template"])
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": args.fixture.stat().st_size + len(template_bytes),
        "evaluation_seconds": perf_counter() - started,
        "external_calls": 0,
    })
    summary["accepted"] = accepted(summary)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
