#!/usr/bin/env python3
"""Evaluate index-to-record title consistency against the EXP-007 baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_index import consistency_findings  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "experiment_title_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    if set(fixture) != {"schema", "cases"} or fixture["schema"] != "experiment-title-v1":
        raise ValueError("fixture must declare only the experiment-title schema and cases")
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 7:
        raise ValueError("fixture must contain exactly seven cases")
    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "index_title", "heading", "expected"}:
            raise ValueError("each case must have id, index_title, heading, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if not isinstance(case["index_title"], str) or not case["index_title"]:
            raise ValueError("index titles must be non-empty strings")
        if not isinstance(case["heading"], str) or case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case contains an invalid heading or expected label")


def build_case(case: dict[str, str]) -> tuple[str, dict[str, str]]:
    index_text = f"""# Synthetic experiment index

| ID | Title | Status | Verdict |
|---|---|---|---|
| EXP-900 | {case['index_title']} | complete | pass |
"""
    record = f"""{case['heading']}

- **Status**: complete

## Decision

`pass`
"""
    return index_text, {"EXP-900-title-consistency.md": record}


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for case in fixture["cases"]:
        index_text, records = build_case(case)
        baseline_findings = consistency_findings(index_text, records, check_titles=False)
        candidate_findings = consistency_findings(index_text, records)
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": "invalid" if baseline_findings else "valid",
                "candidate": "invalid" if candidate_findings else "valid",
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
        and summary["baseline_false_accepts"] >= 5
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
