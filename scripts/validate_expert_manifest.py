#!/usr/bin/env python3
"""Validate the structural contract for a quarantined expert package manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


SCHEMA = "expert-package-v1"
TOP_LEVEL_KEYS = {
    "schema",
    "package_id",
    "version",
    "scope",
    "provenance",
    "layers",
    "tests",
    "expires_on",
    "lifecycle",
}
LAYER_KEYS = {"knowledge", "experience", "skills", "tools", "adapters"}
PACKAGE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
VERSION_RE = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
SOURCE_ID_RE = re.compile(r"^SRC-[0-9]{3}$")


def _string_list(value: Any, *, nonempty: bool) -> bool:
    return (
        isinstance(value, list)
        and (bool(value) or not nonempty)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
        and len(value) == len(set(value))
    )


def validate_manifest(
    manifest: Any,
    *,
    reference_date: date | None = None,
    enforce_layer_id_uniqueness: bool = True,
) -> list[str]:
    """Validate structure and, when supplied, expiry against a pinned date."""
    if not isinstance(manifest, dict):
        return ["manifest-not-object"]

    errors: list[str] = []
    keys = set(manifest)
    for key in sorted(TOP_LEVEL_KEYS - keys):
        errors.append(f"missing-key:{key}")
    for key in sorted(keys - TOP_LEVEL_KEYS):
        errors.append(f"unexpected-key:{key}")
    if errors:
        return errors

    if manifest["schema"] != SCHEMA:
        errors.append("invalid-schema")
    if not isinstance(manifest["package_id"], str) or not PACKAGE_ID_RE.fullmatch(
        manifest["package_id"]
    ):
        errors.append("invalid-package-id")
    if not isinstance(manifest["version"], str) or not VERSION_RE.fullmatch(
        manifest["version"]
    ):
        errors.append("invalid-version")

    scope = manifest["scope"]
    if not isinstance(scope, dict) or set(scope) != {"include", "exclude"}:
        errors.append("invalid-scope-keys")
    else:
        for name in ("include", "exclude"):
            if not _string_list(scope[name], nonempty=True):
                errors.append(f"invalid-scope-list:{name}")

    provenance = manifest["provenance"]
    if not isinstance(provenance, list) or not provenance:
        errors.append("empty-provenance")
    else:
        seen_source_ids: set[str] = set()
        for index, source in enumerate(provenance):
            prefix = f"provenance:{index}"
            if not isinstance(source, dict) or set(source) != {
                "source_id",
                "kind",
                "reference",
            }:
                errors.append(f"{prefix}:invalid-entry")
                continue
            source_id = source["source_id"]
            if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
                errors.append(f"{prefix}:invalid-source-id")
            elif source_id in seen_source_ids:
                errors.append(f"{prefix}:duplicate-source-id")
            else:
                seen_source_ids.add(source_id)
            if source["kind"] not in {"public", "synthetic"}:
                errors.append(f"{prefix}:invalid-kind")
            if not isinstance(source["reference"], str) or not source["reference"].strip():
                errors.append(f"{prefix}:invalid-reference")

    layers = manifest["layers"]
    if not isinstance(layers, dict) or set(layers) != LAYER_KEYS:
        errors.append("invalid-layer-keys")
    else:
        valid_layer_lists = True
        for name in sorted(LAYER_KEYS):
            if not _string_list(layers[name], nonempty=False):
                errors.append(f"invalid-layer-list:{name}")
                valid_layer_lists = False
        if enforce_layer_id_uniqueness and valid_layer_lists:
            owners: dict[str, str] = {}
            for name in sorted(LAYER_KEYS):
                for layer_id in layers[name]:
                    if layer_id in owners:
                        errors.append(
                            f"cross-layer-id-collision:{layer_id}:{owners[layer_id]}:{name}"
                        )
                    else:
                        owners[layer_id] = name

    tests = manifest["tests"]
    if not isinstance(tests, dict) or set(tests) != {"target", "held_out_regression"}:
        errors.append("invalid-test-keys")
    else:
        for name in ("target", "held_out_regression"):
            if not _string_list(tests[name], nonempty=True):
                errors.append(f"invalid-test-list:{name}")

    expires_on = manifest["expires_on"]
    if not isinstance(expires_on, str):
        errors.append("invalid-expiry")
    else:
        try:
            parsed_expiry = date.fromisoformat(expires_on)
        except ValueError:
            errors.append("invalid-expiry")
        else:
            if parsed_expiry.isoformat() != expires_on:
                errors.append("invalid-expiry")
            elif reference_date is not None and parsed_expiry < reference_date:
                errors.append("expired")

    lifecycle = manifest["lifecycle"]
    if not isinstance(lifecycle, dict) or set(lifecycle) != {"state", "rollback"}:
        errors.append("invalid-lifecycle-keys")
    else:
        if lifecycle["state"] != "quarantine":
            errors.append("invalid-lifecycle-state")
        rollback = lifecycle["rollback"]
        if not isinstance(rollback, dict) or set(rollback) != {"mode"}:
            errors.append("invalid-rollback")
        elif rollback["mode"] != "unload":
            errors.append("invalid-rollback-mode")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--reference-date",
        required=True,
        help="pinned canonical date used for expiry evaluation (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    try:
        reference_date = date.fromisoformat(args.reference_date)
    except ValueError:
        parser.error("--reference-date must be a canonical calendar date (YYYY-MM-DD)")
    if reference_date.isoformat() != args.reference_date:
        parser.error("--reference-date must be a canonical calendar date (YYYY-MM-DD)")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"expert-manifest: FAIL ({exc})")
        return 1
    errors = validate_manifest(manifest, reference_date=reference_date)
    if errors:
        for error in errors:
            print(error)
        print(f"expert-manifest: FAIL ({len(errors)} finding(s))")
        return 1
    print("expert-manifest: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
