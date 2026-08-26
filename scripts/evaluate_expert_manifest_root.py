#!/usr/bin/env python3
"""Evaluate an opt-in rooted expert-manifest contract without promoting it."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_hierarchical_scope_routing import _scope_segments  # noqa: E402
from scripts.evaluate_wildcard_scope_routing import _pattern_segments  # noqa: E402
from scripts.validate_expert_manifest import (  # noqa: E402
    SCHEMA as V1_SCHEMA,
    TOP_LEVEL_KEYS,
    validate_manifest,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_manifest_root_cases.json"
V2_SCHEMA = "expert-package-v2"
V2_KEYS = TOP_LEVEL_KEYS | {"root"}
EXPECTED_LABELS = {"valid", "invalid"}
LOCKED_HISTORICAL_SOURCES = {
    ("public-template", "templates/expert-package.json", ()),
    (
        "manifest-contract-base",
        "fixtures/expert_manifest_cases.json",
        ("base_manifest",),
    ),
    (
        "expiry-contract-base",
        "fixtures/expert_expiry_cases.json",
        ("base_manifest",),
    ),
    (
        "layer-identity-base",
        "fixtures/expert_layer_identity_cases.json",
        ("base_manifest",),
    ),
}


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    required = {"schema", "base_manifest", "cases", "historical_v1_sources"}
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-manifest-root-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    if not isinstance(fixture["base_manifest"], dict):
        raise ValueError("base_manifest must be an object")
    if fixture["base_manifest"].get("schema") != V2_SCHEMA:
        raise ValueError("base_manifest must opt in to expert-package-v2")

    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 10:
        raise ValueError("fixture must contain exactly ten cases")
    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "mutation",
            "expected",
            "expected_candidate_error",
        }:
            raise ValueError("case has unexpected structure")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
            raise ValueError("case ids must be non-empty and unique")
        seen_ids.add(case_id)
        if case["expected"] not in EXPECTED_LABELS:
            raise ValueError("case has an invalid expected label")
        expected_error = case["expected_candidate_error"]
        if case["expected"] == "valid" and expected_error is not None:
            raise ValueError("valid cases cannot declare a candidate error")
        if case["expected"] == "invalid" and (
            not isinstance(expected_error, str) or not expected_error
        ):
            raise ValueError("invalid cases must declare a candidate error")
        mutation = case["mutation"]
        if not isinstance(mutation, dict) or mutation.get("op") not in {
            "none",
            "set",
            "remove",
        }:
            raise ValueError("case has an invalid mutation")
        if mutation["op"] == "none" and set(mutation) != {"op"}:
            raise ValueError("none mutation must contain only op")
        if mutation["op"] == "remove" and set(mutation) != {"op", "path"}:
            raise ValueError("remove mutation must contain op and path")
        if mutation["op"] == "set" and set(mutation) != {"op", "path", "value"}:
            raise ValueError("set mutation must contain op, path, and value")
        if mutation["op"] != "none" and (
            not isinstance(mutation["path"], list)
            or not mutation["path"]
            or not all(isinstance(part, str) and part for part in mutation["path"])
        ):
            raise ValueError("mutation path must be a non-empty string list")

    historical = fixture["historical_v1_sources"]
    if not isinstance(historical, list) or len(historical) != 4:
        raise ValueError("fixture must lock exactly four historical v1 sources")
    declared_sources: set[tuple[str, str, tuple[str, ...]]] = set()
    for source in historical:
        if not isinstance(source, dict) or set(source) != {"id", "path", "selector"}:
            raise ValueError("historical source has unexpected structure")
        if not isinstance(source["selector"], list) or not all(
            isinstance(part, str) and part for part in source["selector"]
        ):
            raise ValueError("historical selector must be a string list")
        declared_sources.add((source["id"], source["path"], tuple(source["selector"])))
    if declared_sources != LOCKED_HISTORICAL_SOURCES:
        raise ValueError("historical v1 sources do not match the locked set")


def build_manifest(base: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    manifest = deepcopy(base)
    if mutation["op"] == "none":
        return manifest
    target = manifest
    for part in mutation["path"][:-1]:
        if not isinstance(target.get(part), dict):
            raise ValueError("mutation path does not resolve to an object")
        target = target[part]
    leaf = mutation["path"][-1]
    if mutation["op"] == "set":
        target[leaf] = deepcopy(mutation["value"])
    else:
        if leaf not in target:
            raise ValueError("remove mutation path does not exist")
        del target[leaf]
    return manifest


def _v1_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    projected = deepcopy(manifest)
    projected.pop("root", None)
    projected["schema"] = V1_SCHEMA
    return projected


def baseline_errors(manifest: Any) -> list[str]:
    """Presence-only root baseline with unchanged v1 validation beneath it."""
    if not isinstance(manifest, dict):
        return ["manifest-not-object"]
    if manifest.get("schema") == V1_SCHEMA:
        return validate_manifest(manifest)
    if manifest.get("schema") != V2_SCHEMA:
        return ["unsupported-schema"]
    errors: list[str] = []
    keys = set(manifest)
    for key in sorted(V2_KEYS - keys):
        errors.append(f"missing-key:{key}")
    for key in sorted(keys - V2_KEYS):
        errors.append(f"unexpected-key:{key}")
    if errors:
        return errors
    errors.extend(validate_manifest(_v1_projection(manifest)))
    root = manifest["root"]
    if not isinstance(root, str) or not root:
        errors.append("invalid-root")
    return errors


def candidate_errors(manifest: Any) -> list[str]:
    """Validate v1 unchanged or the quarantined, opt-in rooted v2 contract."""
    if not isinstance(manifest, dict):
        return ["manifest-not-object"]
    if manifest.get("schema") == V1_SCHEMA:
        return validate_manifest(manifest)
    if manifest.get("schema") != V2_SCHEMA:
        return ["unsupported-schema"]

    errors: list[str] = []
    keys = set(manifest)
    for key in sorted(V2_KEYS - keys):
        errors.append(f"missing-key:{key}")
    for key in sorted(keys - V2_KEYS):
        errors.append(f"unexpected-key:{key}")
    if errors:
        return errors

    errors.extend(validate_manifest(_v1_projection(manifest)))
    if errors:
        return errors

    root = manifest["root"]
    try:
        root_segments = _scope_segments(root)
    except ValueError:
        return ["invalid-root"]
    if len(root_segments) != 1 or "*" in root_segments[0]:
        return ["invalid-root"]

    for name in ("include", "exclude"):
        for pattern in manifest["scope"][name]:
            try:
                pattern_segments = _pattern_segments(pattern)
            except ValueError:
                errors.append(f"invalid-scope-pattern:{name}:{pattern}")
                continue
            if pattern_segments[0] not in {"*", root}:
                errors.append(f"scope-root-mismatch:{name}:{pattern}")
    return errors


def _load_historical_manifest(source: dict[str, Any]) -> Any:
    data: Any = json.loads((ROOT / source["path"]).read_text(encoding="utf-8"))
    for part in source["selector"]:
        if not isinstance(data, dict) or part not in data:
            raise ValueError(f"historical selector does not resolve:{source['id']}")
        data = data[part]
    return data


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    case_runs: list[dict[str, Any]] = []
    for case in fixture["cases"]:
        manifest = build_manifest(fixture["base_manifest"], case["mutation"])
        baseline = baseline_errors(manifest)
        candidate = candidate_errors(manifest)
        case_runs.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "expected_candidate_error": case["expected_candidate_error"],
                "baseline_errors": baseline,
                "candidate_errors": candidate,
            }
        )

    historical_runs: list[dict[str, Any]] = []
    for source in fixture["historical_v1_sources"]:
        manifest = _load_historical_manifest(source)
        legacy = validate_manifest(manifest)
        historical_runs.append(
            {
                "id": source["id"],
                "legacy_errors": legacy,
                "candidate_errors": candidate_errors(manifest),
            }
        )
    return {"case_runs": case_runs, "historical_runs": historical_runs}


def summarize(trial: dict[str, Any]) -> dict[str, Any]:
    cases = trial["case_runs"]
    invalid = [case for case in cases if case["expected"] == "invalid"]
    historical = trial["historical_runs"]
    return {
        "case_count": len(cases),
        "baseline_correct": sum(
            (not case["baseline_errors"]) == (case["expected"] == "valid")
            for case in cases
        ),
        "baseline_false_accepts": sum(not case["baseline_errors"] for case in invalid),
        "candidate_correct": sum(
            (not case["candidate_errors"]) == (case["expected"] == "valid")
            for case in cases
        ),
        "candidate_false_accepts": sum(not case["candidate_errors"] for case in invalid),
        "candidate_expected_errors": sum(
            case["expected_candidate_error"] is None
            and not case["candidate_errors"]
            or case["expected_candidate_error"] in case["candidate_errors"]
            for case in cases
        ),
        "historical_v1_count": len(historical),
        "historical_v1_accepted": sum(not run["candidate_errors"] for run in historical),
        "historical_v1_exact_matches": sum(
            run["legacy_errors"] == run["candidate_errors"] for run in historical
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first = run_trial(fixture)
    second = run_trial(fixture)
    elapsed_seconds = perf_counter() - started

    summary = summarize(first)
    summary.update(
        {
            "repeatable": first == second,
            "fixture_bytes": args.fixture.stat().st_size,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["case_count"] == 10
        and summary["baseline_correct"] == 4
        and summary["baseline_false_accepts"] == 6
        and summary["candidate_correct"] == 10
        and summary["candidate_false_accepts"] == 0
        and summary["candidate_expected_errors"] == 10
        and summary["historical_v1_count"] == 4
        and summary["historical_v1_accepted"] == 4
        and summary["historical_v1_exact_matches"] == 4
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
