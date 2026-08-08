#!/usr/bin/env python3
"""Evaluate pinned-date expert expiry against the syntax-only baseline."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_expiry_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}


def _canonical_date(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("reference_date must be a canonical date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("reference_date must be a canonical date string") from exc
    if parsed.isoformat() != value:
        raise ValueError("reference_date must be a canonical date string")
    return parsed


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    if set(fixture) != {"schema", "reference_date", "base_manifest", "cases"}:
        raise ValueError("fixture has unexpected keys")
    if fixture["schema"] != "expert-expiry-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    _canonical_date(fixture["reference_date"])
    if not isinstance(fixture["base_manifest"], dict):
        raise ValueError("base_manifest must be an object")
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 7:
        raise ValueError("fixture must contain exactly seven cases")
    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "expires_on", "expected"}:
            raise ValueError("each case must have id, expires_on, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case has an invalid expected label")


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    reference_date = _canonical_date(fixture["reference_date"])
    results: list[dict[str, str]] = []
    for case in fixture["cases"]:
        manifest = deepcopy(fixture["base_manifest"])
        manifest["expires_on"] = case["expires_on"]
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": "invalid" if validate_manifest(manifest) else "valid",
                "candidate": (
                    "invalid"
                    if validate_manifest(manifest, reference_date=reference_date)
                    else "valid"
                ),
            }
        )
    return results


def summarize(results: list[dict[str, str]]) -> dict[str, int]:
    invalid_cases = [result for result in results if result["expected"] == "invalid"]
    return {
        "case_count": len(results),
        "candidate_correct": sum(result["candidate"] == result["expected"] for result in results),
        "candidate_false_accepts": sum(result["candidate"] == "valid" for result in invalid_cases),
        "baseline_false_accepts": sum(result["baseline"] == "valid" for result in invalid_cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first_results = evaluate_fixture(fixture)
    repeated_results = evaluate_fixture(fixture)
    elapsed_seconds = perf_counter() - started

    summary = summarize(first_results)
    summary.update(
        {
            "repeatable": first_results == repeated_results,
            "fixture_bytes": args.fixture.stat().st_size,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["case_count"] == 7
        and summary["candidate_correct"] == summary["case_count"]
        and summary["candidate_false_accepts"] == 0
        and summary["baseline_false_accepts"] >= 2
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
