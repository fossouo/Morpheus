#!/usr/bin/env python3
"""Evaluate stable opt-in v2 manifest validation against locked prior behavior."""

from __future__ import annotations

import argparse
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
    _load_historical_manifest,
    _v1_projection,
    build_manifest,
    candidate_errors,
    load_fixture as load_manifest_fixture,
)
from scripts.evaluate_manifest_integrated_root_routing import (  # noqa: E402
    ManifestIntegratedRootKernel,
    load_fixture as load_integration_fixture,
    run_trial as run_integration_trial,
    summarize as summarize_integration_trial,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_manifest_v2_promotion_cases.json"


def promotion_candidate_errors(
    manifest: Any, *, reference_date: date | None = None
) -> list[str]:
    """Reproduce the unpromoted v2 candidate, including pinned-date expiry."""
    errors = candidate_errors(manifest)
    if errors or reference_date is None:
        return errors
    if isinstance(manifest, dict) and manifest.get("schema") == "expert-package-v2":
        return validate_manifest(_v1_projection(manifest), reference_date=reference_date)
    return validate_manifest(manifest, reference_date=reference_date)


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
    required = {"schema", "reference_date", "manifest_fixture", "integration_fixture"}
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-manifest-v2-promotion-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")
    for name in ("manifest_fixture", "integration_fixture"):
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
    manifest_path, _ = _read_pinned_json(fixture["manifest_fixture"])
    manifest_fixture = load_manifest_fixture(manifest_path)
    if len(manifest_fixture["cases"]) != 10:
        raise ValueError("manifest source no longer matches the locked protocol")
    integration_path, _ = _read_pinned_json(fixture["integration_fixture"])
    integration_fixture = load_integration_fixture(integration_path)
    if integration_fixture["reference_date"] != "2026-08-27":
        raise ValueError("integration source reference date changed")


class PromotionCandidateManifestKernel(ManifestIntegratedRootKernel):
    """Gate EXP-027 composition through the quarantined promotion candidate."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")
        for package in packages:
            if not isinstance(package, dict) or set(package) != {
                "manifest",
                "knowledge_records",
            }:
                raise ValueError("package must contain only manifest and knowledge_records")
            errors = promotion_candidate_errors(
                package["manifest"], reference_date=reference_date
            )
            if errors:
                raise ValueError(f"invalid expert manifest: {errors}")
        super().compose_quarantined_experts(packages, reference_date=reference_date)


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    reference_date = date.fromisoformat(fixture["reference_date"])
    manifest_path, _ = _read_pinned_json(fixture["manifest_fixture"])
    manifest_fixture = load_manifest_fixture(manifest_path)

    structural_runs: list[dict[str, Any]] = []
    for case in manifest_fixture["cases"]:
        manifest = build_manifest(manifest_fixture["base_manifest"], case["mutation"])
        structural_runs.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "quarantine_errors": candidate_errors(manifest),
                "candidate_errors": promotion_candidate_errors(manifest),
            }
        )

    historical_runs: list[dict[str, Any]] = []
    for source in manifest_fixture["historical_v1_sources"]:
        manifest = _load_historical_manifest(source)
        historical_runs.append(
            {
                "id": source["id"],
                "quarantine_errors": candidate_errors(manifest),
                "candidate_errors": promotion_candidate_errors(
                    manifest, reference_date=reference_date
                ),
            }
        )

    integration_path, _ = _read_pinned_json(fixture["integration_fixture"])
    integration_fixture = load_integration_fixture(integration_path)
    quarantine_trial = run_integration_trial(integration_fixture)
    candidate_trial = run_integration_trial(
        integration_fixture,
        candidate_kernel_class=PromotionCandidateManifestKernel,
    )
    return {
        "structural_runs": structural_runs,
        "historical_runs": historical_runs,
        "quarantine_trial": quarantine_trial,
        "candidate_trial": candidate_trial,
        "integration_summary": summarize_integration_trial(
            integration_fixture, candidate_trial
        ),
    }


def summarize(trial: dict[str, Any]) -> dict[str, Any]:
    structural = trial["structural_runs"]
    historical = trial["historical_runs"]
    integration = trial["integration_summary"]
    invalid = [run for run in structural if run["expected"] == "invalid"]
    return {
        "structural_case_count": len(structural),
        "candidate_v2_exact_matches": sum(
            run["quarantine_errors"] == run["candidate_errors"] for run in structural
        ),
        "candidate_v2_correct": sum(
            (not run["candidate_errors"]) == (run["expected"] == "valid")
            for run in structural
        ),
        "candidate_v2_false_accepts": sum(
            not run["candidate_errors"] for run in invalid
        ),
        "historical_v1_count": len(historical),
        "historical_v1_accepted": sum(
            not run["candidate_errors"] for run in historical
        ),
        "historical_v1_exact_matches": sum(
            run["quarantine_errors"] == run["candidate_errors"] for run in historical
        ),
        "integration_target_parity": integration["target_parity"],
        "integration_target_count": integration["target_count"],
        "integration_regression_parity": integration["regression_parity"],
        "integration_regression_count": integration["regression_count"],
        "integration_invalid_rejected": integration["invalid_manifests_rejected"],
        "integration_invalid_count": integration["invalid_order_count"],
        "integration_clean_states": integration["invalid_states_clean"],
        "integration_rollback_matches": integration["rollback_matches_baseline"],
        "quarantine_candidate_trial_exact_match": (
            trial["quarantine_trial"] == trial["candidate_trial"]
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
    summary = summarize(first)
    summary.update(
        {
            "repeatable": first == repeated,
            "fixture_bytes": args.fixture.stat().st_size,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["structural_case_count"]
        == summary["candidate_v2_exact_matches"]
        == summary["candidate_v2_correct"]
        == 10
        and summary["candidate_v2_false_accepts"] == 0
        and summary["historical_v1_count"]
        == summary["historical_v1_accepted"]
        == summary["historical_v1_exact_matches"]
        == 4
        and summary["integration_target_parity"]
        == summary["integration_target_count"]
        == 8
        and summary["integration_regression_parity"]
        == summary["integration_regression_count"]
        == 3
        and summary["integration_invalid_rejected"]
        == summary["integration_invalid_count"]
        == summary["integration_clean_states"]
        == 8
        and summary["integration_rollback_matches"] == 16
        and summary["quarantine_candidate_trial_exact_match"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
