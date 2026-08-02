#!/usr/bin/env python3
"""Validate the structural contract of public experiment records."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path


STRICT_SCHEMA = "strict-v1"
ALLOWED_STATUSES = {"planned", "running", "complete", "blocked", "superseded"}
ALLOWED_COMPUTE = {"C0", "C1", "C2", "C3", "CM"}
ALLOWED_DECISIONS = {"pass", "fail", "mixed", "inconclusive", "proceed", "stop"}
REQUIRED_METADATA = {"Schema", "Date", "Status", "Compute", "Data"}
REQUIRED_SECTIONS = {
    "Question",
    "Hypothesis",
    "Baseline",
    "Protocol",
    "Metrics",
    "Acceptance and stop criteria",
    "Results",
    "Interpretation",
    "Limitations",
    "Decision",
}
TEMPLATE_SECTION_BODIES = {
    "What specific question is being tested?",
    "State a claim that can be rejected.",
    "Describe the comparison and why it is fair.",
    (
        "List deterministic steps, pinned versions, seeds, and budgets. Never include private "
        "addresses, hostnames, identifiers, credentials, paths, or raw system output."
    ),
    "Define quality, cost, latency, memory, and regression metrics before execution.",
    "Declare both success and failure thresholds.",
    "Report sanitized aggregates and uncertainty.",
    "Separate observation from inference.",
    "State the configuration scope and threats to validity.",
}
PLACEHOLDER_SECTION_BODIES = {"tbd", "todo", "pending", "n/a"}

TITLE_RE = re.compile(r"^# (EXP-\d{3}) — \S.*$", re.MULTILINE)
FILENAME_RE = re.compile(r"^(EXP-\d{3})-[a-z0-9][a-z0-9-]*\.md$")
METADATA_RE = re.compile(r"^- \*\*(?P<key>[^*]+)\*\*:\s*(?P<value>.*?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^## (?P<name>[^\n]+?)\s*$", re.MULTILINE)


def title_errors(text: str, filename: str) -> list[str]:
    errors: list[str] = []
    title = TITLE_RE.match(text)
    file_match = FILENAME_RE.fullmatch(filename)
    if title is None:
        errors.append("invalid-title")
    if file_match is None:
        errors.append("invalid-filename")
    if title is not None and file_match is not None and title.group(1) != file_match.group(1):
        errors.append("id-mismatch")
    return errors


def _metadata_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for match in METADATA_RE.finditer(text):
        values.setdefault(match.group("key"), []).append(match.group("value"))
    return values


def _section_body(text: str, section_name: str) -> str:
    matches = list(SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group("name") != section_name:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[match.end():end].strip()
    return ""


def _normalized_section_body(body: str) -> str:
    return " ".join(body.strip("` \t\r\n.").split()).casefold()


def validate_record(text: str, filename: str) -> list[str]:
    errors = title_errors(text, filename)
    metadata = _metadata_values(text)
    schema_values = metadata.get("Schema", [])

    if not schema_values:
        return errors
    if len(schema_values) != 1:
        errors.append("duplicate-metadata:Schema")
        return errors
    if schema_values[0] != STRICT_SCHEMA:
        errors.append("unsupported-schema")
        return errors

    for key in sorted(REQUIRED_METADATA):
        values = metadata.get(key, [])
        if not values or not values[0]:
            errors.append(f"missing-metadata:{key}")
        elif len(values) > 1:
            errors.append(f"duplicate-metadata:{key}")

    status_values = metadata.get("Status", [])
    if len(status_values) == 1 and status_values[0] not in ALLOWED_STATUSES:
        errors.append("invalid-status")

    compute_values = metadata.get("Compute", [])
    if len(compute_values) == 1 and compute_values[0] not in ALLOWED_COMPUTE:
        errors.append("invalid-compute")

    date_values = metadata.get("Date", [])
    if len(date_values) == 1:
        try:
            parsed_date = date.fromisoformat(date_values[0])
        except ValueError:
            errors.append("invalid-date")
        else:
            if parsed_date.isoformat() != date_values[0]:
                errors.append("invalid-date")

    section_counts = Counter(match.group("name") for match in SECTION_RE.finditer(text))
    for section in sorted(REQUIRED_SECTIONS):
        if section_counts[section] == 0:
            errors.append(f"missing-section:{section}")
        elif section_counts[section] > 1:
            errors.append(f"duplicate-section:{section}")
        else:
            body = _section_body(text, section)
            if not body:
                errors.append(f"empty-section:{section}")
            elif _normalized_section_body(body) in {
                _normalized_section_body(value)
                for value in PLACEHOLDER_SECTION_BODIES | TEMPLATE_SECTION_BODIES
            }:
                errors.append(f"placeholder-section:{section}")

    if section_counts["Decision"] == 1:
        decision = _section_body(text, "Decision").strip("` \n")
        if decision not in ALLOWED_DECISIONS:
            errors.append("invalid-decision")

    if status_values == ["complete"] and section_counts["Results"] == 1:
        results = _section_body(text, "Results").strip().lower()
        if results in {"", "pending", "pending.", "tbd", "tbd."}:
            errors.append("complete-results-pending")

    return sorted(set(errors))


def validate_tree(root: Path) -> list[tuple[Path, str]]:
    experiment_dir = root / "experiments"
    findings: list[tuple[Path, str]] = []
    for path in sorted(experiment_dir.glob("EXP-*.md")):
        text = path.read_text(encoding="utf-8")
        for error in validate_record(text, path.name):
            findings.append((path.relative_to(root), error))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    findings = validate_tree(root)
    if findings:
        for path, error in findings:
            print(f"{path}: {error}")
        print(f"experiment-records: FAIL ({len(findings)} finding(s))")
        return 1
    record_count = len(list((root / "experiments").glob("EXP-*.md")))
    print(f"experiment-records: PASS ({record_count} record(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
