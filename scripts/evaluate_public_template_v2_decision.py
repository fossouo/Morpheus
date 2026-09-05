#!/usr/bin/env python3
"""Decide whether the public v1 expert template is safe to replace in place."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_public_template_v2_migration import (  # noqa: E402
    migrate_template,
    project_to_source_v1,
)
from scripts.evaluate_template_disjoint_exclusion import (  # noqa: E402
    accepted as disjoint_accepted,
    evaluate as evaluate_disjoint,
    load_inputs as load_disjoint_inputs,
)
from scripts.evaluate_template_exclusion_reachability import (  # noqa: E402
    accepted as reachability_accepted,
    load_fixture as load_reachability_fixture,
    run_trial as run_reachability_trial,
    summarize as summarize_reachability,
)
from scripts.validate_expert_manifest import (  # noqa: E402
    SCHEMA,
    V2_SCHEMA,
    validate_manifest,
)


DEFAULT_FIXTURE = ROOT / "fixtures/expert_public_template_v2_decision_cases.json"
EXPECTED_EVIDENCE = {
    ("EXP-034", "fixtures/expert_template_disjoint_exclusion_cases.json"),
    ("EXP-035", "fixtures/expert_template_exclusion_reachability_cases.json"),
}
EXPECTED_DIRECT_PINS = {
    "fixtures/expert_manifest_temporal_corpus_cases.json",
    "fixtures/expert_public_template_v2_migration_cases.json",
    "fixtures/expert_template_exclusion_reachability_cases.json",
}


def _read_pinned(source: dict[str, Any], label: str) -> tuple[Path, bytes]:
    path = ROOT / source["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label} hash mismatch")
    return path, payload


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    required = {
        "schema", "reference_date", "expired_date", "root", "template",
        "evidence", "direct_template_pins", "expected_current_pin_count",
        "expected_candidate_preserved_pins",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-public-template-v2-decision-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    reference_date = date.fromisoformat(fixture["reference_date"])
    expired_date = date.fromisoformat(fixture["expired_date"])
    if (
        reference_date.isoformat() != fixture["reference_date"]
        or expired_date.isoformat() != fixture["expired_date"]
        or expired_date <= reference_date
    ):
        raise ValueError("fixture dates must be ordered canonical dates")
    if not isinstance(fixture["root"], str) or "/" in fixture["root"]:
        raise ValueError("root must be one literal segment")
    template = fixture["template"]
    if set(template) != {"path", "sha256"} or template["path"] != "templates/expert-package.json":
        raise ValueError("template pin is unsupported")
    _, template_payload = _read_pinned(template, "public template")
    evidence = fixture["evidence"]
    if not isinstance(evidence, list) or {
        (item.get("id"), item.get("path")) for item in evidence
    } != EXPECTED_EVIDENCE:
        raise ValueError("evidence set changed")
    evidence_bytes = 0
    for item in evidence:
        if set(item) != {"id", "path", "sha256"}:
            raise ValueError("evidence pin has unexpected structure")
        _, pinned_payload = _read_pinned(item, item["id"])
        evidence_bytes += len(pinned_payload)
    if set(fixture["direct_template_pins"]) != EXPECTED_DIRECT_PINS:
        raise ValueError("direct template pin set changed")
    if (
        fixture["expected_current_pin_count"] != 3
        or fixture["expected_candidate_preserved_pins"] != 0
    ):
        raise ValueError("locked pin expectations changed")
    return fixture, len(payload) + len(template_payload) + evidence_bytes


def _direct_pin_hash(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    if path.name == "expert_manifest_temporal_corpus_cases.json":
        public = [item for item in value["sources"] if item["id"] == "public-template"]
        if len(public) != 1:
            raise ValueError("temporal corpus public-template pin changed")
        source = public[0]
    else:
        source = value["template"]
    if source["path"] != "templates/expert-package.json":
        raise ValueError("direct pin no longer targets the public template")
    return source["sha256"]


def _candidate_payload(candidate: dict[str, Any]) -> bytes:
    return (json.dumps(candidate, indent=2) + "\n").encode("utf-8")


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    template_path = ROOT / fixture["template"]["path"]
    template = json.loads(template_path.read_text(encoding="utf-8"))
    reference_date = date.fromisoformat(fixture["reference_date"])
    expired_date = date.fromisoformat(fixture["expired_date"])
    candidate = migrate_template(template, fixture["root"])

    evidence_by_id = {item["id"]: ROOT / item["path"] for item in fixture["evidence"]}
    disjoint_source, disjoint_size = load_disjoint_inputs(evidence_by_id["EXP-034"])
    disjoint = evaluate_disjoint(disjoint_source)
    disjoint.update(fixture_bytes=disjoint_size, evaluation_seconds=0, external_calls=0)

    reach_fixture = load_reachability_fixture(evidence_by_id["EXP-035"])
    reach_first = run_reachability_trial(reach_fixture)
    reach_repeated = run_reachability_trial(reach_fixture)
    reachability = summarize_reachability(reach_fixture, reach_first)
    reachability.update(
        repeatable=reach_first == reach_repeated,
        fixture_bytes=1,
        evaluation_seconds=0,
        external_calls=0,
    )

    current_hash = hashlib.sha256(template_path.read_bytes()).hexdigest()
    candidate_hash = hashlib.sha256(_candidate_payload(candidate)).hexdigest()
    pin_hashes = [
        _direct_pin_hash(ROOT / relative)
        for relative in fixture["direct_template_pins"]
    ]
    current_pins = sum(pin == current_hash for pin in pin_hashes)
    candidate_pins = sum(pin == candidate_hash for pin in pin_hashes)
    functional_ready = all((
        template.get("schema") == SCHEMA,
        candidate.get("schema") == V2_SCHEMA,
        validate_manifest(template, reference_date=reference_date) == [],
        validate_manifest(candidate, reference_date=reference_date) == [],
        validate_manifest(candidate, reference_date=expired_date) == ["expired"],
        project_to_source_v1(candidate) == template,
        disjoint_accepted(disjoint),
        reachability_accepted(reachability),
    ))
    migration_ready = functional_ready and candidate_pins == len(pin_hashes)
    return {
        "baseline_valid": validate_manifest(template, reference_date=reference_date) == [],
        "candidate_valid": validate_manifest(candidate, reference_date=reference_date) == [],
        "candidate_expired_next_day": validate_manifest(candidate, reference_date=expired_date) == ["expired"],
        "projection_exact": project_to_source_v1(candidate) == template,
        "disjoint_evidence_passed": disjoint_accepted(disjoint),
        "reachability_evidence_passed": reachability_accepted(reachability),
        "disjoint_target_pairs": disjoint["target_correct_pairs"],
        "disjoint_regression_pairs": disjoint["regression_correct_pairs"],
        "disjoint_rollback": disjoint["rollback_matches"],
        "reachability_path_parity": reachability["pair_path_parity"],
        "reachability_path_correct": reachability["pair_path_correct"],
        "reachability_allowed": reachability["allowed_path_correct"],
        "reachability_absent": reachability["absent_path_correct"],
        "reachability_rollback": reachability["rollback_correct"],
        "current_direct_pins_valid": current_pins,
        "candidate_direct_pins_preserved": candidate_pins,
        "direct_pin_count": len(pin_hashes),
        "functional_ready": functional_ready,
        "migration_ready": migration_ready,
        "decision": "migrate-in-place" if migration_ready else "defer-for-immutable-v1-snapshot",
    }


def accepted(summary: dict[str, Any]) -> bool:
    return (
        all(summary[key] for key in (
            "baseline_valid", "candidate_valid", "candidate_expired_next_day",
            "projection_exact", "disjoint_evidence_passed",
            "reachability_evidence_passed", "functional_ready", "repeatable",
        ))
        and summary["disjoint_target_pairs"] == 4
        and summary["disjoint_regression_pairs"] == 2
        and summary["disjoint_rollback"] == 4
        and summary["reachability_path_parity"] == 4
        and summary["reachability_path_correct"] == 8
        and summary["reachability_allowed"] == 8
        and summary["reachability_absent"] == 8
        and summary["reachability_rollback"] == 8
        and summary["current_direct_pins_valid"] == summary["direct_pin_count"] == 3
        and summary["candidate_direct_pins_preserved"] == 0
        and not summary["migration_ready"]
        and summary["decision"] == "defer-for-immutable-v1-snapshot"
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture, fixture_bytes = load_fixture(args.fixture)
    first = run_trial(fixture)
    repeated = run_trial(fixture)
    summary = dict(first)
    summary.update({
        "repeatable": first == repeated,
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
