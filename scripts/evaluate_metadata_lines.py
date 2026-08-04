#!/usr/bin/env python3
"""Evaluate line-bounded metadata parsing against the prior strict contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_records import (  # noqa: E402
    LEGACY_METADATA_RE,
    METADATA_RE,
    metadata_values,
    validate_record,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "metadata_line_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}
FIELDS = {"Schema", "Date", "Status", "Compute", "Data"}
BLANK_MUTATIONS = {
    f"{kind}_{field.lower()}"
    for kind in ("empty", "whitespace")
    for field in FIELDS
}
PLACEHOLDER_MUTATIONS = {
    "template_data",
    "tbd_data",
    "todo_data",
    "pending_data",
    "na_data",
}
MUTATIONS = {"none"} | BLANK_MUTATIONS | PLACEHOLDER_MUTATIONS
FILENAME = "EXP-903-synthetic-metadata-line-record.md"

BASE_VALUES = {
    "Schema": "strict-v1",
    "Date": "2026-08-04",
    "Status": "running",
    "Compute": "C0",
    "Data": "sixteen synthetic metadata-line cases",
}

BASE_RECORD = """# EXP-903 — Synthetic metadata-line record

- **Schema**: strict-v1
- **Date**: 2026-08-04
- **Status**: running
- **Compute**: C0
- **Data**: sixteen synthetic metadata-line cases

## Question

Are metadata values parsed only from their own line?

## Hypothesis

Line-bounded parsing rejects blank and exact placeholder values.

## Baseline

Use the prior newline-matching metadata expression.

## Protocol

Apply one deterministic metadata mutation per case.

## Metrics

Classification accuracy, false accepts, and blank-value spill captures.

## Acceptance and stop criteria

Accept at 16/16 correct with zero false accepts and zero candidate spills.

## Results

Execution is reserved until the fixture is locked.

## Interpretation

This fixture tests structural parsing only.

## Limitations

No semantic-quality claim is made.

## Decision

`inconclusive`
"""


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    if set(fixture) != {"schema", "cases"} or fixture["schema"] != "strict-v1-metadata-line-v1":
        raise ValueError("fixture must declare only the metadata-line schema and cases")
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 16:
        raise ValueError("fixture must contain exactly sixteen cases")
    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "mutation", "expected"}:
            raise ValueError("each case must have id, mutation, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if case["mutation"] not in MUTATIONS or case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case contains an unsupported mutation or expected label")


def mutation_field(mutation: str) -> str | None:
    for field in FIELDS:
        if mutation.endswith(f"_{field.lower()}"):
            return field
    return None


def apply_mutation(mutation: str) -> str:
    if mutation == "none":
        return BASE_RECORD
    field = mutation_field(mutation)
    if mutation in BLANK_MUTATIONS and field is not None:
        replacement = "" if mutation.startswith("empty_") else "   "
    elif mutation in PLACEHOLDER_MUTATIONS:
        field = "Data"
        replacement = {
            "template_data": "synthetic/public/other-safe-description",
            "tbd_data": "TBD.",
            "todo_data": "TODO",
            "pending_data": "`pending`",
            "na_data": "N/A",
        }[mutation]
    else:
        raise ValueError(f"unsupported mutation: {mutation}")
    old = f"- **{field}**: {BASE_VALUES[field]}"
    return BASE_RECORD.replace(old, f"- **{field}**: {replacement}", 1)


def _blank_spill(text: str, mutation: str, metadata_re) -> bool:
    if mutation not in BLANK_MUTATIONS:
        return False
    field = mutation_field(mutation)
    values = metadata_values(text, metadata_re).get(field or "", [])
    return len(values) != 1 or bool(values[0])


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str | bool]]:
    results: list[dict[str, str | bool]] = []
    for case in fixture["cases"]:
        mutation = case["mutation"]
        text = apply_mutation(mutation)
        baseline_errors = validate_record(
            text,
            FILENAME,
            metadata_re=LEGACY_METADATA_RE,
            placeholder_metadata_values={},
        )
        candidate_errors = validate_record(text, FILENAME)
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": "invalid" if baseline_errors else "valid",
                "candidate": "invalid" if candidate_errors else "valid",
                "baseline_blank_spill": _blank_spill(text, mutation, LEGACY_METADATA_RE),
                "candidate_blank_spill": _blank_spill(text, mutation, METADATA_RE),
            }
        )
    return results


def summarize(results: list[dict[str, str | bool]]) -> dict[str, int]:
    invalid_cases = [result for result in results if result["expected"] == "invalid"]
    return {
        "case_count": len(results),
        "candidate_correct": sum(result["candidate"] == result["expected"] for result in results),
        "candidate_false_accepts": sum(result["candidate"] == "valid" for result in invalid_cases),
        "baseline_false_accepts": sum(result["baseline"] == "valid" for result in invalid_cases),
        "candidate_blank_spills": sum(bool(result["candidate_blank_spill"]) for result in results),
        "baseline_blank_spills": sum(bool(result["baseline_blank_spill"]) for result in results),
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
        summary["case_count"] == 16
        and summary["candidate_correct"] == summary["case_count"]
        and summary["candidate_false_accepts"] == 0
        and summary["baseline_false_accepts"] >= 7
        and summary["candidate_blank_spills"] == 0
        and summary["baseline_blank_spills"] >= 10
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
