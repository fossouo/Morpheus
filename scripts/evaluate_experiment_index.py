#!/usr/bin/env python3
"""Evaluate experiment-index consistency against a count-only baseline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_index import consistency_findings  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "experiment_index_cases.json"
EXPECTED_LABELS = {"valid", "invalid"}
MUTATIONS = {
    "none",
    "missing_index_entry",
    "duplicate_index_id",
    "orphan_replacement",
    "status_mismatch",
    "verdict_mismatch",
    "invalid_status",
    "missing_record",
}
INDEX_ROW_RE = re.compile(r"^\|\s*EXP-\d{3}\s*\|", re.MULTILINE)

BASE_INDEX = """# Synthetic experiment index

| ID | Title | Status | Verdict |
|---|---|---|---|
| EXP-900 | Alpha | complete | pass |
| EXP-901 | Beta | planned | inconclusive |
| EXP-902 | Gamma | complete | fail |

Status and verdict values follow the repository contract.
"""


def _record(experiment_id: str, status: str, decision: str) -> str:
    return f"""# {experiment_id} — Synthetic record

- **Status**: {status}

## Decision

`{decision}`
"""


BASE_RECORDS = {
    "EXP-900-alpha.md": _record("EXP-900", "complete", "pass"),
    "EXP-901-beta.md": _record("EXP-901", "planned", "inconclusive"),
    "EXP-902-gamma.md": _record("EXP-902", "complete", "fail"),
}


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    if set(fixture) != {"schema", "cases"} or fixture["schema"] != "experiment-index-v1":
        raise ValueError("fixture must declare only the experiment-index schema and cases")
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


def apply_mutation(mutation: str) -> tuple[str, dict[str, str]]:
    index_text = BASE_INDEX
    records = dict(BASE_RECORDS)
    gamma_row = "| EXP-902 | Gamma | complete | fail |"
    if mutation == "none":
        pass
    elif mutation == "missing_index_entry":
        index_text = index_text.replace(f"{gamma_row}\n", "", 1)
    elif mutation == "duplicate_index_id":
        index_text = index_text.replace(gamma_row, "| EXP-901 | Gamma | complete | fail |", 1)
    elif mutation == "orphan_replacement":
        index_text = index_text.replace(gamma_row, "| EXP-999 | Gamma | complete | fail |", 1)
    elif mutation == "status_mismatch":
        index_text = index_text.replace(
            "| EXP-901 | Beta | planned | inconclusive |",
            "| EXP-901 | Beta | complete | inconclusive |",
            1,
        )
    elif mutation == "verdict_mismatch":
        index_text = index_text.replace(gamma_row, "| EXP-902 | Gamma | complete | pass |", 1)
    elif mutation == "invalid_status":
        index_text = index_text.replace(
            "| EXP-901 | Beta | planned | inconclusive |",
            "| EXP-901 | Beta | pending | inconclusive |",
            1,
        )
    elif mutation == "missing_record":
        records.pop("EXP-902-gamma.md")
    else:
        raise ValueError(f"unsupported mutation: {mutation}")
    return index_text, records


def _count_only_baseline(index_text: str, records: dict[str, str]) -> str:
    return "valid" if len(INDEX_ROW_RE.findall(index_text)) == len(records) else "invalid"


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for case in fixture["cases"]:
        index_text, records = apply_mutation(case["mutation"])
        findings = consistency_findings(index_text, records)
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "baseline": _count_only_baseline(index_text, records),
                "candidate": "invalid" if findings else "valid",
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
