#!/usr/bin/env python3
"""Evaluate held-out recall before, during, and after a quarantined expert load."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_lookup_cases.json"


class StableKernel:
    """A fixed request handler with optional, unloadable exact-match knowledge."""

    def __init__(self) -> None:
        self._knowledge: dict[str, str] = {}

    def answer(self, request: Any) -> str:
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        operation = request.get("operation")
        if operation == "echo" and set(request) == {"operation", "value"}:
            value = request["value"]
            if not isinstance(value, str):
                raise ValueError("echo value must be a string")
            return value
        if operation == "recall" and set(request) == {"operation", "key"}:
            key = request["key"]
            if not isinstance(key, str) or not key:
                raise ValueError("recall key must be a non-empty string")
            return self._knowledge.get(key, "unknown")
        raise ValueError("unsupported request")

    def load_quarantined_expert(
        self,
        manifest: Any,
        knowledge_records: Any,
        *,
        reference_date: date,
    ) -> None:
        if self._knowledge:
            raise ValueError("an expert is already loaded")
        errors = validate_manifest(manifest, reference_date=reference_date)
        if errors:
            raise ValueError(f"invalid expert manifest: {errors}")
        if any(source["kind"] != "synthetic" for source in manifest["provenance"]):
            raise ValueError("this evaluator permits synthetic provenance only")
        records = _validate_knowledge_records(knowledge_records)
        declared = set(manifest["layers"]["knowledge"])
        if set(records) != declared:
            raise ValueError("knowledge records must exactly match declared knowledge ids")
        self._knowledge = records

    def unload_expert(self) -> None:
        self._knowledge = {}


def _validate_knowledge_records(value: Any) -> dict[str, str]:
    if not isinstance(value, list) or not value:
        raise ValueError("knowledge_records must be a non-empty list")
    records: dict[str, str] = {}
    for record in value:
        if not isinstance(record, dict) or set(record) != {"id", "value"}:
            raise ValueError("each knowledge record must contain only id and value")
        record_id = record["id"]
        record_value = record["value"]
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("knowledge record ids must be non-empty strings")
        if not isinstance(record_value, str) or not record_value:
            raise ValueError("knowledge record values must be non-empty strings")
        if record_id in records:
            raise ValueError("knowledge record ids must be unique")
        records[record_id] = record_value
    return records


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    if not isinstance(fixture, dict) or set(fixture) != {
        "schema",
        "reference_date",
        "package",
        "held_out_target",
        "held_out_regression",
    }:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-lookup-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical calendar date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical calendar date")

    package = fixture["package"]
    if not isinstance(package, dict) or set(package) != {"manifest", "knowledge_records"}:
        raise ValueError("package must contain only manifest and knowledge_records")
    kernel = StableKernel()
    kernel.load_quarantined_expert(
        package["manifest"], package["knowledge_records"], reference_date=reference_date
    )

    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    if not isinstance(targets, list) or len(targets) != 6:
        raise ValueError("fixture must contain exactly six target cases")
    if not isinstance(regressions, list) or len(regressions) != 4:
        raise ValueError("fixture must contain exactly four regression cases")

    target_ids = _validate_cases(
        targets, required_keys={"id", "request", "expected_unloaded", "expected_loaded"}
    )
    regression_ids = _validate_cases(
        regressions, required_keys={"id", "request", "expected"}
    )
    manifest_tests = package["manifest"]["tests"]
    if target_ids != manifest_tests["target"]:
        raise ValueError("target case ids must match the manifest in order")
    if regression_ids != manifest_tests["held_out_regression"]:
        raise ValueError("regression case ids must match the manifest in order")


def _validate_cases(cases: list[Any], *, required_keys: set[str]) -> list[str]:
    ids: list[str] = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != required_keys:
            raise ValueError("case has unexpected structure")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("case ids must be non-empty and unique")
        ids.append(case_id)
        if not isinstance(case["request"], dict):
            raise ValueError("case request must be an object")
        for key in required_keys - {"id", "request"}:
            if not isinstance(case[key], str):
                raise ValueError("expected responses must be strings")
    return ids


def run_transition(fixture: dict[str, Any]) -> dict[str, list[str]]:
    kernel = StableKernel()
    targets = fixture["held_out_target"]
    regressions = fixture["held_out_regression"]
    baseline_target = [kernel.answer(case["request"]) for case in targets]
    baseline_regression = [kernel.answer(case["request"]) for case in regressions]

    package = fixture["package"]
    kernel.load_quarantined_expert(
        package["manifest"],
        package["knowledge_records"],
        reference_date=date.fromisoformat(fixture["reference_date"]),
    )
    loaded_target = [kernel.answer(case["request"]) for case in targets]
    loaded_regression = [kernel.answer(case["request"]) for case in regressions]

    kernel.unload_expert()
    post_unload_target = [kernel.answer(case["request"]) for case in targets]
    return {
        "baseline_target": baseline_target,
        "loaded_target": loaded_target,
        "baseline_regression": baseline_regression,
        "loaded_regression": loaded_regression,
        "post_unload_target": post_unload_target,
    }


def summarize(fixture: dict[str, Any], transition: dict[str, list[str]]) -> dict[str, int | float]:
    expected_unloaded = [case["expected_unloaded"] for case in fixture["held_out_target"]]
    expected_loaded = [case["expected_loaded"] for case in fixture["held_out_target"]]
    expected_regression = [case["expected"] for case in fixture["held_out_regression"]]
    target_count = len(expected_loaded)
    regression_count = len(expected_regression)
    baseline_target_correct = sum(
        actual == expected
        for actual, expected in zip(transition["baseline_target"], expected_loaded)
    )
    loaded_target_correct = sum(
        actual == expected
        for actual, expected in zip(transition["loaded_target"], expected_loaded)
    )
    baseline_regression_correct = sum(
        actual == expected
        for actual, expected in zip(transition["baseline_regression"], expected_regression)
    )
    loaded_regression_correct = sum(
        actual == expected
        for actual, expected in zip(transition["loaded_regression"], expected_regression)
    )
    return {
        "target_count": target_count,
        "baseline_target_correct": baseline_target_correct,
        "loaded_target_correct": loaded_target_correct,
        "target_accuracy_gain": round(
            (loaded_target_correct - baseline_target_correct) / target_count, 6
        ),
        "regression_count": regression_count,
        "baseline_regression_correct": baseline_regression_correct,
        "loaded_regression_correct": loaded_regression_correct,
        "regression_accuracy_drop": round(
            (baseline_regression_correct - loaded_regression_correct) / regression_count, 6
        ),
        "rollback_matches_baseline": sum(
            actual == expected
            for actual, expected in zip(transition["post_unload_target"], expected_unloaded)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first = run_transition(fixture)
    repeated = run_transition(fixture)
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
        summary["baseline_target_correct"] == 0
        and summary["loaded_target_correct"] == summary["target_count"] == 6
        and summary["target_accuracy_gain"] == 1.0
        and summary["baseline_regression_correct"]
        == summary["loaded_regression_correct"]
        == summary["regression_count"]
        == 4
        and summary["regression_accuracy_drop"] == 0.0
        and summary["rollback_matches_baseline"] == summary["target_count"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
