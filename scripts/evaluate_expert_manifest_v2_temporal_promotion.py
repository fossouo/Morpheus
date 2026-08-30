#!/usr/bin/env python3
"""Evaluate v2 promotion with separate structural and temporal expectations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_manifest_root import (  # noqa: E402
    V2_SCHEMA,
    build_manifest,
    load_fixture as load_manifest_fixture,
)
from scripts.evaluate_expert_manifest_temporal_corpus import (  # noqa: E402
    load_fixture as load_temporal_fixture,
    run_trial as run_temporal_trial,
    summarize as summarize_temporal_trial,
)
from scripts.evaluate_expert_manifest_v2_promotion import (  # noqa: E402
    PromotionCandidateManifestKernel,
    promotion_candidate_errors,
)
from scripts.evaluate_manifest_integrated_root_routing import (  # noqa: E402
    load_fixture as load_integration_fixture,
    run_trial as run_integration_trial,
    summarize as summarize_integration_trial,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_manifest_v2_temporal_promotion_cases.json"
SOURCE_NAMES = {"manifest_fixture", "integration_fixture", "temporal_fixture"}


def _read_pinned_source(source: dict[str, Any]) -> tuple[Path, bytes]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"source fixture hash mismatch:{source['path']}")
    return path, payload


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    if not isinstance(fixture, dict) or set(fixture) != {"schema", *SOURCE_NAMES}:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-manifest-v2-temporal-promotion-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    for name in SOURCE_NAMES:
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

    manifest_path, _ = _read_pinned_source(fixture["manifest_fixture"])
    manifest_fixture = load_manifest_fixture(manifest_path)
    if len(manifest_fixture["cases"]) != 10:
        raise ValueError("manifest source no longer matches the locked protocol")

    integration_path, _ = _read_pinned_source(fixture["integration_fixture"])
    integration_fixture = load_integration_fixture(integration_path)
    if integration_fixture["reference_date"] != "2026-08-27":
        raise ValueError("integration source reference date changed")

    temporal_path, _ = _read_pinned_source(fixture["temporal_fixture"])
    temporal_fixture = load_temporal_fixture(temporal_path)
    if temporal_fixture["promotion_reference_date"] != "2026-08-28":
        raise ValueError("temporal source promotion date changed")


def frozen_v1_baseline_errors(manifest: Any) -> list[str]:
    """Freeze the pre-promotion stable behavior for opt-in v2 manifests."""
    if isinstance(manifest, dict) and manifest.get("schema") == V2_SCHEMA:
        return ["unsupported-schema"]
    return validate_manifest(manifest)


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    manifest_path, _ = _read_pinned_source(fixture["manifest_fixture"])
    manifest_fixture = load_manifest_fixture(manifest_path)
    structural_runs: list[dict[str, Any]] = []
    for case in manifest_fixture["cases"]:
        manifest = build_manifest(manifest_fixture["base_manifest"], case["mutation"])
        structural_runs.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "expected_candidate_error": case["expected_candidate_error"],
                "baseline_errors": frozen_v1_baseline_errors(manifest),
                "candidate_errors": promotion_candidate_errors(manifest),
            }
        )

    temporal_path, _ = _read_pinned_source(fixture["temporal_fixture"])
    temporal_fixture = load_temporal_fixture(temporal_path)
    temporal_trial = run_temporal_trial(temporal_fixture)

    integration_path, _ = _read_pinned_source(fixture["integration_fixture"])
    integration_fixture = load_integration_fixture(integration_path)
    quarantine_trial = run_integration_trial(integration_fixture)
    candidate_trial = run_integration_trial(
        integration_fixture,
        candidate_kernel_class=PromotionCandidateManifestKernel,
    )
    return {
        "structural_runs": structural_runs,
        "temporal_trial": temporal_trial,
        "temporal_summary": summarize_temporal_trial(temporal_trial),
        "quarantine_trial": quarantine_trial,
        "candidate_trial": candidate_trial,
        "integration_summary": summarize_integration_trial(
            integration_fixture, candidate_trial
        ),
    }


def summarize(trial: dict[str, Any]) -> dict[str, Any]:
    structural = trial["structural_runs"]
    valid = [run for run in structural if run["expected"] == "valid"]
    temporal = trial["temporal_summary"]
    integration = trial["integration_summary"]
    return {
        "structural_case_count": len(structural),
        "baseline_structural_correct": sum(
            (not run["baseline_errors"]) == (run["expected"] == "valid")
            for run in structural
        ),
        "baseline_valid_v2_rejected": sum(bool(run["baseline_errors"]) for run in valid),
        "candidate_structural_correct": sum(
            (not run["candidate_errors"]) == (run["expected"] == "valid")
            for run in structural
        ),
        "candidate_structural_false_accepts": sum(
            not run["candidate_errors"]
            for run in structural
            if run["expected"] == "invalid"
        ),
        "candidate_structural_expected_errors": sum(
            run["expected_candidate_error"] is None
            and not run["candidate_errors"]
            or run["expected_candidate_error"] in run["candidate_errors"]
            for run in structural
        ),
        "temporal_source_count": temporal["source_count"],
        "temporal_structural_exact_matches": temporal["structural_exact_matches"],
        "temporal_lifecycle_case_count": temporal["lifecycle_case_count"],
        "temporal_lifecycle_exact_matches": temporal[
            "candidate_lifecycle_exact_matches"
        ],
        "temporal_false_accepts": temporal["candidate_false_accepts"],
        "promotion_date_exact_matches": temporal["promotion_date_exact_matches"],
        "promotion_date_accepted": temporal["promotion_date_accepted"],
        "promotion_date_expired": temporal["promotion_date_expired"],
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
    source_bytes = sum(
        len(_read_pinned_source(fixture[name])[1]) for name in SOURCE_NAMES
    )
    summary.update(
        {
            "repeatable": first == repeated,
            "fixture_bytes": args.fixture.stat().st_size + source_bytes,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["structural_case_count"] == 10
        and summary["baseline_structural_correct"] == 8
        and summary["baseline_valid_v2_rejected"] == 2
        and summary["candidate_structural_correct"] == 10
        and summary["candidate_structural_false_accepts"] == 0
        and summary["candidate_structural_expected_errors"] == 10
        and summary["temporal_source_count"]
        == summary["temporal_structural_exact_matches"]
        == 4
        and summary["temporal_lifecycle_case_count"]
        == summary["temporal_lifecycle_exact_matches"]
        == 16
        and summary["temporal_false_accepts"] == 0
        and summary["promotion_date_exact_matches"] == 4
        and summary["promotion_date_accepted"] == 3
        and summary["promotion_date_expired"] == 1
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
