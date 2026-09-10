#!/usr/bin/env python3
"""Evaluate exact versioned-template discovery for two pinned v2 consumers."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_public_template_v2_migration_replay import (  # noqa: E402
    repaired_packages,
)
from scripts.evaluate_stable_validator_integration import (  # noqa: E402
    StableValidatorManifestKernel,
)
from scripts.validate_expert_manifest import (  # noqa: E402
    SCHEMA,
    V2_SCHEMA,
    validate_manifest,
)


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_versioned_template_discovery_cases.json"
SUPPORTED_SCHEMAS = {SCHEMA, V2_SCHEMA}
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "templates", "consumers",
    "reference_date", "discovery_cases", "targets", "regression", "exclusion",
    "unloaded_expected", "expected_baseline_consumers",
    "expected_candidate_consumers", "expected_removal_error", "expected_decision",
}


def _read_pinned_at(base: Path, source: dict[str, Any], label: str) -> bytes:
    path = base / source["path"]
    try:
        payload = path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    return _read_pinned_at(ROOT, source, label)


def _source_ok(source: Any, *, keys: set[str], expected_path: str) -> bool:
    return (
        isinstance(source, dict)
        and set(source) == keys
        and source.get("path") == expected_path
        and isinstance(source.get("sha256"), str)
        and len(source["sha256"]) == 64
    )


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-versioned-template-discovery-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    prior_experiment = fixture["prior_experiment"]
    if not _source_ok(
        prior_experiment,
        keys={"id", "path", "sha256"},
        expected_path="experiments/EXP-040-versioned-template-materialization.md",
    ) or prior_experiment["id"] != "EXP-040":
        raise ValueError("prior experiment pin is unsupported")
    prior_fixture = fixture["prior_fixture"]
    if not _source_ok(
        prior_fixture,
        keys={"path", "sha256"},
        expected_path="fixtures/expert_versioned_template_materialization_cases.json",
    ):
        raise ValueError("prior fixture pin is unsupported")

    pinned_bytes = len(_read_pinned(prior_experiment, "prior-experiment"))
    prior_payload = _read_pinned(prior_fixture, "prior-fixture")
    pinned_bytes += len(prior_payload)
    prior = json.loads(prior_payload)
    if prior.get("expected_candidate_materialized_consumers") != 1:
        raise ValueError("EXP-040 consumer baseline changed")

    templates = fixture["templates"]
    if not isinstance(templates, list) or len(templates) != 3:
        raise ValueError("fixture must contain exactly three template descriptors")
    expected_templates = [
        (SCHEMA, "templates/expert-package.json", True),
        (V2_SCHEMA, "templates/expert-package-v2.json", False),
        ("expert-package-v3", "templates/expert-package-v3.json", False),
    ]
    for descriptor, (schema, expected_path, is_default) in zip(
        templates, expected_templates
    ):
        if (
            not _source_ok(
                descriptor,
                keys={"schema", "path", "sha256", "default"},
                expected_path=expected_path,
            )
            or descriptor["schema"] != schema
            or descriptor["default"] is not is_default
        ):
            raise ValueError("template descriptor changed")
        if schema in SUPPORTED_SCHEMAS:
            pinned_bytes += len(_read_pinned(descriptor, f"template-{schema}"))

    consumers = fixture["consumers"]
    if not isinstance(consumers, list) or len(consumers) != 2:
        raise ValueError("fixture must contain exactly two consumers")
    if [consumer.get("id") for consumer in consumers] != [
        "consumer-alpha", "consumer-beta"
    ]:
        raise ValueError("consumer identities changed")
    if [consumer.get("authorship") for consumer in consumers] != [
        "locked-exp-040-fixture", "independent-static-fixture"
    ]:
        raise ValueError("consumer authorship declarations changed")
    versioned = templates[1]
    expected_reference = {
        "schema": V2_SCHEMA,
        "path": versioned["path"],
        "sha256": versioned["sha256"],
    }
    if any(consumer.get("template") != expected_reference for consumer in consumers):
        raise ValueError("consumer template reference changed")
    if set(consumers[0]) != {"id", "authorship", "template"}:
        raise ValueError("locked consumer has unexpected structure")
    if set(consumers[1]) != {"id", "authorship", "template", "package"}:
        raise ValueError("independent consumer has unexpected structure")
    package = consumers[1]["package"]
    if not isinstance(package, dict) or set(package) != {
        "manifest", "knowledge_records"
    }:
        raise ValueError("independent package has unexpected structure")
    if validate_manifest(
        package["manifest"], reference_date=date.fromisoformat(fixture["reference_date"])
    ):
        raise ValueError("independent package is invalid")
    if package["manifest"].get("package_id") != "synthetic-indexer":
        raise ValueError("independent package identity changed")

    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be a canonical date") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be a canonical date")

    if not isinstance(fixture["discovery_cases"], list) or len(
        fixture["discovery_cases"]
    ) != 3:
        raise ValueError("fixture must contain exactly three discovery cases")
    for case in fixture["discovery_cases"]:
        if set(case) != {"id", "requested_schema", "expected"}:
            raise ValueError("discovery case has unexpected structure")
    if not isinstance(fixture["targets"], list) or len(fixture["targets"]) != 2:
        raise ValueError("fixture must contain exactly two targets")
    for case in fixture["targets"] + [fixture["regression"], fixture["exclusion"]]:
        if set(case) != {"id", "request", "expected"}:
            raise ValueError("routing case has unexpected structure")
        if set(case["request"]) != {"operation", "scope", "local_id"}:
            raise ValueError("routing request has unexpected structure")

    if (
        fixture["expected_baseline_consumers"] != 1
        or fixture["expected_candidate_consumers"] != 2
        or fixture["expected_removal_error"] != "error:pinned-template-missing"
        or fixture["expected_decision"] != "retain-v1-default-with-opt-in-v2"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def baseline_select(templates: list[dict[str, Any]], requested_schema: Any) -> str:
    del requested_schema
    default = next(descriptor for descriptor in templates if descriptor["default"])
    return f"selected:{default['schema']}:{default['path']}"


def exact_select_at(
    base: Path, templates: list[dict[str, Any]], requested_schema: Any
) -> str:
    if requested_schema is None:
        selected = next(descriptor for descriptor in templates if descriptor["default"])
    elif requested_schema not in SUPPORTED_SCHEMAS:
        return "error:unsupported-template-version"
    else:
        matches = [
            descriptor
            for descriptor in templates
            if descriptor["schema"] == requested_schema
        ]
        if len(matches) != 1:
            return "error:template-selection-ambiguous"
        selected = matches[0]
    try:
        payload = _read_pinned_at(base, selected, "pinned-template")
    except ValueError as exc:
        if str(exc) == "pinned-template-missing":
            return "error:pinned-template-missing"
        return "error:pinned-template-hash-mismatch"
    manifest = json.loads(payload)
    if manifest.get("schema") != selected["schema"]:
        return "error:template-schema-mismatch"
    return f"selected:{selected['schema']}:{selected['path']}"


def exact_select(templates: list[dict[str, Any]], requested_schema: Any) -> str:
    return exact_select_at(ROOT, templates, requested_schema)


def _routing_trial(fixture: dict[str, Any], versioned: dict[str, Any]) -> dict[str, Any]:
    template_package = repaired_packages(versioned)[0]
    independent_package = copy.deepcopy(fixture["consumers"][1]["package"])
    packages = [template_package, independent_package]
    package_ids = [package["manifest"]["package_id"] for package in packages]
    by_id = {package["manifest"]["package_id"]: package for package in packages}
    runs: list[dict[str, Any]] = []
    for order in (package_ids, list(reversed(package_ids))):
        kernel = StableValidatorManifestKernel()
        kernel.compose_quarantined_experts(
            [by_id[package_id] for package_id in order],
            reference_date=date.fromisoformat(fixture["reference_date"]),
        )
        run = {
            "targets": [kernel.answer(case["request"]) for case in fixture["targets"]],
            "regression": kernel.answer(fixture["regression"]["request"]),
            "exclusion": kernel.answer(fixture["exclusion"]["request"]),
        }
        kernel.unload_experts()
        run["unloaded"] = [
            kernel.answer(case["request"]) for case in fixture["targets"]
        ]
        runs.append(run)
    return {"runs": runs}


def _removal_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    public, versioned, _ = fixture["templates"]
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        for descriptor in (public, versioned):
            target = base / descriptor["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_read_pinned(descriptor, f"copy-{descriptor['schema']}"))
        before = exact_select_at(base, fixture["templates"], V2_SCHEMA)
        (base / versioned["path"]).unlink()
        after = exact_select_at(base, fixture["templates"], V2_SCHEMA)
        default_after = exact_select_at(base, fixture["templates"], None)
        incompatible_after = exact_select_at(
            base, fixture["templates"], "expert-package-v3"
        )
    return {
        "versioned_selected_before_removal": before,
        "versioned_after_removal": after,
        "default_after_removal": default_after,
        "incompatible_after_removal": incompatible_after,
        "no_v1_fallback_after_v2_removal": after != default_after,
    }


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    discovery = fixture["discovery_cases"]
    baseline = [
        baseline_select(fixture["templates"], case["requested_schema"])
        for case in discovery
    ]
    candidate = [
        exact_select(fixture["templates"], case["requested_schema"])
        for case in discovery
    ]
    expected = [case["expected"] for case in discovery]
    versioned = json.loads(_read_pinned(fixture["templates"][1], "versioned-template"))
    routing = _routing_trial(fixture, versioned)
    expected_targets = [case["expected"] for case in fixture["targets"]]
    consumer_hash = fixture["templates"][1]["sha256"]
    summary = {
        "baseline_consumers": fixture["expected_baseline_consumers"],
        "candidate_consumers": sum(
            consumer["template"]["sha256"] == consumer_hash
            for consumer in fixture["consumers"]
        ),
        "independent_consumer_valid": validate_manifest(
            fixture["consumers"][1]["package"]["manifest"],
            reference_date=date.fromisoformat(fixture["reference_date"]),
        ) == [],
        "discovered_descriptors": len(fixture["templates"]),
        "supported_descriptors": sum(
            descriptor["schema"] in SUPPORTED_SCHEMAS
            for descriptor in fixture["templates"]
        ),
        "incompatible_descriptor_discovered": any(
            descriptor["schema"] == "expert-package-v3"
            for descriptor in fixture["templates"]
        ),
        "baseline_selection_correct": sum(
            actual == wanted for actual, wanted in zip(baseline, expected)
        ),
        "candidate_selection_correct": sum(
            actual == wanted for actual, wanted in zip(candidate, expected)
        ),
        "default_v1_retained": candidate[0] == expected[0],
        "v2_hash_bound_selection": candidate[1] == expected[1],
        "incompatible_rejected": candidate[2] == expected[2],
        "target_correct": sum(
            actual == wanted
            for run in routing["runs"]
            for actual, wanted in zip(run["targets"], expected_targets)
        ),
        "regression_correct": sum(
            run["regression"] == fixture["regression"]["expected"]
            for run in routing["runs"]
        ),
        "exclusion_correct": sum(
            run["exclusion"] == fixture["exclusion"]["expected"]
            for run in routing["runs"]
        ),
        "order_invariant": routing["runs"][0] == routing["runs"][1],
        "rollback_correct": sum(
            answer == fixture["unloaded_expected"]
            for run in routing["runs"]
            for answer in run["unloaded"]
        ),
        "decision": fixture["expected_decision"],
    }
    summary.update(_removal_trial(fixture))
    return summary


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    expected_default = fixture["discovery_cases"][0]["expected"]
    expected_v2 = fixture["discovery_cases"][1]["expected"]
    expected_incompatible = fixture["discovery_cases"][2]["expected"]
    return (
        summary["baseline_consumers"] == fixture["expected_baseline_consumers"] == 1
        and summary["candidate_consumers"] == fixture["expected_candidate_consumers"] == 2
        and summary["independent_consumer_valid"]
        and summary["discovered_descriptors"] == 3
        and summary["supported_descriptors"] == 2
        and summary["incompatible_descriptor_discovered"]
        and summary["baseline_selection_correct"] == 1
        and summary["candidate_selection_correct"] == 3
        and summary["default_v1_retained"]
        and summary["v2_hash_bound_selection"]
        and summary["incompatible_rejected"]
        and summary["target_correct"] == 4
        and summary["regression_correct"] == 2
        and summary["exclusion_correct"] == 2
        and summary["order_invariant"]
        and summary["rollback_correct"] == 4
        and summary["versioned_selected_before_removal"] == expected_v2
        and summary["versioned_after_removal"] == fixture["expected_removal_error"]
        and summary["default_after_removal"] == expected_default
        and summary["incompatible_after_removal"] == expected_incompatible
        and summary["no_v1_fallback_after_v2_removal"]
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
