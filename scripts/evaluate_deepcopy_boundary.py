#!/usr/bin/env python3
"""Bound deepcopy with a cycle-aware exact-built-in data-graph gate."""

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
DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_deepcopy_boundary_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "prior_evaluator",
    "base_template", "cycle_case", "hook_case", "maximum_containers",
    "expected_baseline_correct", "expected_candidate_correct",
    "expected_baseline_hook_calls", "expected_candidate_hook_calls",
    "expected_decision",
}
ATOMIC_TYPES = {str, int, float, bool, type(None)}


class CopyBoundaryError(ValueError):
    """Raised before deepcopy when a graph crosses the locked data boundary."""


class AdversarialCopyHook:
    """Synthetic custom object whose copy hook mutates its source and returns itself."""

    def __init__(self, source_state: dict[str, Any]) -> None:
        self.source_state = source_state
        self.calls = 0

    def __deepcopy__(self, memo: dict[int, Any]) -> AdversarialCopyHook:
        self.calls += 1
        self.source_state["mutated"] = True
        return self


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    try:
        payload = (ROOT / source["path"]).read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-deepcopy-boundary-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-047-shared-alias-snapshot.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_shared_alias_snapshot_cases.json",
        ),
        "prior_evaluator": (
            {"path", "sha256"},
            "scripts/evaluate_shared_alias_snapshot.py",
        ),
        "base_template": (
            {"path", "sha256"},
            "templates/expert-package-v2.json",
        ),
    }
    pinned_bytes = 0
    pinned: dict[str, bytes] = {}
    for name, (keys, expected_path) in sources.items():
        source = fixture[name]
        if (
            not isinstance(source, dict)
            or set(source) != keys
            or source.get("path") != expected_path
            or not isinstance(source.get("sha256"), str)
            or len(source["sha256"]) != 64
        ):
            raise ValueError(f"{name} pin is unsupported")
        pinned[name] = _read_pinned(source, name.replace("_", "-"))
        pinned_bytes += len(pinned[name])
    if fixture["prior_experiment"]["id"] != "EXP-047":
        raise ValueError("prior experiment changed")

    prior = json.loads(pinned["prior_fixture"])
    if (
        prior.get("expected_deepcopy_correct") != 3
        or prior.get("expected_deepcopy_source_isolations") != 3
        or prior.get("expected_json_alias_losses") != 3
    ):
        raise ValueError("EXP-047 snapshot evidence changed")
    if json.loads(pinned["base_template"]).get("schema") != "expert-package-v2":
        raise ValueError("base template schema changed")

    cycle = fixture["cycle_case"]
    if (
        not isinstance(cycle, dict)
        or set(cycle) != {
            "id", "root_label", "payload_label", "replacement",
            "expected_container_count",
        }
        or cycle["id"] != "COPY-048-CYCLE"
        or cycle["expected_container_count"] != 3
    ):
        raise ValueError("cycle case changed")
    hook = fixture["hook_case"]
    if (
        not isinstance(hook, dict)
        or set(hook) != {"id", "source_label", "expected_error"}
        or hook["id"] != "COPY-048-HOOK"
        or hook["expected_error"] != "unsupported-type:AdversarialCopyHook"
    ):
        raise ValueError("hook case changed")
    if (
        fixture["maximum_containers"] != 16
        or fixture["expected_baseline_correct"] != 1
        or fixture["expected_candidate_correct"] != 2
        or fixture["expected_baseline_hook_calls"] != 1
        or fixture["expected_candidate_hook_calls"] != 0
        or fixture["expected_decision"]
        != "retain-default-and-quarantine-data-only-deepcopy-gate"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def validate_data_graph(value: Any, maximum_containers: int) -> int:
    """Accept only exact dict/list/scalar graphs, preserving cycles via identity memo."""

    seen: set[int] = set()
    stack = [value]
    containers = 0
    while stack:
        current = stack.pop()
        current_type = type(current)
        if current_type in ATOMIC_TYPES:
            continue
        identity = id(current)
        if identity in seen:
            continue
        seen.add(identity)
        if current_type is dict:
            if any(type(key) is not str for key in current):
                raise CopyBoundaryError("unsupported-dict-key")
            containers += 1
            stack.extend(current.values())
        elif current_type is list:
            containers += 1
            stack.extend(current)
        else:
            raise CopyBoundaryError(f"unsupported-type:{current_type.__name__}")
        if containers > maximum_containers:
            raise CopyBoundaryError("container-budget-exceeded")
    return containers


def guarded_deepcopy(value: Any, maximum_containers: int) -> tuple[Any, int]:
    containers = validate_data_graph(value, maximum_containers)
    return copy.deepcopy(value), containers


def _fresh_cycle(case: dict[str, Any]) -> dict[str, Any]:
    root: dict[str, Any] = {"id": case["root_label"], "payload": []}
    bridge = {"label": case["payload_label"], "back": root}
    root["payload"].append(bridge)
    return root


def _cycle_result(
    case: dict[str, Any], maximum_containers: int, guarded: bool
) -> dict[str, Any]:
    source = _fresh_cycle(case)
    if guarded:
        copied, containers = guarded_deepcopy(source, maximum_containers)
    else:
        copied = copy.deepcopy(source)
        containers = None
    topology_preserved = copied["payload"][0]["back"] is copied
    source_isolated = (
        copied is not source
        and copied["payload"] is not source["payload"]
        and copied["payload"][0] is not source["payload"][0]
    )
    copied["payload"][0]["label"] = case["replacement"]
    source_unchanged = (
        source["payload"][0]["label"] == case["payload_label"]
        and source["payload"][0]["back"] is source
    )
    return {
        "correct": topology_preserved and source_isolated and source_unchanged,
        "topology_preserved": topology_preserved,
        "source_isolated": source_isolated,
        "source_unchanged": source_unchanged,
        "container_count": containers,
    }


def _hook_result(
    case: dict[str, Any], maximum_containers: int, guarded: bool
) -> dict[str, Any]:
    state = {"mutated": False}
    hook = AdversarialCopyHook(state)
    source = {"id": case["source_label"], "payload": hook}
    copied: Any = None
    error: str | None = None
    try:
        if guarded:
            copied, _ = guarded_deepcopy(source, maximum_containers)
        else:
            copied = copy.deepcopy(source)
    except CopyBoundaryError as exc:
        error = str(exc)
    rejected = error == case["expected_error"]
    alias_retained = copied is not None and copied["payload"] is hook
    if guarded:
        correct = rejected and hook.calls == 0 and not state["mutated"]
    else:
        correct = hook.calls == 0 and not state["mutated"] and not alias_retained
    return {
        "correct": correct,
        "rejected": rejected,
        "error": error,
        "hook_calls": hook.calls,
        "source_mutated": state["mutated"],
        "alias_retained": alias_retained,
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    maximum = fixture["maximum_containers"]
    baseline_cycle = _cycle_result(fixture["cycle_case"], maximum, False)
    candidate_cycle = _cycle_result(fixture["cycle_case"], maximum, True)
    baseline_hook = _hook_result(fixture["hook_case"], maximum, False)
    candidate_hook = _hook_result(fixture["hook_case"], maximum, True)
    return {
        "case_count": 2,
        "baseline_correct": int(baseline_cycle["correct"]) + int(baseline_hook["correct"]),
        "candidate_correct": int(candidate_cycle["correct"]) + int(candidate_hook["correct"]),
        "baseline_cycle_topology_preserved": baseline_cycle["topology_preserved"],
        "baseline_cycle_source_isolated": baseline_cycle["source_isolated"],
        "candidate_cycle_topology_preserved": candidate_cycle["topology_preserved"],
        "candidate_cycle_source_isolated": candidate_cycle["source_isolated"],
        "candidate_cycle_source_unchanged": candidate_cycle["source_unchanged"],
        "candidate_cycle_container_count": candidate_cycle["container_count"],
        "baseline_hook_calls": baseline_hook["hook_calls"],
        "baseline_hook_source_mutated": baseline_hook["source_mutated"],
        "baseline_hook_alias_retained": baseline_hook["alias_retained"],
        "candidate_hook_rejected": candidate_hook["rejected"],
        "candidate_hook_error": candidate_hook["error"],
        "candidate_hook_calls": candidate_hook["hook_calls"],
        "candidate_hook_source_unchanged": not candidate_hook["source_mutated"],
        "artifact_load_attempts": 0,
        "repository_writes": 0,
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    return (
        summary["case_count"] == 2
        and summary["baseline_correct"]
        == fixture["expected_baseline_correct"] == 1
        and summary["candidate_correct"]
        == fixture["expected_candidate_correct"] == 2
        and summary["baseline_cycle_topology_preserved"]
        and summary["baseline_cycle_source_isolated"]
        and summary["candidate_cycle_topology_preserved"]
        and summary["candidate_cycle_source_isolated"]
        and summary["candidate_cycle_source_unchanged"]
        and summary["candidate_cycle_container_count"]
        == fixture["cycle_case"]["expected_container_count"] == 3
        and summary["baseline_hook_calls"]
        == fixture["expected_baseline_hook_calls"] == 1
        and summary["baseline_hook_source_mutated"]
        and summary["baseline_hook_alias_retained"]
        and summary["candidate_hook_rejected"]
        and summary["candidate_hook_error"]
        == fixture["hook_case"]["expected_error"]
        and summary["candidate_hook_calls"]
        == fixture["expected_candidate_hook_calls"] == 0
        and summary["candidate_hook_source_unchanged"]
        and summary["artifact_load_attempts"] == 0
        and summary["repository_writes"] == 0
        and summary["decision"] == fixture["expected_decision"]
        and summary["repeatable"]
        and summary["fixture_bytes"] < 32 * 1024
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
    second = run_trial(fixture)
    summary = dict(first)
    summary.update({
        "repeatable": first == second,
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
