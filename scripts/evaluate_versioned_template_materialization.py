#!/usr/bin/env python3
"""Gate a materialized v2 template and one pinned synthetic consumer."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_dependency_edge_census as census  # noqa: E402
from scripts.evaluate_public_template_v2_migration import (  # noqa: E402
    migrate_template,
    project_to_source_v1,
)
from scripts.evaluate_public_template_v2_migration_replay import (  # noqa: E402
    repaired_packages,
)
from scripts.evaluate_stable_validator_integration import (  # noqa: E402
    StableValidatorManifestKernel,
)
from scripts.validate_expert_manifest import (  # noqa: E402
    SCHEMA,
    V2_SCHEMA,
    validate_manifest,
)


DEFAULT_FIXTURE = (
    ROOT / "fixtures" / "expert_versioned_template_materialization_cases.json"
)
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "public_template",
    "v1_snapshot", "versioned_template", "reference_date", "expired_date",
    "root", "expected_baseline_materialized_consumers",
    "expected_candidate_materialized_consumers", "targets", "regression",
    "exclusion", "unloaded_expected", "expected_removal_error",
    "expected_decision",
}


def _read_pinned_at(base: Path, source: dict[str, Any], label: str) -> bytes:
    path = base / source["path"]
    try:
        payload = path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    return _read_pinned_at(ROOT, source, label)


def _canonical_payload(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-versioned-template-materialization-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    expected_sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-039-template-dependency-edge-census.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_template_dependency_edge_census_cases.json",
        ),
        "public_template": ({"path", "sha256"}, "templates/expert-package.json"),
        "v1_snapshot": (
            {"path", "sha256"},
            "templates/archive/expert-package-v1.json",
        ),
        "versioned_template": (
            {"path", "sha256"},
            "templates/expert-package-v2.json",
        ),
    }
    pinned_bytes = 0
    for name, (keys, expected_path) in expected_sources.items():
        source = fixture[name]
        if (
            not isinstance(source, dict)
            or set(source) != keys
            or source["path"] != expected_path
            or not isinstance(source["sha256"], str)
            or len(source["sha256"]) != 64
        ):
            raise ValueError(f"{name} pin is unsupported")
        pinned_bytes += len(_read_pinned(source, name.replace("_", "-")))
    if fixture["prior_experiment"].get("id") != "EXP-039":
        raise ValueError("prior experiment changed")

    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
        expired_date = date.fromisoformat(fixture["expired_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("fixture dates must be canonical dates") from exc
    if (
        reference_date.isoformat() != fixture["reference_date"]
        or expired_date.isoformat() != fixture["expired_date"]
        or expired_date <= reference_date
    ):
        raise ValueError("fixture dates must be ordered canonical dates")
    if fixture["root"] != "synthetic":
        raise ValueError("root changed")
    if (
        fixture["expected_baseline_materialized_consumers"] != 0
        or fixture["expected_candidate_materialized_consumers"] != 1
        or fixture["expected_removal_error"] != "versioned-template-missing"
        or fixture["expected_decision"] != "publish-versioned-v2-template"
    ):
        raise ValueError("locked expectations changed")

    if not isinstance(fixture["targets"], list) or len(fixture["targets"]) != 2:
        raise ValueError("fixture must contain exactly two targets")
    for case in fixture["targets"]:
        if set(case) != {"id", "request", "expected"}:
            raise ValueError("target case has unexpected structure")
    for name in ("regression", "exclusion"):
        if set(fixture[name]) != {"id", "request", "expected"}:
            raise ValueError(f"{name} case has unexpected structure")
    for case in fixture["targets"] + [fixture["regression"], fixture["exclusion"]]:
        if set(case["request"]) != {"operation", "scope", "local_id"}:
            raise ValueError("request has unexpected structure")

    prior_report = _read_pinned(fixture["prior_experiment"], "prior-experiment")
    if b"proposed path was unused" not in prior_report:
        raise ValueError("EXP-039 materialization baseline changed")
    census.load_fixture(ROOT / fixture["prior_fixture"]["path"])
    return fixture, len(payload) + pinned_bytes


def _historical_edge_summary(fixture: dict[str, Any]) -> dict[str, Any]:
    prior, _, replay_fixture, _ = census.load_fixture(
        ROOT / fixture["prior_fixture"]["path"]
    )
    expected = sorted(prior["expected_edges"], key=lambda item: (
        item["class"], item["referrer"], item["pointer"], item["source_id"]
    ))
    locked_referrers = {edge["referrer"] for edge in expected}
    observed = [
        edge
        for edge in census.census_edges(
            replay_fixture["direct_pins"], prior["evidence_fixture"]["path"]
        )
        if edge["referrer"] in locked_referrers
    ]
    return {
        "historical_edges_preserved": observed == expected,
        "historical_edge_total": len(observed),
        "historical_consumer_edges": sum(
            edge["class"] == "consumer" for edge in observed
        ),
        "historical_evidence_edges": sum(
            edge["class"] == "experiment-evidence" for edge in observed
        ),
        "historical_referrer_files": len({edge["referrer"] for edge in observed}),
    }


def _routing_trial(fixture: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    packages = repaired_packages(candidate)
    package_ids = [package["manifest"]["package_id"] for package in packages]
    by_id = {package["manifest"]["package_id"]: package for package in packages}
    orders = [package_ids, list(reversed(package_ids))]
    runs: list[dict[str, Any]] = []
    for order in orders:
        kernel = StableValidatorManifestKernel()
        kernel.compose_quarantined_experts(
            [by_id[package_id] for package_id in order],
            reference_date=date.fromisoformat(fixture["reference_date"]),
        )
        run = {
            "targets": [
                kernel.answer(case["request"]) for case in fixture["targets"]
            ],
            "regression": kernel.answer(fixture["regression"]["request"]),
            "exclusion": kernel.answer(fixture["exclusion"]["request"]),
        }
        kernel.unload_experts()
        run["unloaded"] = [
            kernel.answer(case["request"]) for case in fixture["targets"]
        ]
        runs.append(run)
    return {"orders": orders, "runs": runs}


def _removal_trial(
    fixture: dict[str, Any], public_payload: bytes, versioned_payload: bytes
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        public_path = base / fixture["public_template"]["path"]
        versioned_path = base / fixture["versioned_template"]["path"]
        public_path.parent.mkdir(parents=True)
        public_path.write_bytes(public_payload)
        versioned_path.write_bytes(versioned_payload)
        before = _read_pinned_at(
            base, fixture["versioned_template"], "versioned-template"
        )
        versioned_path.unlink()
        removal_error = ""
        try:
            _read_pinned_at(base, fixture["versioned_template"], "versioned-template")
        except ValueError as exc:
            removal_error = str(exc)
        public_after = _read_pinned_at(
            base, fixture["public_template"], "public-template"
        )
        return {
            "versioned_loaded_before_removal": before == versioned_payload,
            "versioned_removal_error": removal_error,
            "public_v1_survives_removal": public_after == public_payload,
            "versioned_absent_after_removal": not versioned_path.exists(),
        }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    public_payload = _read_pinned(fixture["public_template"], "public-template")
    snapshot_payload = _read_pinned(fixture["v1_snapshot"], "v1-snapshot")
    versioned_payload = _read_pinned(
        fixture["versioned_template"], "versioned-template"
    )
    public = json.loads(public_payload)
    candidate = json.loads(versioned_payload)
    reference_date = date.fromisoformat(fixture["reference_date"])
    expired_date = date.fromisoformat(fixture["expired_date"])
    canonical = migrate_template(public, fixture["root"])
    consumer_pins = sum(
        digest == fixture["versioned_template"]["sha256"]
        for _, digest in census._sha_edges(fixture)
    )
    routing = _routing_trial(fixture, candidate)
    expected_targets = [case["expected"] for case in fixture["targets"]]
    summary = {
        "baseline_materialized_consumers": 0,
        "candidate_materialized_consumers": consumer_pins,
        "public_v1_schema": public.get("schema") == SCHEMA,
        "public_v1_valid": validate_manifest(public, reference_date=reference_date) == [],
        "snapshot_byte_exact": snapshot_payload == public_payload,
        "versioned_v2_schema": candidate.get("schema") == V2_SCHEMA,
        "versioned_byte_canonical": versioned_payload == _canonical_payload(canonical),
        "versioned_valid": validate_manifest(candidate, reference_date=reference_date) == [],
        "versioned_expired_next_day": validate_manifest(
            candidate, reference_date=expired_date
        ) == ["expired"],
        "projection_exact": project_to_source_v1(candidate) == public,
        "target_correct": sum(
            actual == expected
            for run in routing["runs"]
            for actual, expected in zip(run["targets"], expected_targets)
        ),
        "regression_correct": sum(
            run["regression"] == fixture["regression"]["expected"]
            for run in routing["runs"]
        ),
        "exclusion_correct": sum(
            run["exclusion"] == fixture["exclusion"]["expected"]
            for run in routing["runs"]
        ),
        "order_invariant": routing["runs"][0] == routing["runs"][1],
        "rollback_correct": sum(
            answer == fixture["unloaded_expected"]
            for run in routing["runs"]
            for answer in run["unloaded"]
        ),
        "decision": fixture["expected_decision"],
    }
    summary.update(_historical_edge_summary(fixture))
    summary.update(_removal_trial(fixture, public_payload, versioned_payload))
    return summary


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["baseline_materialized_consumers"]
        == fixture["expected_baseline_materialized_consumers"]
        and summary["candidate_materialized_consumers"]
        == fixture["expected_candidate_materialized_consumers"]
        and summary["historical_edges_preserved"]
        and summary["historical_edge_total"] == 6
        and summary["historical_consumer_edges"] == 3
        and summary["historical_evidence_edges"] == 3
        and summary["historical_referrer_files"] == 4
        and all(summary[key] for key in (
            "public_v1_schema", "public_v1_valid", "snapshot_byte_exact",
            "versioned_v2_schema", "versioned_byte_canonical", "versioned_valid",
            "versioned_expired_next_day", "projection_exact", "order_invariant",
            "versioned_loaded_before_removal", "public_v1_survives_removal",
            "versioned_absent_after_removal", "repeatable",
        ))
        and summary["target_correct"] == 4
        and summary["regression_correct"] == 2
        and summary["exclusion_correct"] == 2
        and summary["rollback_correct"] == 4
        and summary["versioned_removal_error"] == fixture["expected_removal_error"]
        and summary["decision"] == fixture["expected_decision"]
        and summary["fixture_bytes"] < 32 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture, fixture_bytes = load_fixture(args.fixture)
    first = run_trial(fixture)
    repeated = run_trial(fixture)
    summary = dict(first)
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": fixture_bytes,
        "evaluation_seconds": perf_counter() - started,
        "external_calls": 0,
    })
    summary["accepted"] = accepted(summary, fixture)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
