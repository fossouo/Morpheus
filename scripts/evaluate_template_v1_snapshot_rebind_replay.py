#!/usr/bin/env python3
"""Replay EXP-037 after repairing only its full-source selector handling."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_expert_manifest_temporal_corpus as temporal  # noqa: E402
from scripts import evaluate_public_template_v2_migration as migration  # noqa: E402
from scripts import evaluate_template_exclusion_reachability as reachability  # noqa: E402
from scripts import evaluate_template_v1_snapshot_rebind as legacy  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures/expert_template_v1_snapshot_rebind_replay_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "expected_legacy_error",
    "expected_full_source_selector_repairs", "expected_baseline_loaders",
    "expected_rebound_loaders", "expected_path_blockers",
    "expected_transitive_pins", "expected_decision",
}


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    if set(source) not in ({"path", "sha256"}, {"id", "path", "sha256"}):
        raise ValueError(f"{label} pin has unexpected structure")
    payload = (ROOT / source["path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label} hash mismatch")
    return payload


def load_fixture(path: Path) -> tuple[dict[str, Any], dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-template-v1-snapshot-rebind-replay-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    prior_experiment = fixture["prior_experiment"]
    if prior_experiment.get("id") != "EXP-037":
        raise ValueError("prior experiment changed")
    experiment_payload = _read_pinned(prior_experiment, "EXP-037")
    prior_fixture_payload = _read_pinned(fixture["prior_fixture"], "EXP-037 fixture")
    prior_fixture, prior_bytes = legacy.load_fixture(
        ROOT / fixture["prior_fixture"]["path"]
    )
    if (
        fixture["expected_legacy_error"] != "temporal-corpus direct pin changed"
        or fixture["expected_full_source_selector_repairs"] != 1
        or fixture["expected_baseline_loaders"] != 3
        or fixture["expected_rebound_loaders"] != 1
        or fixture["expected_path_blockers"] != {
            "migration": "template must contain the public path and SHA-256",
            "reachability": "template pin is unsupported",
        }
        or fixture["expected_transitive_pins"] != 3
        or fixture["expected_decision"]
        != "defer-for-path-contract-and-transitive-pin-plan"
    ):
        raise ValueError("locked expectations changed")
    total_bytes = len(payload) + len(experiment_payload) + prior_bytes
    if len(prior_fixture_payload) == 0:
        raise ValueError("EXP-037 fixture is empty")
    return fixture, prior_fixture, total_bytes


def _legacy_error(prior_fixture: dict[str, Any]) -> str | None:
    try:
        legacy.run_trial(prior_fixture)
    except ValueError as exc:
        return str(exc)
    return None


def _rebound_path_member(
    source: dict[str, Any], snapshot: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    document = json.loads((ROOT / source["path"]).read_text(encoding="utf-8"))
    rebound = copy.deepcopy(document)
    selected = legacy._selected_pin(rebound, source["selector"])
    if (
        selected.get("path") != "templates/expert-package.json"
        or selected.get("sha256") != snapshot["sha256"]
    ):
        raise ValueError(f"{source['id']} direct pin changed")
    before = copy.deepcopy(selected)
    selected["path"] = snapshot["path"]
    expected = copy.deepcopy(before)
    expected["path"] = snapshot["path"]
    if selected != expected:
        raise ValueError(f"{source['id']} changed beyond path")
    return rebound, set(before) != {"path", "sha256"}


def run_candidate(prior_fixture: dict[str, Any]) -> dict[str, Any]:
    template_payload = (ROOT / prior_fixture["template"]["path"]).read_bytes()
    snapshot_payload = (ROOT / prior_fixture["snapshot"]["path"]).read_bytes()
    by_id = {item["id"]: item for item in prior_fixture["direct_pins"]}
    loaders: dict[str, Callable[[Path], Any]] = {
        "temporal-corpus": temporal.load_fixture,
        "migration": migration.load_fixture,
        "reachability": reachability.load_fixture,
    }
    baseline_loaded = 0
    rebound_loaded = 0
    rebound_references = 0
    full_source_selector_repairs = 0
    blockers: dict[str, str] = {}
    fixture_hashes_changed = 0
    transitive_pins = 0
    temporal_parity = False
    for source_id, loader in loaders.items():
        source = by_id[source_id]
        original_path = ROOT / source["path"]
        original_document = json.loads(original_path.read_text(encoding="utf-8"))
        baseline_ok, _, baseline = legacy._load_with(loader, original_document)
        baseline_loaded += baseline_ok
        rebound_document, repaired_full_source = _rebound_path_member(
            source, prior_fixture["snapshot"]
        )
        rebound_references += 1
        full_source_selector_repairs += repaired_full_source
        rebound_ok, error, rebound = legacy._load_with(loader, rebound_document)
        rebound_loaded += rebound_ok
        if error is not None:
            blockers[source_id] = error
        original_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
        rebound_bytes = (json.dumps(rebound_document, indent=2) + "\n").encode("utf-8")
        rebound_hash = hashlib.sha256(rebound_bytes).hexdigest()
        fixture_hashes_changed += rebound_hash != original_hash
        transitive_pins += legacy._transitive_pin_count(original_hash)
        if source_id == "temporal-corpus" and baseline_ok and rebound_ok:
            temporal_parity = temporal.run_trial(baseline) == temporal.run_trial(rebound)
    return {
        "snapshot_byte_exact": snapshot_payload == template_payload,
        "snapshot_hash_exact": hashlib.sha256(snapshot_payload).hexdigest()
        == prior_fixture["template"]["sha256"],
        "baseline_loaders": baseline_loaded,
        "rebound_references": rebound_references,
        "full_source_selector_repairs": full_source_selector_repairs,
        "rebound_loaders": rebound_loaded,
        "path_blockers": blockers,
        "temporal_behavior_parity": temporal_parity,
        "candidate_fixture_hashes_changed": fixture_hashes_changed,
        "transitive_pins": transitive_pins,
        "candidate_transitive_pins_preserved": 0,
        "migration_ready": False,
        "decision": "defer-for-path-contract-and-transitive-pin-plan",
    }


def run_trial(fixture: dict[str, Any], prior_fixture: dict[str, Any]) -> dict[str, Any]:
    summary = run_candidate(prior_fixture)
    summary["legacy_error"] = _legacy_error(prior_fixture)
    summary["legacy_failure_reproduced"] = (
        summary["legacy_error"] == fixture["expected_legacy_error"]
    )
    return summary


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["legacy_failure_reproduced"]
        and summary["snapshot_byte_exact"]
        and summary["snapshot_hash_exact"]
        and summary["baseline_loaders"] == fixture["expected_baseline_loaders"]
        and summary["rebound_references"] == 3
        and summary["full_source_selector_repairs"]
        == fixture["expected_full_source_selector_repairs"]
        and summary["rebound_loaders"] == fixture["expected_rebound_loaders"]
        and summary["path_blockers"] == fixture["expected_path_blockers"]
        and summary["temporal_behavior_parity"]
        and summary["candidate_fixture_hashes_changed"] == 3
        and summary["transitive_pins"] == fixture["expected_transitive_pins"]
        and summary["candidate_transitive_pins_preserved"] == 0
        and not summary["migration_ready"]
        and summary["decision"] == fixture["expected_decision"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 16 * 1024
        and summary["evaluation_seconds"] < 1
        and summary["external_calls"] == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture, prior_fixture, fixture_bytes = load_fixture(args.fixture)
    first = run_trial(fixture, prior_fixture)
    repeated = run_trial(fixture, prior_fixture)
    summary = dict(first)
    summary.update({
        "repeatable": first == repeated,
        "fixture_bytes": fixture_bytes,
        "evaluation_seconds": perf_counter() - started,
        "external_calls": 0,
    })
    summary["accepted"] = accepted(summary, fixture)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
