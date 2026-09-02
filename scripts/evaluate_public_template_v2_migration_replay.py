#!/usr/bin/env python3
"""Replay the public-template migration gate with one record-shape repair."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_public_template_v2_migration import (  # noqa: E402
    _packages as failed_packages,
    load_fixture as load_source_fixture,
    migrate_template,
    run_trial as run_source_trial,
    summarize,
)


DEFAULT_FIXTURE = (
    ROOT / "fixtures" / "expert_public_template_v2_migration_replay_cases.json"
)
BASELINE_FAILURE = "knowledge_records must be a non-empty list"


def _read_pinned_source(source: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError("source fixture hash mismatch")
    fixture = load_source_fixture(path)
    return fixture, payload


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    if not isinstance(fixture, dict) or set(fixture) != {
        "schema", "source_fixture", "adapter_change",
    }:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-public-template-v2-migration-replay-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    if fixture["adapter_change"] != "knowledge-record-mapping-to-sorted-list":
        raise ValueError("fixture has an unsupported adapter change")
    source = fixture["source_fixture"]
    if (
        not isinstance(source, dict)
        or set(source) != {"path", "sha256"}
        or source["path"] != "fixtures/expert_public_template_v2_migration_cases.json"
        or not isinstance(source["sha256"], str)
        or len(source["sha256"]) != 64
    ):
        raise ValueError("source fixture must contain the EXP-032 path and SHA-256")
    _read_pinned_source(source)


def repaired_packages(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Change only the knowledge-record container used by EXP-032's adapter."""

    packages = failed_packages(candidate)
    repaired = copy.deepcopy(packages)
    for package in repaired:
        records = package["knowledge_records"]
        package["knowledge_records"] = [
            {"id": record_id, "value": value}
            for record_id, value in sorted(records.items())
        ]
    return repaired


def adapter_change_is_shape_only(candidate: dict[str, Any]) -> bool:
    before = failed_packages(candidate)
    after = repaired_packages(candidate)
    if len(before) != len(after):
        return False
    for original, repaired in zip(before, after):
        if original["manifest"] != repaired["manifest"]:
            return False
        expected = [
            {"id": record_id, "value": value}
            for record_id, value in sorted(original["knowledge_records"].items())
        ]
        if repaired["knowledge_records"] != expected:
            return False
    return True


def reproduce_baseline_failure(source_fixture: dict[str, Any]) -> str:
    try:
        run_source_trial(source_fixture)
    except ValueError as exc:
        return str(exc)
    return ""


def run_trial(source_fixture: dict[str, Any]) -> dict[str, Any]:
    return run_source_trial(source_fixture, package_builder=repaired_packages)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    source_fixture, source_bytes = _read_pinned_source(fixture["source_fixture"])
    template_path = ROOT / source_fixture["template"]["path"]
    template = json.loads(template_path.read_text(encoding="utf-8"))
    candidate = migrate_template(template, source_fixture["root"])

    baseline_failure = reproduce_baseline_failure(source_fixture)
    first = run_trial(source_fixture)
    repeated = run_trial(source_fixture)
    elapsed_seconds = perf_counter() - started

    summary = summarize(source_fixture, first)
    summary.update({
        "adapter_change_is_shape_only": adapter_change_is_shape_only(candidate),
        "baseline_failure": baseline_failure,
        "baseline_failure_reproduced": baseline_failure == BASELINE_FAILURE,
        "repeatable": first == repeated,
        "fixture_bytes": (
            args.fixture.stat().st_size
            + len(source_bytes)
            + template_path.stat().st_size
        ),
        "evaluation_seconds": round(elapsed_seconds, 6),
        "external_calls": 0,
    })
    summary["accepted"] = (
        summary["adapter_change_is_shape_only"]
        and summary["baseline_failure_reproduced"]
        and summary["baseline_valid"]
        and summary["candidate_valid"]
        and summary["candidate_expired_next_day"]
        and summary["projection_exact"]
        and summary["target_parity"]
        == summary["target_correct"]
        == summary["target_count"]
        == 2
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
