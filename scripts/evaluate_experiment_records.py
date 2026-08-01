#!/usr/bin/env python3
"""Evaluate strict experiment-record validation against a title-only baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_records import title_errors, validate_record  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "experiment_record_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}
MUTATIONS = {
    "none",
    "missing_hypothesis",
    "missing_baseline",
    "duplicate_metrics",
    "invalid_status",
    "mismatched_id",
    "missing_decision",
}

BASE_RECORD = """# EXP-900 — Synthetic strict record

- **Schema**: strict-v1
- **Date**: 2026-08-01
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic

## Question

Does this record satisfy the structural contract?

## Hypothesis

The complete record is valid.

## Baseline

Title-only validation.

## Protocol

Perform one deterministic validation.

## Metrics

Structural validity.

## Acceptance and stop criteria

Accept if every required field is present; stop after one validation.

## Results

The synthetic record was evaluated.

## Interpretation

This is a structural fixture only.

## Limitations

It does not establish scientific quality.

## Decision

`pass`
"""


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    if set(fixture) != {"schema", "cases"} or fixture["schema"] != "strict-v1":
        raise ValueError("fixture must declare only the strict-v1 schema and cases")
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 7:
        raise ValueError("fixture must contain exactly seven cases")
    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "mutation", "expected"}:
            raise ValueError("each case must have id, mutation, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if case["mutation"] not in MUTATIONS or case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case contains an unsupported mutation or expected label")


def _remove_section(text: str, section: str) -> str:
    marker = f"## {section}\n"
    start = text.index(marker)
    next_start = text.find("\n## ", start + len(marker))
    end = len(text) if next_start == -1 else next_start + 1
    return text[:start] + text[end:]


def apply_mutation(mutation: str) -> str:
    if mutation == "none":
        return BASE_RECORD
    if mutation == "missing_hypothesis":
        return _remove_section(BASE_RECORD, "Hypothesis")
    if mutation == "missing_baseline":
        return _remove_section(BASE_RECORD, "Baseline")
    if mutation == "duplicate_metrics":
        duplicate = "## Metrics\n\nDuplicate metrics.\n\n"
        return BASE_RECORD.replace("## Acceptance and stop criteria", duplicate + "## Acceptance and stop criteria")
    if mutation == "invalid_status":
        return BASE_RECORD.replace("- **Status**: complete", "- **Status**: accepted")
    if mutation == "mismatched_id":
        return BASE_RECORD.replace("# EXP-900 —", "# EXP-901 —", 1)
    if mutation == "missing_decision":
        return _remove_section(BASE_RECORD, "Decision")
    raise ValueError(f"unsupported mutation: {mutation}")


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for case in fixture["cases"]:
        text = apply_mutation(case["mutation"])
        filename = "EXP-900-synthetic-strict-record.md"
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": "invalid" if title_errors(text, filename) else "valid",
                "strict": "invalid" if validate_record(text, filename) else "valid",
            }
        )
    return results


def summarize(results: list[dict[str, str]]) -> dict[str, int]:
    invalid_cases = [result for result in results if result["expected"] == "invalid"]
    return {
        "case_count": len(results),
        "strict_correct": sum(result["strict"] == result["expected"] for result in results),
        "strict_false_accepts": sum(result["strict"] == "valid" for result in invalid_cases),
        "baseline_false_accepts": sum(result["baseline"] == "valid" for result in invalid_cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    fixture_bytes = args.fixture.stat().st_size
    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first_results = evaluate_fixture(fixture)
    repeated_results = evaluate_fixture(fixture)
    elapsed_seconds = perf_counter() - started

    summary = summarize(first_results)
    summary.update(
        {
            "repeatable": first_results == repeated_results,
            "fixture_bytes": fixture_bytes,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["case_count"] == 7
        and summary["strict_correct"] == summary["case_count"]
        and summary["strict_false_accepts"] == 0
        and summary["baseline_false_accepts"] >= 4
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
