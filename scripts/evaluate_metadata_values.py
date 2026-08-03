#!/usr/bin/env python3
"""Evaluate placeholder-aware metadata validation against the prior contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_records import METADATA_RE, validate_record  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "metadata_value_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}
MUTATIONS = {
    "none",
    "template_data",
    "tbd_data",
    "todo_data",
    "pending_data",
    "na_data",
    "empty_data",
    "whitespace_data",
}
FILENAME = "EXP-902-synthetic-metadata-value-record.md"
PLACEHOLDER_DATA_VALUES = {
    "synthetic/public/other-safe-description",
    "tbd",
    "todo",
    "pending",
    "n/a",
}

BASE_RECORD = """# EXP-902 — Synthetic metadata-value record

- **Schema**: strict-v1
- **Date**: 2026-08-03
- **Status**: running
- **Compute**: C0
- **Data**: eight synthetic metadata-value cases

## Question

Does required metadata contain a declared non-placeholder value?

## Hypothesis

Known placeholder metadata values will be rejected.

## Baseline

Require metadata presence and existing typed-field checks.

## Protocol

Apply one deterministic Data mutation per case.

## Metrics

Classification accuracy and false accepts.

## Acceptance and stop criteria

Accept at 8/8 correct with zero false accepts; stop after eight cases.

## Results

Execution is reserved until the fixture is locked.

## Interpretation

This fixture tests exact structural markers only.

## Limitations

No general semantic-quality claim is made.

## Decision

`inconclusive`
"""


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    if set(fixture) != {"schema", "cases"} or fixture["schema"] != "strict-v1-metadata-value-v1":
        raise ValueError("fixture must declare only the metadata-value schema and cases")
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 8:
        raise ValueError("fixture must contain exactly eight cases")
    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "mutation", "expected"}:
            raise ValueError("each case must have id, mutation, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if case["mutation"] not in MUTATIONS or case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case contains an unsupported mutation or expected label")


def apply_mutation(mutation: str) -> str:
    replacements = {
        "template_data": "synthetic/public/other-safe-description",
        "tbd_data": "TBD.",
        "todo_data": "TODO",
        "pending_data": "`pending`",
        "na_data": "N/A",
        "empty_data": "",
        "whitespace_data": "   ",
    }
    if mutation == "none":
        return BASE_RECORD
    old = "- **Data**: eight synthetic metadata-value cases"
    return BASE_RECORD.replace(old, f"- **Data**: {replacements[mutation]}")


def _normalized_value(value: str) -> str:
    return " ".join(value.strip("` \t\r\n.").split()).casefold()


def candidate_errors(text: str) -> list[str]:
    errors = validate_record(text, FILENAME)
    for match in METADATA_RE.finditer(text):
        if match.group("key") == "Data" and _normalized_value(match.group("value")) in {
            _normalized_value(value) for value in PLACEHOLDER_DATA_VALUES
        }:
            errors.append("placeholder-metadata:Data")
    return sorted(set(errors))


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for case in fixture["cases"]:
        text = apply_mutation(case["mutation"])
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": "invalid" if validate_record(text, FILENAME) else "valid",
                "candidate": "invalid" if candidate_errors(text) else "valid",
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
        summary["case_count"] == 8
        and summary["candidate_correct"] == summary["case_count"]
        and summary["candidate_false_accepts"] == 0
        and summary["baseline_false_accepts"] >= 5
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
