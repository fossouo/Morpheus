#!/usr/bin/env python3
"""Diagnose an exposed exclusion expectation without changing routing behavior."""

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
    migrate_template,
    project_to_source_v1,
)
from scripts.evaluate_public_template_v2_migration_replay import (  # noqa: E402
    _read_pinned_source,
    load_fixture as load_replay_fixture,
    repaired_packages,
    run_trial,
)

DEFAULT_FIXTURE = ROOT / "fixtures/expert_template_disjoint_exclusion_cases.json"
SOURCE_PATH = "fixtures/expert_public_template_v2_migration_replay_cases.json"
OLD_EXPECTED = "route-error:scope-excluded"
NEW_EXPECTED = "route-error:scope-not-found"


def load_inputs(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if (
        set(fixture) != {"schema", "source_fixture", "expected_change"}
        or fixture["schema"] != "expert-template-disjoint-exclusion-cases-v1"
        or fixture["expected_change"] != {"from": OLD_EXPECTED, "to": NEW_EXPECTED}
    ):
        raise ValueError("unsupported diagnostic fixture")
    source = fixture["source_fixture"]
    if set(source) != {"path", "sha256"} or source["path"] != SOURCE_PATH:
        raise ValueError("diagnostic must pin EXP-033")
    replay_path = ROOT / SOURCE_PATH
    replay_bytes = replay_path.read_bytes()
    if hashlib.sha256(replay_bytes).hexdigest() != source["sha256"]:
        raise ValueError("EXP-033 fixture hash mismatch")
    replay = load_replay_fixture(replay_path)
    original, source_bytes = _read_pinned_source(replay["source_fixture"])
    size = len(payload) + len(replay_bytes) + len(source_bytes)
    size += (ROOT / original["template"]["path"]).stat().st_size
    return original, size


def corrected_fixture(source: dict[str, Any]) -> dict[str, Any]:
    if source["exclusion"]["expected"] != OLD_EXPECTED:
        raise ValueError("historical exclusion expectation changed")
    corrected = copy.deepcopy(source)
    corrected["exclusion"]["expected"] = NEW_EXPECTED
    return corrected


def literal_prefix_match(pattern: str, scope: str) -> bool:
    """Independent literal-only oracle; do not reuse the router's matcher."""
    prefix, request = pattern.split("/"), scope.split("/")
    if any(segment in {"", "*", ".", ".."} for segment in prefix + request):
        raise ValueError("probe requires nonempty literal segments")
    return request[:len(prefix)] == prefix


def exclusion_scores(trial: dict[str, Any], expected: str) -> dict[str, int]:
    runs = trial["order_runs"]
    return {
        "response_equal": sum(
            run["baseline_exclusion"] == run["stable_exclusion"] for run in runs
        ),
        "baseline_correct": sum(run["baseline_exclusion"] == expected for run in runs),
        "candidate_correct": sum(run["stable_exclusion"] == expected for run in runs),
    }


def evaluate(source: dict[str, Any]) -> dict[str, Any]:
    template = json.loads((ROOT / source["template"]["path"]).read_text())
    migrated = migrate_template(template, source["root"])
    packages = repaired_packages(migrated)
    scope = source["exclusion"]["request"]["scope"]
    matches = {
        name: sum(
            literal_prefix_match(pattern, scope)
            for package in packages
            for pattern in package["manifest"]["scope"][name]
        )
        for name in ("include", "exclude")
    }
    historical = run_trial(source)
    corrected = corrected_fixture(source)
    restored = copy.deepcopy(corrected)
    restored["exclusion"]["expected"] = OLD_EXPECTED
    first = run_trial(corrected)
    repeated = run_trial(corrected)
    projected = project_to_source_v1(migrated)
    runs = first["order_runs"]
    targets = [case["expected"] for case in source["targets"]]
    return {
        "historical": exclusion_scores(historical, OLD_EXPECTED),
        "corrected": exclusion_scores(first, NEW_EXPECTED),
        "literal_matches": matches,
        "expectation_only_change": restored == source,
        "complete_outputs_unchanged": historical == first == repeated,
        "baseline_valid": first["baseline_errors"] == [],
        "candidate_valid": first["candidate_errors"] == [],
        "candidate_expired_next_day": first["expired_errors"] == ["expired"],
        "projection_exact": projected == template,
        "scope_lists_preserved": projected["scope"] == template["scope"],
        "target_correct_pairs": sum(
            baseline == candidate == expected
            for run in runs
            for baseline, candidate, expected in zip(
                run["baseline_targets"], run["stable_targets"], targets
            )
        ),
        "regression_correct_pairs": sum(
            run["baseline_regression"] == run["stable_regression"]
            == source["regression"]["expected"] for run in runs
        ),
        "rollback_matches": sum(
            actual == source["unloaded_expected"] for run in runs for actual in run["unloaded"]
        ),
        "order_count": len(runs),
        "order_invariant": all(run == runs[0] for run in runs),
        "repeatable": first == repeated,
    }


def accepted(summary: dict[str, Any]) -> bool:
    return (
        summary["historical"] == {
            "response_equal": 2, "baseline_correct": 0, "candidate_correct": 0,
        }
        and summary["corrected"] == {
            "response_equal": 2, "baseline_correct": 2, "candidate_correct": 2,
        }
        and summary["literal_matches"] == {"include": 0, "exclude": 1}
        and all(summary[key] for key in (
            "expectation_only_change", "complete_outputs_unchanged", "baseline_valid",
            "candidate_valid", "candidate_expired_next_day", "projection_exact",
            "scope_lists_preserved", "order_invariant", "repeatable",
        ))
        and summary["target_correct_pairs"] == 4
        and summary["regression_correct_pairs"] == 2
        and summary["rollback_matches"] == 4
        and summary["order_count"] == 2
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    source, fixture_bytes = load_inputs(args.fixture)
    summary = evaluate(source)
    summary.update({
        "fixture_bytes": fixture_bytes,
        "evaluation_seconds": perf_counter() - started,
        "external_calls": 0,
    })
    summary["accepted"] = accepted(summary)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
