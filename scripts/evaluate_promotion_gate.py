#!/usr/bin/env python3
"""Evaluate a deterministic target-gain and held-out-regression promotion gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "fixtures" / "promotion_gate_cases.json"
DECISIONS = {"promote", "quarantine"}


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    required_top_level = {"score_scale", "thresholds", "cases"}
    if set(fixture) != required_top_level:
        raise ValueError("fixture must contain score_scale, thresholds, and cases")

    scale = fixture["score_scale"]
    if not isinstance(scale, int) or isinstance(scale, bool) or scale <= 0:
        raise ValueError("score_scale must be a positive integer")

    thresholds = fixture["thresholds"]
    if set(thresholds) != {"min_target_gain", "max_control_drop"}:
        raise ValueError("thresholds must define target gain and control drop")
    for value in thresholds.values():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("thresholds must be non-negative integers")

    cases = fixture["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a non-empty list")

    seen_ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "baseline", "candidate", "expected"}:
            raise ValueError("each case must have id, baseline, candidate, and expected")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case["id"])
        if case["expected"] not in DECISIONS:
            raise ValueError("expected must be promote or quarantine")
        for snapshot_name in ("baseline", "candidate"):
            snapshot = case[snapshot_name]
            if set(snapshot) != {"target", "control"}:
                raise ValueError("snapshots must contain target and control")
            for score in snapshot.values():
                if (
                    not isinstance(score, int)
                    or isinstance(score, bool)
                    or not 0 <= score <= scale
                ):
                    raise ValueError("scores must be integers within score_scale")


def target_only_decision(case: dict[str, Any], min_target_gain: int) -> str:
    target_gain = case["candidate"]["target"] - case["baseline"]["target"]
    return "promote" if target_gain >= min_target_gain else "quarantine"


def guarded_decision(
    case: dict[str, Any],
    min_target_gain: int,
    max_control_drop: int,
) -> str:
    target_gain = case["candidate"]["target"] - case["baseline"]["target"]
    control_drop = case["baseline"]["control"] - case["candidate"]["control"]
    if target_gain >= min_target_gain and control_drop <= max_control_drop:
        return "promote"
    return "quarantine"


def evaluate_fixture(fixture: dict[str, Any]) -> list[dict[str, str]]:
    thresholds = fixture["thresholds"]
    return [
        {
            "id": case["id"],
            "expected": case["expected"],
            "baseline": target_only_decision(case, thresholds["min_target_gain"]),
            "guarded": guarded_decision(
                case,
                thresholds["min_target_gain"],
                thresholds["max_control_drop"],
            ),
        }
        for case in fixture["cases"]
    ]


def summarize(results: list[dict[str, str]]) -> dict[str, int]:
    rejected = [result for result in results if result["expected"] == "quarantine"]
    return {
        "case_count": len(results),
        "guarded_correct": sum(
            result["guarded"] == result["expected"] for result in results
        ),
        "guarded_false_promotions": sum(
            result["guarded"] == "promote" for result in rejected
        ),
        "baseline_false_promotions": sum(
            result["baseline"] == "promote" for result in rejected
        ),
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
    accepted = (
        summary["case_count"] == 5
        and summary["guarded_correct"] == summary["case_count"]
        and summary["guarded_false_promotions"] == 0
        and summary["baseline_false_promotions"] >= 1
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
    )
    summary["accepted"] = accepted
    print(json.dumps(summary, sort_keys=True))
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
