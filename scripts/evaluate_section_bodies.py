#!/usr/bin/env python3
"""Evaluate content-aware section validation against a presence-only baseline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_records import (  # noqa: E402
    REQUIRED_SECTIONS,
    SECTION_RE,
    validate_record,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "section_body_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}
MUTATIONS = {
    "none",
    "empty_question",
    "whitespace_hypothesis",
    "tbd_baseline",
    "todo_protocol",
    "pending_metrics",
    "template_question",
    "template_hypothesis",
    "template_acceptance",
}
FILENAME = "EXP-901-synthetic-section-body-record.md"

BASE_RECORD = """# EXP-901 — Synthetic section-body record

- **Schema**: strict-v1
- **Date**: 2026-08-02
- **Status**: running
- **Compute**: C0
- **Data**: synthetic

## Question

Does every required section contain declared content?

## Hypothesis

Known empty and placeholder bodies will be rejected.

## Baseline

Require every section heading exactly once.

## Protocol

Apply one deterministic mutation per case.

## Metrics

Classification accuracy and false accepts.

## Acceptance and stop criteria

Accept at 9/9 correct with zero false accepts; stop after nine cases.

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
    if set(fixture) != {"schema", "cases"} or fixture["schema"] != "strict-v1-section-body-v1":
        raise ValueError("fixture must declare only the section-body schema and cases")
    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 9:
        raise ValueError("fixture must contain exactly nine cases")
    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "mutation", "expected"}:
            raise ValueError("each case must have id, mutation, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if case["mutation"] not in MUTATIONS or case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case contains an unsupported mutation or expected label")


def _replace_body(text: str, section: str, body: str) -> str:
    marker = f"## {section}\n"
    start = text.index(marker) + len(marker)
    next_start = text.find("\n## ", start)
    end = len(text) if next_start == -1 else next_start
    return text[:start] + f"\n{body}\n" + text[end:]


def apply_mutation(mutation: str) -> str:
    replacements = {
        "empty_question": ("Question", ""),
        "whitespace_hypothesis": ("Hypothesis", "   \n\t"),
        "tbd_baseline": ("Baseline", "TBD."),
        "todo_protocol": ("Protocol", "TODO"),
        "pending_metrics": ("Metrics", "`pending`"),
        "template_question": ("Question", "What specific question is being tested?"),
        "template_hypothesis": ("Hypothesis", "State a claim that can be rejected."),
        "template_acceptance": (
            "Acceptance and stop criteria",
            "Declare both success and failure thresholds.",
        ),
    }
    if mutation == "none":
        return BASE_RECORD
    section, body = replacements[mutation]
    return _replace_body(BASE_RECORD, section, body)


def presence_only_valid(text: str) -> bool:
    counts = Counter(match.group("name") for match in SECTION_RE.finditer(text))
    return all(counts[section] == 1 for section in REQUIRED_SECTIONS)


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for case in fixture["cases"]:
        text = apply_mutation(case["mutation"])
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": "valid" if presence_only_valid(text) else "invalid",
                "candidate": "invalid" if validate_record(text, FILENAME) else "valid",
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
        summary["case_count"] == 9
        and summary["candidate_correct"] == summary["case_count"]
        and summary["candidate_false_accepts"] == 0
        and summary["baseline_false_accepts"] >= 7
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
