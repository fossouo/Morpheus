#!/usr/bin/env python3
"""Test a snapshot plus three direct path rebindings without mutating history."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_expert_manifest_temporal_corpus as temporal  # noqa: E402
from scripts import evaluate_public_template_v2_migration as migration  # noqa: E402
from scripts import evaluate_template_exclusion_reachability as reachability  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures/expert_template_v1_snapshot_rebind_cases.json"
EXPECTED_IDS = {"temporal-corpus", "migration", "reachability"}


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    payload = (ROOT / source["path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label} hash mismatch")
    return payload


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    required = {
        "schema", "template", "snapshot", "direct_pins",
        "expected_baseline_loaders", "expected_rebound_loaders",
        "expected_path_blockers", "expected_transitive_pins",
    }
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-template-v1-snapshot-rebind-cases-v1":
        raise ValueError("fixture has an unsupported schema")
    template = fixture["template"]
    snapshot = fixture["snapshot"]
    if (
        set(template) != {"path", "sha256"}
        or template["path"] != "templates/expert-package.json"
        or set(snapshot) != {"path", "sha256"}
        or snapshot["path"] != "templates/archive/expert-package-v1.json"
        or template["sha256"] != snapshot["sha256"]
    ):
        raise ValueError("template and snapshot pins are not locked")
    template_payload = _read_pinned(template, "public template")
    snapshot_payload = _read_pinned(snapshot, "v1 snapshot")
    pins = fixture["direct_pins"]
    if (
        not isinstance(pins, list)
        or len(pins) != 3
        or {item.get("id") for item in pins if isinstance(item, dict)} != EXPECTED_IDS
    ):
        raise ValueError("direct pin set changed")
    source_bytes = 0
    for item in pins:
        if set(item) != {"id", "path", "sha256", "selector"}:
            raise ValueError("direct pin has unexpected structure")
        source_bytes += len(_read_pinned(item, item["id"]))
    if (
        fixture["expected_baseline_loaders"] != 3
        or fixture["expected_rebound_loaders"] != 1
        or fixture["expected_path_blockers"] != {
            "migration": "template must contain the public path and SHA-256",
            "reachability": "template pin is unsupported",
        }
        or fixture["expected_transitive_pins"] != 3
    ):
        raise ValueError("locked expectations changed")
    return fixture, len(payload) + len(template_payload) + len(snapshot_payload) + source_bytes


def _selected_pin(document: dict[str, Any], selector: list[str]) -> dict[str, Any]:
    value: Any = document
    for key in selector:
        if key == "public-template":
            matches = [item for item in value if item.get("id") == key]
            if len(matches) != 1:
                raise ValueError("public-template selector changed")
            value = matches[0]
        else:
            value = value[key]
    if not isinstance(value, dict):
        raise ValueError("selected pin is not an object")
    return value


def _rebound_document(source: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    document = json.loads((ROOT / source["path"]).read_text(encoding="utf-8"))
    rebound = copy.deepcopy(document)
    selected = _selected_pin(rebound, source["selector"])
    if selected != {
        "path": "templates/expert-package.json",
        "sha256": snapshot["sha256"],
    }:
        raise ValueError(f"{source['id']} direct pin changed")
    selected["path"] = snapshot["path"]
    return rebound


def _load_with(
    loader: Callable[[Path], Any], document: dict[str, Any]
) -> tuple[bool, str | None, Any]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        try:
            return True, None, loader(path)
        except ValueError as exc:
            return False, str(exc), None


def _transitive_pin_count(source_hash: str) -> int:
    count = 0
    for path in (ROOT / "fixtures").glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, child in current.items():
                    if key == "sha256" and child == source_hash:
                        count += 1
                    else:
                        stack.append(child)
            elif isinstance(current, list):
                stack.extend(current)
    return count


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    template_payload = (ROOT / fixture["template"]["path"]).read_bytes()
    snapshot_payload = (ROOT / fixture["snapshot"]["path"]).read_bytes()
    by_id = {item["id"]: item for item in fixture["direct_pins"]}
    loaders: dict[str, Callable[[Path], Any]] = {
        "temporal-corpus": temporal.load_fixture,
        "migration": migration.load_fixture,
        "reachability": reachability.load_fixture,
    }
    baseline_loaded = 0
    rebound_loaded = 0
    blockers: dict[str, str] = {}
    fixture_hashes_changed = 0
    transitive_pins = 0
    temporal_parity = False
    for source_id, loader in loaders.items():
        source = by_id[source_id]
        original_path = ROOT / source["path"]
        original_document = json.loads(original_path.read_text(encoding="utf-8"))
        baseline_ok, _, baseline = _load_with(loader, original_document)
        baseline_loaded += baseline_ok
        rebound_document = _rebound_document(source, fixture["snapshot"])
        rebound_ok, error, rebound = _load_with(loader, rebound_document)
        rebound_loaded += rebound_ok
        if error is not None:
            blockers[source_id] = error
        original_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
        rebound_bytes = (json.dumps(rebound_document, indent=2) + "\n").encode("utf-8")
        rebound_hash = hashlib.sha256(rebound_bytes).hexdigest()
        fixture_hashes_changed += rebound_hash != original_hash
        transitive_pins += _transitive_pin_count(original_hash)
        if source_id == "temporal-corpus" and baseline_ok and rebound_ok:
            temporal_parity = temporal.run_trial(baseline) == temporal.run_trial(rebound)
    return {
        "snapshot_byte_exact": snapshot_payload == template_payload,
        "snapshot_hash_exact": hashlib.sha256(snapshot_payload).hexdigest() == fixture["template"]["sha256"],
        "baseline_loaders": baseline_loaded,
        "rebound_references": len(loaders),
        "rebound_loaders": rebound_loaded,
        "path_blockers": blockers,
        "temporal_behavior_parity": temporal_parity,
        "candidate_fixture_hashes_changed": fixture_hashes_changed,
        "transitive_pins": transitive_pins,
        "candidate_transitive_pins_preserved": 0,
        "migration_ready": False,
        "decision": "defer-for-path-contract-and-transitive-pin-plan",
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["snapshot_byte_exact"]
        and summary["snapshot_hash_exact"]
        and summary["baseline_loaders"] == fixture["expected_baseline_loaders"]
        and summary["rebound_references"] == 3
        and summary["rebound_loaders"] == fixture["expected_rebound_loaders"]
        and summary["path_blockers"] == fixture["expected_path_blockers"]
        and summary["temporal_behavior_parity"]
        and summary["candidate_fixture_hashes_changed"] == 3
        and summary["transitive_pins"] == fixture["expected_transitive_pins"]
        and summary["candidate_transitive_pins_preserved"] == 0
        and not summary["migration_ready"]
        and summary["decision"] == "defer-for-path-contract-and-transitive-pin-plan"
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
    summary["accepted"] = accepted(summary, fixture)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
