#!/usr/bin/env python3
"""Evaluate exact versus highest-compatible pinned template selection."""

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

from scripts.validate_expert_manifest import V2_SCHEMA, validate_manifest  # noqa: E402


DEFAULT_FIXTURE = ROOT / "fixtures" / "expert_template_compatibility_policy_cases.json"
EXPECTED_TOP_LEVEL = {
    "schema", "prior_experiment", "prior_fixture", "base_template",
    "reference_date", "artifacts", "catalogs", "selection_cases", "removal",
    "expected_baseline_correct", "expected_candidate_correct", "expected_decision",
}


def _canonical_payload(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _read_pinned_at(base: Path, source: dict[str, Any], label: str) -> bytes:
    try:
        payload = (base / source["path"]).read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label}-missing") from exc
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"{label}-hash-mismatch")
    return payload


def _read_pinned(source: dict[str, Any], label: str) -> bytes:
    return _read_pinned_at(ROOT, source, label)


def _parse_version(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise ValueError("version must be a string")
    parts = value.split(".")
    if len(parts) != 3 or any(
        not part.isdigit() or (len(part) > 1 and part.startswith("0"))
        for part in parts
    ):
        raise ValueError("version must contain three canonical numeric components")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _derived_artifact(base_template: dict[str, Any], version: str) -> bytes:
    candidate = copy.deepcopy(base_template)
    candidate["version"] = version
    return _canonical_payload(candidate)


def load_fixture(path: Path) -> tuple[dict[str, Any], int]:
    payload = path.read_bytes()
    fixture = json.loads(payload)
    if not isinstance(fixture, dict) or set(fixture) != EXPECTED_TOP_LEVEL:
        raise ValueError("fixture has unexpected top-level structure")
    if fixture["schema"] != "expert-template-compatibility-policy-cases-v1":
        raise ValueError("fixture has an unsupported schema")

    sources = {
        "prior_experiment": (
            {"id", "path", "sha256"},
            "experiments/EXP-041-versioned-template-discovery.md",
        ),
        "prior_fixture": (
            {"path", "sha256"},
            "fixtures/expert_versioned_template_discovery_cases.json",
        ),
        "base_template": (
            {"path", "sha256"},
            "templates/expert-package-v2.json",
        ),
    }
    pinned_bytes = 0
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
        pinned_bytes += len(_read_pinned(source, name.replace("_", "-")))
    if fixture["prior_experiment"]["id"] != "EXP-041":
        raise ValueError("prior experiment changed")
    prior = json.loads(_read_pinned(fixture["prior_fixture"], "prior-fixture"))
    if prior.get("expected_candidate_consumers") != 2:
        raise ValueError("EXP-041 consumer baseline changed")

    try:
        reference_date = date.fromisoformat(fixture["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reference_date must be canonical") from exc
    if reference_date.isoformat() != fixture["reference_date"]:
        raise ValueError("reference_date must be canonical")

    base_template = json.loads(_read_pinned(fixture["base_template"], "base-template"))
    artifacts = fixture["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 4:
        raise ValueError("fixture must contain four artifacts")
    ids: set[str] = set()
    paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "id", "schema", "version", "path", "sha256"
        }:
            raise ValueError("artifact descriptor has unexpected structure")
        if artifact["schema"] != V2_SCHEMA:
            raise ValueError("artifact schema changed")
        _parse_version(artifact["version"])
        if artifact["id"] in ids or artifact["path"] in paths:
            raise ValueError("artifact identity or path is duplicated")
        ids.add(artifact["id"])
        paths.add(artifact["path"])
        derived = _derived_artifact(base_template, artifact["version"])
        if hashlib.sha256(derived).hexdigest() != artifact["sha256"]:
            raise ValueError("derived artifact hash changed")
        manifest = json.loads(derived)
        if validate_manifest(manifest, reference_date=reference_date):
            raise ValueError("derived artifact is invalid")
        pinned_bytes += len(derived)

    if set(fixture["catalogs"]) != {"patch", "minor", "ambiguous"}:
        raise ValueError("catalog identities changed")
    expected_catalogs = {
        "patch": ["v2-1-0-0", "v2-1-0-2"],
        "minor": ["v2-1-0-0", "v2-1-0-2", "v2-1-1-0"],
        "ambiguous": [
            "v2-1-0-0", "v2-1-0-2", "v2-1-1-0", "v2-1-1-0-mirror"
        ],
    }
    if fixture["catalogs"] != expected_catalogs:
        raise ValueError("catalog membership changed")

    cases = fixture["selection_cases"]
    if not isinstance(cases, list) or len(cases) != 5:
        raise ValueError("fixture must contain five selection cases")
    if [case.get("id") for case in cases] != [
        "SEL-042-A", "SEL-042-B", "SEL-042-C", "SEL-042-D", "SEL-042-E"
    ]:
        raise ValueError("selection case identities changed")
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "id", "catalog", "policy", "expected"
        }:
            raise ValueError("selection case has unexpected structure")

    removal = fixture["removal"]
    if not isinstance(removal, dict) or set(removal) != {
        "catalog", "policy", "selected_artifact", "expected_before", "expected_after"
    }:
        raise ValueError("removal case has unexpected structure")
    if (
        fixture["expected_baseline_correct"] != 1
        or fixture["expected_candidate_correct"] != 5
        or removal["expected_after"] != "error:pinned-template-missing"
        or fixture["expected_decision"]
        != "retain-exact-default-and-quarantine-compatible-selection"
    ):
        raise ValueError("locked expectation changed")
    return fixture, len(payload) + pinned_bytes


def _artifacts_by_id(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {artifact["id"]: artifact for artifact in fixture["artifacts"]}


def _catalog(fixture: dict[str, Any], name: str) -> list[dict[str, Any]]:
    by_id = _artifacts_by_id(fixture)
    return [by_id[artifact_id] for artifact_id in fixture["catalogs"][name]]


def materialize_artifacts(base: Path, fixture: dict[str, Any]) -> None:
    template = json.loads(_read_pinned(fixture["base_template"], "base-template"))
    for artifact in fixture["artifacts"]:
        target = base / artifact["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_derived_artifact(template, artifact["version"]))


def _select_descriptor(
    descriptors: list[dict[str, Any]], policy: dict[str, Any]
) -> dict[str, Any] | str:
    if not isinstance(policy, dict) or policy.get("schema") != V2_SCHEMA:
        return "error:unsupported-template-schema"
    mode = policy.get("mode")
    if mode == "exact":
        if set(policy) != {"mode", "schema", "version"}:
            return "error:invalid-compatibility-policy"
        try:
            wanted = _parse_version(policy["version"])
        except ValueError:
            return "error:invalid-compatibility-policy"
        matches = [
            item for item in descriptors
            if item["schema"] == policy["schema"]
            and _parse_version(item["version"]) == wanted
        ]
    elif mode == "compatible":
        if set(policy) != {"mode", "schema", "minimum", "major"}:
            return "error:invalid-compatibility-policy"
        try:
            minimum = _parse_version(policy["minimum"])
        except ValueError:
            return "error:invalid-compatibility-policy"
        if not isinstance(policy["major"], int) or policy["major"] != minimum[0]:
            return "error:invalid-compatibility-policy"
        compatible = [
            item for item in descriptors
            if item["schema"] == policy["schema"]
            and _parse_version(item["version"])[0] == policy["major"]
            and _parse_version(item["version"]) >= minimum
        ]
        if not compatible:
            return "error:no-compatible-template"
        highest = max(_parse_version(item["version"]) for item in compatible)
        matches = [
            item for item in compatible
            if _parse_version(item["version"]) == highest
        ]
    else:
        return "error:invalid-compatibility-policy"
    if not matches:
        return "error:no-compatible-template"
    if len(matches) != 1:
        return "error:ambiguous-highest-version"
    return matches[0]


def _load_selected(base: Path, selected: dict[str, Any] | str) -> str:
    if isinstance(selected, str):
        return selected
    try:
        payload = _read_pinned_at(base, selected, "pinned-template")
    except ValueError as exc:
        if str(exc) == "pinned-template-missing":
            return "error:pinned-template-missing"
        return "error:pinned-template-hash-mismatch"
    manifest = json.loads(payload)
    if manifest.get("schema") != selected["schema"]:
        return "error:template-schema-mismatch"
    if manifest.get("version") != selected["version"]:
        return "error:template-version-mismatch"
    return (
        f"selected:{selected['schema']}:{selected['version']}:{selected['path']}"
    )


def exact_baseline_select_at(
    base: Path, descriptors: list[dict[str, Any]], policy: dict[str, Any]
) -> str:
    if policy.get("mode") != "exact":
        return "error:exact-version-required"
    return _load_selected(base, _select_descriptor(descriptors, policy))


def compatible_select_at(
    base: Path, descriptors: list[dict[str, Any]], policy: dict[str, Any]
) -> str:
    return _load_selected(base, _select_descriptor(descriptors, policy))


def run_trial(fixture: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        materialize_artifacts(base, fixture)
        baseline: list[str] = []
        candidate: list[str] = []
        for case in fixture["selection_cases"]:
            descriptors = _catalog(fixture, case["catalog"])
            baseline.append(exact_baseline_select_at(base, descriptors, case["policy"]))
            candidate.append(compatible_select_at(base, descriptors, case["policy"]))

        removal = fixture["removal"]
        removal_catalog = _catalog(fixture, removal["catalog"])
        before = compatible_select_at(base, removal_catalog, removal["policy"])
        selected = _artifacts_by_id(fixture)[removal["selected_artifact"]]
        (base / selected["path"]).unlink()
        after = compatible_select_at(base, removal_catalog, removal["policy"])
        lower_candidates_remain = all(
            (base / artifact["path"]).is_file()
            for artifact in removal_catalog
            if _parse_version(artifact["version"]) < _parse_version(selected["version"])
        )

    expected = [case["expected"] for case in fixture["selection_cases"]]
    base_template = json.loads(_read_pinned(fixture["base_template"], "base-template"))
    reference_date = date.fromisoformat(fixture["reference_date"])
    valid_artifacts = sum(
        validate_manifest(
            json.loads(_derived_artifact(base_template, artifact["version"])),
            reference_date=reference_date,
        ) == []
        for artifact in fixture["artifacts"]
    )
    return {
        "artifact_count": len(fixture["artifacts"]),
        "unique_version_count": len({item["version"] for item in fixture["artifacts"]}),
        "valid_artifacts": valid_artifacts,
        "baseline_correct": sum(actual == wanted for actual, wanted in zip(baseline, expected)),
        "candidate_correct": sum(actual == wanted for actual, wanted in zip(candidate, expected)),
        "exact_correct": candidate[0] == expected[0],
        "highest_patch_correct": candidate[1] == expected[1],
        "highest_minor_correct": candidate[2] == expected[2],
        "no_match_rejected": candidate[3] == expected[3],
        "ambiguity_rejected": candidate[4] == expected[4],
        "removal_before": before,
        "removal_after": after,
        "lower_candidates_remain": lower_candidates_remain,
        "no_downgrade_after_removal": after == removal["expected_after"],
        "decision": fixture["expected_decision"],
    }


def accepted(summary: dict[str, Any], fixture: dict[str, Any]) -> bool:
    removal = fixture["removal"]
    return (
        summary["artifact_count"] == 4
        and summary["unique_version_count"] == 3
        and summary["valid_artifacts"] == 4
        and summary["baseline_correct"] == fixture["expected_baseline_correct"] == 1
        and summary["candidate_correct"] == fixture["expected_candidate_correct"] == 5
        and summary["exact_correct"]
        and summary["highest_patch_correct"]
        and summary["highest_minor_correct"]
        and summary["no_match_rejected"]
        and summary["ambiguity_rejected"]
        and summary["removal_before"] == removal["expected_before"]
        and summary["removal_after"] == removal["expected_after"]
        and summary["lower_candidates_remain"]
        and summary["no_downgrade_after_removal"]
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
