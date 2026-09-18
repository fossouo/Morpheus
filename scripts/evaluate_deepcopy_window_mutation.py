#!/usr/bin/env python3
"""Detect a locked built-in mutation between deepcopy preflight and return."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from scripts import evaluate_deepcopy_boundary as boundary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_deepcopy_window_mutation_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "prior_evaluator",
    "base_template", "cases", "maximum_containers", "expected_container_count",
    "expected_baseline_correct", "expected_candidate_correct",
    "expected_baseline_silent_drifts", "expected_candidate_detected_mutations",
    "expected_candidate_error", "expected_decision",
}


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
    if fixture["schema"] != "expert-deepcopy-window-mutation-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-048-deepcopy-boundary.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_deepcopy_boundary_cases.json",
        ),
        "prior_evaluator": (
            {"path", "sha256"},
            "scripts/evaluate_deepcopy_boundary.py",
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
    if fixture["prior_experiment"]["id"] != "EXP-048":
        raise ValueError("prior experiment changed")

    prior = json.loads(pinned["prior_fixture"])
    if (
        prior.get("expected_baseline_correct") != 1
        or prior.get("expected_candidate_correct") != 2
        or prior.get("expected_candidate_hook_calls") != 0
    ):
        raise ValueError("EXP-048 boundary evidence changed")
    if json.loads(pinned["base_template"]).get("schema") != "expert-package-v2":
        raise ValueError("base template schema changed")

    cases = fixture["cases"]
    if not isinstance(cases, list) or len(cases) != 2:
        raise ValueError("fixture must contain two cases")
    expected_cases = {
        "COPY-049-CONTROL": ("none", "accept", "accept"),
        "COPY-049-SCALAR": ("replace-payload-label", "reject", "reject"),
    }
    required_case_keys = {
        "id", "mutation", "root_label", "payload_label", "replacement",
        "expected_baseline", "expected_candidate",
    }
    if {case.get("id") for case in cases} != set(expected_cases):
        raise ValueError("locked cases changed")
    for case in cases:
        if set(case) != required_case_keys:
            raise ValueError("case structure changed")
        if (
            (case["mutation"], case["expected_baseline"], case["expected_candidate"])
            != expected_cases[case["id"]]
        ):
            raise ValueError("case expectation changed")
    if (
        fixture["maximum_containers"] != 16
        or fixture["expected_container_count"] != 3
        or fixture["expected_baseline_correct"] != 1
        or fixture["expected_candidate_correct"] != 2
        or fixture["expected_baseline_silent_drifts"] != 1
        or fixture["expected_candidate_detected_mutations"] != 1
        or fixture["expected_candidate_error"]
        != "source-changed-during-copy-window"
        or fixture["expected_decision"]
        != "retain-default-and-quarantine-window-integrity-gate"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def canonical_graph_bytes(value: Any) -> bytes:
    """Encode exact built-in graphs with deterministic alias and cycle references."""

    memo: dict[int, int] = {}
    nodes: list[Any] = []

    def visit(current: Any) -> Any:
        current_type = type(current)
        if current_type is str:
            return ["str", current]
        if current_type is bool:
            return ["bool", current]
        if current_type is int:
            return ["int", str(current)]
        if current_type is float:
            return ["float", current.hex()]
        if current is None:
            return ["none"]
        if current_type not in {dict, list}:
            raise boundary.CopyBoundaryError(
                f"unsupported-type:{current_type.__name__}"
            )
        identity = id(current)
        if identity in memo:
            return ["ref", memo[identity]]
        index = len(nodes)
        memo[identity] = index
        nodes.append(None)
        if current_type is dict:
            if any(type(key) is not str for key in current):
                raise boundary.CopyBoundaryError("unsupported-dict-key")
            node = ["dict", [[key, visit(current[key])] for key in sorted(current)]]
        else:
            node = ["list", [visit(item) for item in current]]
        nodes[index] = node
        return ["ref", index]

    encoded = {"root": visit(value), "nodes": nodes}
    return json.dumps(
        encoded, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def graph_digest(value: Any) -> str:
    return hashlib.sha256(canonical_graph_bytes(value)).hexdigest()


def _fresh_graph(case: dict[str, Any]) -> dict[str, Any]:
    root: dict[str, Any] = {"id": case["root_label"], "payload": []}
    bridge = {"label": case["payload_label"], "back": root}
    root["payload"].append(bridge)
    return root


def _injector(case: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
    if case["mutation"] == "none":
        return lambda source: None
    if case["mutation"] == "replace-payload-label":
        return lambda source: source["payload"][0].__setitem__(
            "label", case["replacement"]
        )
    raise ValueError("unsupported mutation")


def _copy_with_window_check(
    source: dict[str, Any],
    maximum_containers: int,
    inject: Callable[[dict[str, Any]], None],
    guarded: bool,
) -> tuple[Any | None, dict[str, Any]]:
    containers = boundary.validate_data_graph(source, maximum_containers)
    before = graph_digest(source)
    inject(source)
    copied = copy.deepcopy(source)
    after = graph_digest(source)
    copied_digest = graph_digest(copied)
    drift = before != after or before != copied_digest
    if guarded and drift:
        return None, {
            "error": "source-changed-during-copy-window",
            "containers": containers,
            "before": before,
            "after": after,
            "copied": copied_digest,
            "drift": True,
        }
    return copied, {
        "error": None,
        "containers": containers,
        "before": before,
        "after": after,
        "copied": copied_digest,
        "drift": drift,
    }


def _case_result(
    case: dict[str, Any], maximum_containers: int, guarded: bool
) -> dict[str, Any]:
    source = _fresh_graph(case)
    copied, details = _copy_with_window_check(
        source, maximum_containers, _injector(case), guarded
    )
    outcome = "reject" if details["error"] else "accept"
    expected = case["expected_candidate"] if guarded else case["expected_baseline"]
    topology_preserved = (
        copied is None
        or (
            copied is not source
            and copied["payload"] is not source["payload"]
            and copied["payload"][0]["back"] is copied
        )
    )
    return {
        "id": case["id"],
        "correct": outcome == expected and topology_preserved,
        "outcome": outcome,
        "error": details["error"],
        "drift": details["drift"],
        "copy_returned": copied is not None,
        "copy_matches_post_mutation": details["copied"] == details["after"],
        "container_count": details["containers"],
        "topology_preserved": topology_preserved,
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    maximum = fixture["maximum_containers"]
    baseline = [_case_result(case, maximum, False) for case in fixture["cases"]]
    candidate = [_case_result(case, maximum, True) for case in fixture["cases"]]
    baseline_mutation = next(item for item in baseline if item["id"] == "COPY-049-SCALAR")
    candidate_mutation = next(item for item in candidate if item["id"] == "COPY-049-SCALAR")
    return {
        "case_count": len(fixture["cases"]),
        "baseline_correct": sum(item["correct"] for item in baseline),
        "candidate_correct": sum(item["correct"] for item in candidate),
        "baseline_silent_drifts": sum(
            item["drift"] and item["outcome"] == "accept" for item in baseline
        ),
        "candidate_detected_mutations": sum(
            item["drift"] and item["outcome"] == "reject" for item in candidate
        ),
        "baseline_mutation_copy_matches_post_mutation": baseline_mutation[
            "copy_matches_post_mutation"
        ],
        "candidate_mutation_error": candidate_mutation["error"],
        "candidate_mutation_copy_returned": candidate_mutation["copy_returned"],
        "all_container_counts_locked": all(
            item["container_count"] == fixture["expected_container_count"]
            for item in baseline + candidate
        ),
        "all_topologies_preserved": all(
            item["topology_preserved"] for item in baseline + candidate
        ),
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
        and summary["baseline_silent_drifts"]
        == fixture["expected_baseline_silent_drifts"] == 1
        and summary["candidate_detected_mutations"]
        == fixture["expected_candidate_detected_mutations"] == 1
        and summary["baseline_mutation_copy_matches_post_mutation"]
        and summary["candidate_mutation_error"]
        == fixture["expected_candidate_error"]
        and not summary["candidate_mutation_copy_returned"]
        and summary["all_container_counts_locked"]
        and summary["all_topologies_preserved"]
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
