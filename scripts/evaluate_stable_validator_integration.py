#!/usr/bin/env python3
"""Evaluate routing through the promoted stable v2 manifest validator."""

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

from scripts.evaluate_expert_manifest_v2_promotion import (  # noqa: E402
    PromotionCandidateManifestKernel,
)
from scripts.evaluate_manifest_integrated_root_routing import (  # noqa: E402
    load_fixture as load_integration_fixture,
    run_trial as run_integration_trial,
    summarize as summarize_integration_trial,
)
from scripts.evaluate_package_root_ownership import (  # noqa: E402
    PackageRootOwnershipKernel,
)
from scripts.validate_expert_manifest import SCHEMA, validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_stable_validator_integration_cases.json"


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
    required = {"schema", "reference_date", "integration_fixture"}
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-stable-validator-integration-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    source = fixture["integration_fixture"]
    if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
        raise ValueError("integration_fixture has unexpected structure")
    if (
        not isinstance(source["path"], str)
        or not source["path"].startswith("fixtures/")
        or not isinstance(source["sha256"], str)
        or len(source["sha256"]) != 64
    ):
        raise ValueError("integration_fixture must contain a fixture path and SHA-256")
    integration_path, _ = _read_pinned_source(source)
    integration = load_integration_fixture(integration_path)
    if len(integration["invalid_manifests"]) != 4:
        raise ValueError("integration source no longer matches the locked protocol")


def _project_v2_to_v1(manifest: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)
    projected.pop("root")
    projected["schema"] = SCHEMA
    return projected


class StableValidatorManifestKernel(PackageRootOwnershipKernel):
    """Validate v2 manifests natively, then reuse the locked rooted router."""

    def compose_quarantined_experts(
        self, packages: Any, *, reference_date: date
    ) -> None:
        if not isinstance(packages, list) or len(packages) < 2:
            raise ValueError("composition requires at least two expert packages")

        entries: list[dict[str, Any]] = []
        for package in packages:
            if not isinstance(package, dict) or set(package) != {
                "manifest",
                "knowledge_records",
            }:
                raise ValueError("package must contain only manifest and knowledge_records")
            manifest = package["manifest"]
            errors = validate_manifest(manifest, reference_date=reference_date)
            if errors:
                raise ValueError(f"invalid expert manifest: {errors}")
            entries.append(
                {
                    "root": manifest["root"],
                    "package": {
                        "manifest": _project_v2_to_v1(manifest),
                        "knowledge_records": copy.deepcopy(package["knowledge_records"]),
                    },
                }
            )

        super().compose_quarantined_experts(entries, reference_date=reference_date)


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    integration_path, _ = _read_pinned_source(fixture["integration_fixture"])
    integration = load_integration_fixture(integration_path)
    integration = copy.deepcopy(integration)
    integration["reference_date"] = fixture["reference_date"]

    baseline = run_integration_trial(
        integration, candidate_kernel_class=PromotionCandidateManifestKernel
    )
    candidate = run_integration_trial(
        integration, candidate_kernel_class=StableValidatorManifestKernel
    )
    return {
        "baseline": baseline,
        "candidate": candidate,
        "candidate_summary": summarize_integration_trial(integration, candidate),
    }


def summarize(trial: dict[str, Any]) -> dict[str, Any]:
    candidate = trial["candidate_summary"]
    return {
        "trial_exact_match": trial["baseline"] == trial["candidate"],
        "target_parity": candidate["target_parity"],
        "target_count": candidate["target_count"],
        "target_correct": candidate["candidate_target_correct"],
        "regression_parity": candidate["regression_parity"],
        "regression_count": candidate["regression_count"],
        "regression_correct": candidate["candidate_regression_correct"],
        "order_invariant": candidate["candidate_order_invariant"],
        "probe_parity": candidate["probe_parity"],
        "invalid_rejected": candidate["invalid_manifests_rejected"],
        "invalid_count": candidate["invalid_order_count"],
        "clean_states": candidate["invalid_states_clean"],
        "rollback_matches": candidate["rollback_matches_baseline"],
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
    _, source_bytes = _read_pinned_source(fixture["integration_fixture"])
    summary.update(
        {
            "repeatable": first == repeated,
            "fixture_bytes": args.fixture.stat().st_size + len(source_bytes),
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["trial_exact_match"]
        and summary["target_parity"]
        == summary["target_correct"]
        == summary["target_count"]
        == 8
        and summary["regression_parity"]
        == summary["regression_correct"]
        == summary["regression_count"]
        == 3
        and summary["order_invariant"]
        and summary["probe_parity"] == 2
        and summary["invalid_rejected"]
        == summary["invalid_count"]
        == summary["clean_states"]
        == 8
        and summary["rollback_matches"] == 16
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
