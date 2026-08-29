#!/usr/bin/env python3
"""Separate structural compatibility from pinned-date manifest lifecycle state."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_manifest_temporal_corpus_cases.json"
LOCKED_SOURCE_IDS = {
    "public-template",
    "manifest-contract-base",
    "expiry-contract-base",
    "layer-identity-base",
}
LOCKED_CASE_IDS = {"before-expiry", "on-expiry", "after-expiry", "promotion-date"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a canonical calendar date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a canonical calendar date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be a canonical calendar date")
    return parsed


def _expected_lifecycle_errors(expiry: date, reference: date) -> list[str]:
    return ["expired"] if reference > expiry else []


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Any) -> None:
    if not isinstance(fixture, dict) or set(fixture) != {
        "schema",
        "promotion_reference_date",
        "sources",
    }:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-manifest-temporal-corpus-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    promotion_date = _canonical_date(
        fixture["promotion_reference_date"], "promotion_reference_date"
    )
    sources = fixture["sources"]
    if not isinstance(sources, list) or len(sources) != 4:
        raise ValueError("fixture must contain exactly four sources")
    if {source.get("id") for source in sources if isinstance(source, dict)} != LOCKED_SOURCE_IDS:
        raise ValueError("fixture must contain the four locked source ids")

    for source in sources:
        if set(source) != {
            "id",
            "path",
            "sha256",
            "selector",
            "expected_expires_on",
            "expected_structural_errors",
            "lifecycle_cases",
        }:
            raise ValueError("source has unexpected structure")
        if (
            not isinstance(source["path"], str)
            or not source["path"].startswith(("fixtures/", "templates/"))
            or not SHA256_RE.fullmatch(source["sha256"])
            or not isinstance(source["selector"], list)
            or not all(isinstance(key, str) and key for key in source["selector"])
        ):
            raise ValueError("source path, hash, or selector is invalid")
        if source["expected_structural_errors"] != []:
            raise ValueError("locked sources must be structurally valid")
        expiry = _canonical_date(source["expected_expires_on"], "expected_expires_on")
        cases = source["lifecycle_cases"]
        if not isinstance(cases, list) or len(cases) != 4:
            raise ValueError("each source must contain exactly four lifecycle cases")
        if {case.get("id") for case in cases if isinstance(case, dict)} != LOCKED_CASE_IDS:
            raise ValueError("source must contain the four locked lifecycle case ids")
        for case in cases:
            if set(case) != {"id", "reference_date", "expected_errors"}:
                raise ValueError("lifecycle case has unexpected structure")
            reference = _canonical_date(case["reference_date"], "reference_date")
            if case["expected_errors"] != _expected_lifecycle_errors(expiry, reference):
                raise ValueError("lifecycle expectation contradicts inclusive expiry policy")
            expected_reference = {
                "before-expiry": expiry - timedelta(days=1),
                "on-expiry": expiry,
                "after-expiry": expiry + timedelta(days=1),
                "promotion-date": promotion_date,
            }[case["id"]]
            if reference != expected_reference:
                raise ValueError("lifecycle case is not on its locked reference date")


def _load_source(source: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"source fixture hash mismatch:{source['path']}")
    value: Any = json.loads(payload)
    for key in source["selector"]:
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f"source selector mismatch:{source['id']}")
        value = value[key]
    if not isinstance(value, dict):
        raise ValueError(f"selected manifest is not an object:{source['id']}")
    return value


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    source_runs: list[dict[str, Any]] = []
    for source in fixture["sources"]:
        manifest = _load_source(source)
        structural_errors = validate_manifest(manifest)
        lifecycle_runs: list[dict[str, Any]] = []
        for case in source["lifecycle_cases"]:
            lifecycle_runs.append(
                {
                    "id": case["id"],
                    "reference_date": case["reference_date"],
                    "expected_errors": case["expected_errors"],
                    "baseline_errors": structural_errors,
                    "candidate_errors": validate_manifest(
                        manifest,
                        reference_date=date.fromisoformat(case["reference_date"]),
                    ),
                }
            )
        source_runs.append(
            {
                "id": source["id"],
                "expected_expires_on": source["expected_expires_on"],
                "observed_expires_on": manifest.get("expires_on"),
                "expected_structural_errors": source["expected_structural_errors"],
                "structural_errors": structural_errors,
                "lifecycle_runs": lifecycle_runs,
            }
        )
    return {"source_runs": source_runs}


def summarize(trial: dict[str, Any]) -> dict[str, int]:
    sources = trial["source_runs"]
    lifecycle = [run for source in sources for run in source["lifecycle_runs"]]
    expired = [run for run in lifecycle if run["expected_errors"] == ["expired"]]
    promotion = [run for run in lifecycle if run["id"] == "promotion-date"]
    return {
        "source_count": len(sources),
        "source_expiry_matches": sum(
            source["observed_expires_on"] == source["expected_expires_on"]
            for source in sources
        ),
        "structural_exact_matches": sum(
            source["structural_errors"] == source["expected_structural_errors"]
            for source in sources
        ),
        "structural_accepted": sum(not source["structural_errors"] for source in sources),
        "lifecycle_case_count": len(lifecycle),
        "baseline_lifecycle_correct": sum(
            run["baseline_errors"] == run["expected_errors"] for run in lifecycle
        ),
        "baseline_false_accepts": sum(not run["baseline_errors"] for run in expired),
        "candidate_lifecycle_exact_matches": sum(
            run["candidate_errors"] == run["expected_errors"] for run in lifecycle
        ),
        "candidate_false_accepts": sum(not run["candidate_errors"] for run in expired),
        "on_expiry_accepted": sum(
            not run["candidate_errors"] for run in lifecycle if run["id"] == "on-expiry"
        ),
        "after_expiry_rejected": sum(
            run["candidate_errors"] == ["expired"]
            for run in lifecycle
            if run["id"] == "after-expiry"
        ),
        "promotion_date_exact_matches": sum(
            run["candidate_errors"] == run["expected_errors"] for run in promotion
        ),
        "promotion_date_accepted": sum(not run["candidate_errors"] for run in promotion),
        "promotion_date_expired": sum(run["candidate_errors"] == ["expired"] for run in promotion),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    started = perf_counter()
    fixture = load_fixture(args.fixture)
    first = run_trial(fixture)
    repeated = run_trial(fixture)
    elapsed_seconds = perf_counter() - started
    summary: dict[str, Any] = summarize(first)
    summary.update(
        {
            "repeatable": first == repeated,
            "fixture_bytes": args.fixture.stat().st_size,
            "evaluation_seconds": round(elapsed_seconds, 6),
            "external_calls": 0,
        }
    )
    summary["accepted"] = (
        summary["source_count"]
        == summary["source_expiry_matches"]
        == summary["structural_exact_matches"]
        == summary["structural_accepted"]
        == 4
        and summary["lifecycle_case_count"] == 16
        and summary["baseline_lifecycle_correct"] == 11
        and summary["baseline_false_accepts"] == 5
        and summary["candidate_lifecycle_exact_matches"] == 16
        and summary["candidate_false_accepts"] == 0
        and summary["on_expiry_accepted"] == 4
        and summary["after_expiry_rejected"] == 4
        and summary["promotion_date_exact_matches"] == 4
        and summary["promotion_date_accepted"] == 3
        and summary["promotion_date_expired"] == 1
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
