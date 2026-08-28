#!/usr/bin/env python3
"""Evaluate manifest-integrated package-root routing without stable promotion."""

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

from scripts.evaluate_expert_manifest_root import (  # noqa: E402
    _v1_projection,
    candidate_errors,
    load_fixture as load_manifest_fixture,
    run_trial as run_manifest_trial,
    summarize as summarize_manifest_trial,
)
from scripts.evaluate_package_root_ownership import (  # noqa: E402
    PackageRootOwnershipKernel,
    load_fixture as load_routing_fixture,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_manifest_integrated_root_routing_cases.json"


def _read_pinned_json(source: dict[str, Any]) -> tuple[Path, Any]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"source fixture hash mismatch:{source['path']}")
    return path, json.loads(payload)


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "routing_fixture", "manifest_fixture",
        "invalid_manifests",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-manifest-integrated-root-routing-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    for name in ("routing_fixture", "manifest_fixture"):
        source = fixture[name]
        if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
            raise ValueError(f"{name} has unexpected structure")
        if (
            not isinstance(source["path"], str)
            or not source["path"].startswith("fixtures/")
            or not isinstance(source["sha256"], str)
            or len(source["sha256"]) != 64
        ):
            raise ValueError(f"{name} must contain a fixture path and SHA-256")

    invalid = fixture["invalid_manifests"]
    if not isinstance(invalid, list) or len(invalid) != 4:
        raise ValueError("fixture must contain exactly four invalid manifests")
    seen_ids: set[str] = set()
    expected_ids = {"synthetic-root-alpha", "synthetic-root-beta"}
    for case in invalid:
        if not isinstance(case, dict) or set(case) != {
            "id", "package_id", "mutation", "expected_error",
        }:
            raise ValueError("invalid manifest case has unexpected structure")
        if case["id"] in seen_ids or case["package_id"] not in expected_ids:
            raise ValueError("invalid manifest ids and package ids must be locked")
        seen_ids.add(case["id"])
        if not isinstance(case["expected_error"], str) or not case["expected_error"]:
            raise ValueError("invalid manifest cases require an expected error")
        mutation = case["mutation"]
        if not isinstance(mutation, dict) or mutation.get("op") not in {"set", "remove"}:
            raise ValueError("invalid manifest mutation")
        expected_keys = (
            {"op", "path", "value"} if mutation["op"] == "set" else {"op", "path"}
        )
        if set(mutation) != expected_keys:
            raise ValueError("invalid manifest mutation shape")
        path = mutation["path"]
        if (
            not isinstance(path, list)
            or not path
            or not all(isinstance(part, (str, int)) for part in path)
        ):
            raise ValueError("mutation path must be a non-empty string/integer list")

    routing_path, _ = _read_pinned_json(fixture["routing_fixture"])
    routing = load_routing_fixture(routing_path)
    if routing["reference_date"] != "2026-08-25":
        raise ValueError("routing source reference date changed")
    if len(routing["held_out_target"]) != 8 or len(routing["held_out_regression"]) != 3:
        raise ValueError("routing source no longer matches the locked protocol")
    manifest_path, _ = _read_pinned_json(fixture["manifest_fixture"])
    load_manifest_fixture(manifest_path)


def _integrated_packages(routing: dict[str, Any]) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for entry in routing["packages"]:
        package = copy.deepcopy(entry["package"])
        package["manifest"]["schema"] = "expert-package-v2"
        package["manifest"]["root"] = entry["root"]
        packages.append(package)
    return packages


def _apply_mutation(package: dict[str, Any], mutation: dict[str, Any]) -> None:
    target: Any = package["manifest"]
    for part in mutation["path"][:-1]:
        target = target[part]
    leaf = mutation["path"][-1]
    if mutation["op"] == "remove":
        del target[leaf]
    else:
        target[leaf] = copy.deepcopy(mutation["value"])


class ManifestIntegratedRootKernel(PackageRootOwnershipKernel):
    """Read package roots from opt-in v2 manifests, then reuse EXP-025 routing."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")

        entries: list[dict[str, Any]] = []
        for package in packages:
            if not isinstance(package, dict) or set(package) != {
                "manifest", "knowledge_records",
            }:
                raise ValueError("package must contain only manifest and knowledge_records")
            manifest = package["manifest"]
            errors = candidate_errors(manifest)
            if errors:
                raise ValueError(f"invalid expert manifest: {errors}")
            projected = _v1_projection(manifest)
            dated_errors = validate_manifest(projected, reference_date=reference_date)
            if dated_errors:
                raise ValueError(f"invalid expert manifest: {dated_errors}")
            entries.append(
                {
                    "root": manifest["root"],
                    "package": {
                        "manifest": projected,
                        "knowledge_records": copy.deepcopy(package["knowledge_records"]),
                    },
                }
            )

        super().compose_quarantined_experts(entries, reference_date=reference_date)


def run_trial(
    fixture: dict[str, Any],
    *,
    candidate_kernel_class: type[ManifestIntegratedRootKernel] = ManifestIntegratedRootKernel,
) -> dict[str, Any]:
    routing_path, _ = _read_pinned_json(fixture["routing_fixture"])
    routing = load_routing_fixture(routing_path)
    reference_date = date.fromisoformat(fixture["reference_date"])
    integrated = _integrated_packages(routing)
    by_id = {package["manifest"]["package_id"]: package for package in integrated}
    entry_by_id = {
        entry["package"]["manifest"]["package_id"]: entry
        for entry in routing["packages"]
    }
    orders = [
        routing["compatible_package_ids"],
        list(reversed(routing["compatible_package_ids"])),
    ]
    targets = routing["held_out_target"]
    regressions = routing["held_out_regression"]

    order_runs: list[dict[str, Any]] = []
    for order in orders:
        baseline = PackageRootOwnershipKernel()
        baseline.compose_quarantined_experts(
            [entry_by_id[package_id] for package_id in order],
            reference_date=date.fromisoformat(routing["reference_date"]),
        )
        baseline_target = [baseline.answer(case["request"]) for case in targets]
        baseline_regression = [baseline.answer(case["request"]) for case in regressions]
        baseline_probe = baseline.answer(routing["cross_root_probe"]["request"])
        baseline_absent = baseline.answer(routing["absent_scope_probe"]["request"])

        candidate = candidate_kernel_class()
        candidate.compose_quarantined_experts(
            [by_id[package_id] for package_id in order], reference_date=reference_date
        )
        candidate_target = [candidate.answer(case["request"]) for case in targets]
        candidate_regression = [candidate.answer(case["request"]) for case in regressions]
        candidate_probe = candidate.answer(routing["cross_root_probe"]["request"])
        candidate_absent = candidate.answer(routing["absent_scope_probe"]["request"])
        candidate.unload_experts()
        post_unload_target = [candidate.answer(case["request"]) for case in targets]
        order_runs.append(
            {
                "baseline_target": baseline_target,
                "baseline_regression": baseline_regression,
                "baseline_probe": baseline_probe,
                "baseline_absent": baseline_absent,
                "candidate_target": candidate_target,
                "candidate_regression": candidate_regression,
                "candidate_probe": candidate_probe,
                "candidate_absent": candidate_absent,
                "post_unload_target": post_unload_target,
            }
        )

    invalid_runs: list[dict[str, Any]] = []
    for case in fixture["invalid_manifests"]:
        mutated = copy.deepcopy(integrated)
        package = next(
            item
            for item in mutated
            if item["manifest"]["package_id"] == case["package_id"]
        )
        _apply_mutation(package, case["mutation"])
        for packages in (mutated, list(reversed(mutated))):
            candidate = candidate_kernel_class()
            error = ""
            try:
                candidate.compose_quarantined_experts(
                    packages, reference_date=reference_date
                )
            except ValueError as exc:
                error = str(exc)
            invalid_runs.append(
                {
                    "case_id": case["id"],
                    "error": error,
                    "expected_error": case["expected_error"],
                    "clean_state": candidate.answer(routing["clean_state_probe"]),
                }
            )

    manifest_path, _ = _read_pinned_json(fixture["manifest_fixture"])
    historical = summarize_manifest_trial(
        run_manifest_trial(load_manifest_fixture(manifest_path))
    )
    return {
        "orders": orders,
        "order_runs": order_runs,
        "invalid_runs": invalid_runs,
        "historical": historical,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    routing_path, _ = _read_pinned_json(fixture["routing_fixture"])
    routing = load_routing_fixture(routing_path)
    expected_targets = [case["expected_candidate"] for case in routing["held_out_target"]]
    expected_regressions = [case["expected"] for case in routing["held_out_regression"]]
    expected_unloaded = [case["expected_unloaded"] for case in routing["held_out_target"]]
    first = trial["order_runs"][0]
    return {
        "target_count": len(expected_targets),
        "target_parity": sum(
            baseline == candidate
            for baseline, candidate in zip(
                first["baseline_target"], first["candidate_target"]
            )
        ),
        "candidate_target_correct": sum(
            actual == expected
            for actual, expected in zip(first["candidate_target"], expected_targets)
        ),
        "regression_count": len(expected_regressions),
        "regression_parity": sum(
            baseline == candidate
            for baseline, candidate in zip(
                first["baseline_regression"], first["candidate_regression"]
            )
        ),
        "candidate_regression_correct": sum(
            actual == expected
            for actual, expected in zip(first["candidate_regression"], expected_regressions)
        ),
        "order_count": len(trial["orders"]),
        "candidate_order_invariant": all(
            run["candidate_target"] == first["candidate_target"]
            and run["candidate_regression"] == first["candidate_regression"]
            for run in trial["order_runs"]
        ),
        "probe_parity": sum(
            run["baseline_probe"] == run["candidate_probe"]
            and run["baseline_absent"] == run["candidate_absent"]
            for run in trial["order_runs"]
        ),
        "rollback_matches_baseline": sum(
            actual == expected
            for run in trial["order_runs"]
            for actual, expected in zip(run["post_unload_target"], expected_unloaded)
        ),
        "invalid_order_count": len(trial["invalid_runs"]),
        "invalid_manifests_rejected": sum(
            run["error"] == run["expected_error"] for run in trial["invalid_runs"]
        ),
        "invalid_states_clean": sum(
            run["clean_state"] == "route-error:scope-not-found"
            for run in trial["invalid_runs"]
        ),
        "historical_v1_count": trial["historical"]["historical_v1_count"],
        "historical_v1_accepted": trial["historical"]["historical_v1_accepted"],
        "historical_v1_exact_matches": trial["historical"]["historical_v1_exact_matches"],
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
        summary["target_parity"]
        == summary["candidate_target_correct"]
        == summary["target_count"]
        == 8
        and summary["regression_parity"]
        == summary["candidate_regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["order_count"] == 2
        and summary["candidate_order_invariant"]
        and summary["probe_parity"] == 2
        and summary["rollback_matches_baseline"] == 16
        and summary["invalid_order_count"] == 8
        and summary["invalid_manifests_rejected"] == 8
        and summary["invalid_states_clean"] == 8
        and summary["historical_v1_count"]
        == summary["historical_v1_accepted"]
        == summary["historical_v1_exact_matches"]
        == 4
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
