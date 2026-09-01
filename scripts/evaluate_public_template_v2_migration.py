#!/usr/bin/env python3
"""Evaluate a reversible v1-to-v2 migration of the public expert template."""

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
from scripts.evaluate_stable_validator_integration import (  # noqa: E402
    StableValidatorManifestKernel,
)
from scripts.validate_expert_manifest import (  # noqa: E402
    SCHEMA,
    V2_SCHEMA,
    validate_manifest,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_public_template_v2_migration_cases.json"


def _read_pinned_template(source: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError("public template hash mismatch")
    return json.loads(payload), payload


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {
        "schema", "reference_date", "expired_date", "root", "template",
        "targets", "regression", "exclusion", "unloaded_expected",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-public-template-v2-migration-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
        expired_date = date.fromisoformat(fixture["expired_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("fixture dates must be canonical calendar dates") from exc
    if (
        reference_date.isoformat() != fixture["reference_date"]
        or expired_date.isoformat() != fixture["expired_date"]
        or expired_date <= reference_date
    ):
        raise ValueError("fixture dates must be ordered canonical calendar dates")
    if not isinstance(fixture["root"], str) or not fixture["root"] or "/" in fixture["root"]:
        raise ValueError("root must be one literal segment")
    source = fixture["template"]
    if (
        not isinstance(source, dict)
        or set(source) != {"path", "sha256"}
        or source["path"] != "templates/expert-package.json"
        or not isinstance(source["sha256"], str)
        or len(source["sha256"]) != 64
    ):
        raise ValueError("template must contain the public path and SHA-256")
    template, _ = _read_pinned_template(source)
    if template.get("schema") != SCHEMA:
        raise ValueError("source template must remain v1")
    if len(fixture["targets"]) != 2:
        raise ValueError("fixture must contain exactly two targets")
    for case in fixture["targets"]:
        if not isinstance(case, dict) or set(case) != {"id", "request", "expected"}:
            raise ValueError("target case has unexpected structure")
    for name in ("regression", "exclusion"):
        case = fixture[name]
        expected = {"id", "request", "expected"} if name == "regression" else {"request", "expected"}
        if not isinstance(case, dict) or set(case) != expected:
            raise ValueError(f"{name} case has unexpected structure")


def migrate_template(template: dict[str, Any], root: str) -> dict[str, Any]:
    migrated = copy.deepcopy(template)
    migrated["schema"] = V2_SCHEMA
    migrated["root"] = root
    for name in ("include", "exclude"):
        migrated["scope"][name] = [
            f"{root}/{pattern}" for pattern in migrated["scope"][name]
        ]
    return migrated


def project_to_source_v1(manifest: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)
    root = projected.pop("root")
    projected["schema"] = SCHEMA
    prefix = f"{root}/"
    for name in ("include", "exclude"):
        if any(not pattern.startswith(prefix) for pattern in projected["scope"][name]):
            raise ValueError("migration projection encountered an unrooted scope")
        projected["scope"][name] = [
            pattern[len(prefix):] for pattern in projected["scope"][name]
        ]
    return projected


def _routing_v1(manifest: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)
    projected.pop("root")
    projected["schema"] = SCHEMA
    return projected


def _peer_manifest(source: dict[str, Any]) -> dict[str, Any]:
    peer = copy.deepcopy(source)
    peer["package_id"] = "synthetic-peer"
    peer["root"] = "auxiliary"
    peer["scope"] = {
        "include": ["auxiliary/peer-task"],
        "exclude": ["auxiliary/blocked"],
    }
    peer["provenance"] = [{
        "source_id": "SRC-002",
        "kind": "synthetic",
        "reference": "fixture:public-template-v2-peer",
    }]
    peer["layers"] = {
        "knowledge": ["synthetic-peer-format-v1"],
        "experience": [],
        "skills": ["synthetic-peer-skill-v1"],
        "tools": [],
        "adapters": [],
    }
    peer["tests"] = {"target": ["TGT-002"], "held_out_regression": ["REG-001"]}
    return peer


def _packages(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    peer = _peer_manifest(candidate)
    return [
        {
            "manifest": candidate,
            "knowledge_records": {"synthetic-notice-format-v1": "template-answer"},
        },
        {
            "manifest": peer,
            "knowledge_records": {"synthetic-peer-format-v1": "peer-answer"},
        },
    ]


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    template, _ = _read_pinned_template(fixture["template"])
    reference_date = date.fromisoformat(fixture["reference_date"])
    expired_date = date.fromisoformat(fixture["expired_date"])
    candidate = migrate_template(template, fixture["root"])
    packages = _packages(candidate)
    package_ids = [package["manifest"]["package_id"] for package in packages]
    by_id = {package["manifest"]["package_id"]: package for package in packages}
    orders = [package_ids, list(reversed(package_ids))]

    order_runs: list[dict[str, Any]] = []
    for order in orders:
        ordered = [by_id[package_id] for package_id in order]
        baseline = PackageRootOwnershipKernel()
        baseline.compose_quarantined_experts(
            [
                {
                    "root": package["manifest"]["root"],
                    "package": {
                        "manifest": _routing_v1(package["manifest"]),
                        "knowledge_records": copy.deepcopy(package["knowledge_records"]),
                    },
                }
                for package in ordered
            ],
            reference_date=reference_date,
        )
        stable = StableValidatorManifestKernel()
        stable.compose_quarantined_experts(ordered, reference_date=reference_date)
        baseline_targets = [baseline.answer(case["request"]) for case in fixture["targets"]]
        stable_targets = [stable.answer(case["request"]) for case in fixture["targets"]]
        baseline_regression = baseline.answer(fixture["regression"]["request"])
        stable_regression = stable.answer(fixture["regression"]["request"])
        baseline_exclusion = baseline.answer(fixture["exclusion"]["request"])
        stable_exclusion = stable.answer(fixture["exclusion"]["request"])
        stable.unload_experts()
        unloaded = [stable.answer(case["request"]) for case in fixture["targets"]]
        order_runs.append({
            "baseline_targets": baseline_targets,
            "stable_targets": stable_targets,
            "baseline_regression": baseline_regression,
            "stable_regression": stable_regression,
            "baseline_exclusion": baseline_exclusion,
            "stable_exclusion": stable_exclusion,
            "unloaded": unloaded,
        })

    return {
        "baseline_errors": validate_manifest(template, reference_date=reference_date),
        "candidate_errors": validate_manifest(candidate, reference_date=reference_date),
        "expired_errors": validate_manifest(candidate, reference_date=expired_date),
        "projection_exact": project_to_source_v1(candidate) == template,
        "orders": orders,
        "order_runs": order_runs,
    }


def summarize(fixture: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    expected_targets = [case["expected"] for case in fixture["targets"]]
    expected_regression = fixture["regression"]["expected"]
    expected_exclusion = fixture["exclusion"]["expected"]
    expected_unloaded = fixture["unloaded_expected"]
    first = trial["order_runs"][0]
    return {
        "baseline_valid": trial["baseline_errors"] == [],
        "candidate_valid": trial["candidate_errors"] == [],
        "candidate_expired_next_day": trial["expired_errors"] == ["expired"],
        "projection_exact": trial["projection_exact"],
        "target_count": len(expected_targets),
        "target_parity": sum(
            baseline == stable
            for baseline, stable in zip(first["baseline_targets"], first["stable_targets"])
        ),
        "target_correct": sum(
            actual == expected
            for actual, expected in zip(first["stable_targets"], expected_targets)
        ),
        "regression_parity": sum(
            run["baseline_regression"] == run["stable_regression"] == expected_regression
            for run in trial["order_runs"]
        ),
        "exclusion_parity": sum(
            run["baseline_exclusion"] == run["stable_exclusion"] == expected_exclusion
            for run in trial["order_runs"]
        ),
        "order_invariant": all(
            run["stable_targets"] == first["stable_targets"]
            for run in trial["order_runs"]
        ),
        "rollback_matches": sum(
            actual == expected_unloaded
            for run in trial["order_runs"]
            for actual in run["unloaded"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    try:
        first = run_trial(fixture)
        repeated = run_trial(fixture)
    except ValueError as exc:
        elapsed_seconds = perf_counter() - started
        _, template_bytes = _read_pinned_template(fixture["template"])
        print(json.dumps({
            "accepted": False,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
            "failure": str(exc),
            "fixture_bytes": args.fixture.stat().st_size + len(template_bytes),
            "stage": "first-order-baseline-composition",
        }, sort_keys=True))
        return 1
    elapsed_seconds = perf_counter() - started
    summary = summarize(fixture, first)
    _, template_bytes = _read_pinned_template(fixture["template"])
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": args.fixture.stat().st_size + len(template_bytes),
        "evaluation_seconds": round(elapsed_seconds, 6),
        "external_calls": 0,
    })
    summary["accepted"] = (
        summary["baseline_valid"]
        and summary["candidate_valid"]
        and summary["candidate_expired_next_day"]
        and summary["projection_exact"]
        and summary["target_parity"] == summary["target_correct"] == summary["target_count"] == 2
        and summary["regression_parity"] == 2
        and summary["exclusion_parity"] == 2
        and summary["order_invariant"]
        and summary["rollback_matches"] == 4
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
