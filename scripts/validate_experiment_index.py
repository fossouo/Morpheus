#!/usr/bin/env python3
"""Validate coverage and metadata consistency of the experiment index."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_experiment_records import (
    ALLOWED_DECISIONS,
    ALLOWED_STATUSES,
    METADATA_RE,
    metadata_values,
)


INDEX_HEADERS = ["ID", "Title", "Status", "Verdict"]
INDEX_DELIMITER_RE = re.compile(r"^:?-{3,}:?$")
EXPERIMENT_FILENAME_RE = re.compile(r"^(EXP-\d{3})-[a-z0-9][a-z0-9-]*\.md$")
EXPERIMENT_ID_RE = re.compile(r"^EXP-\d{3}$")
DECISION_SECTION_RE = re.compile(
    r"^## (?:Decision|Verdict)[ \t]*$\n(?P<body>.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
DECISION_TOKEN_RE = re.compile(
    r"^[\s`*_]*(?P<decision>pass|fail|mixed|inconclusive|proceed|stop)\b",
    re.IGNORECASE,
)
INLINE_VERDICT_RE = re.compile(
    r"^\*\*Verdict:[ \t]*(?P<decision>pass|fail|mixed|inconclusive|proceed|stop)"
    r"\.?\*\*[ \t]*$",
    re.MULTILINE | re.IGNORECASE,
)
RECORD_HEADING_RE = re.compile(
    r"^# (?P<experiment_id>EXP-\d{3}) —(?P<title>[^\r\n]*)$",
    re.MULTILINE,
)


def split_gfm_row(line: str) -> list[str] | None:
    """Split the repository's pipe-delimited GFM rows, preserving escaped pipes."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in stripped[1:-1]:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells


def parse_index(index_text: str) -> tuple[list[dict[str, str]], list[str]]:
    lines = index_text.splitlines()
    header_lines = [
        index for index, line in enumerate(lines) if split_gfm_row(line) == INDEX_HEADERS
    ]
    if len(header_lines) != 1:
        error = "missing-index-table" if not header_lines else "duplicate-index-table"
        return [], [error]

    header_index = header_lines[0]
    if header_index + 1 >= len(lines):
        return [], ["missing-index-delimiter"]
    delimiter = split_gfm_row(lines[header_index + 1])
    if (
        delimiter is None
        or len(delimiter) != len(INDEX_HEADERS)
        or any(INDEX_DELIMITER_RE.fullmatch(cell) is None for cell in delimiter)
    ):
        return [], ["invalid-index-delimiter"]

    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for line_number, line in enumerate(lines[header_index + 2 :], start=header_index + 3):
        if not line.strip():
            break
        cells = split_gfm_row(line)
        if cells is None or len(cells) != len(INDEX_HEADERS):
            errors.append(f"malformed-index-row:{line_number}")
            continue
        row = dict(zip(INDEX_HEADERS, cells))
        experiment_id = row["ID"]
        if EXPERIMENT_ID_RE.fullmatch(experiment_id) is None:
            errors.append(f"invalid-index-id:{line_number}")
            continue
        if not row["Title"]:
            errors.append(f"missing-index-title:{experiment_id}")
        if row["Status"] not in ALLOWED_STATUSES:
            errors.append(f"invalid-index-status:{experiment_id}")
        if row["Verdict"] not in ALLOWED_DECISIONS:
            errors.append(f"invalid-index-verdict:{experiment_id}")
        rows.append(row)
    return rows, errors


def _record_decision(text: str) -> str | None:
    sections = list(DECISION_SECTION_RE.finditer(text))
    if len(sections) == 1:
        token = DECISION_TOKEN_RE.match(sections[0].group("body"))
        if token is not None:
            return token.group("decision").lower()
    inline = list(INLINE_VERDICT_RE.finditer(text))
    if len(inline) == 1:
        return inline[0].group("decision").lower()
    return None


def _rendered_index_title(title: str) -> str:
    """Decode the escaped-pipe form supported by this repository's table parser."""
    return title.replace(r"\|", "|")


def _title_findings(
    rows: list[dict[str, str]],
    row_counts: Counter[str],
    record_groups: dict[str, list[tuple[str, str]]],
) -> list[str]:
    findings: list[str] = []
    single_rows = {row["ID"]: row for row in rows if row_counts[row["ID"]] == 1}
    for experiment_id in sorted(set(single_rows) & set(record_groups)):
        if len(record_groups[experiment_id]) != 1:
            continue
        _, text = record_groups[experiment_id][0]
        headings = list(RECORD_HEADING_RE.finditer(text))
        if not headings:
            findings.append(f"missing-record-heading:{experiment_id}")
            continue
        if len(headings) > 1:
            findings.append(f"duplicate-record-heading:{experiment_id}")
            continue
        heading = headings[0]
        if heading.group("experiment_id") != experiment_id:
            findings.append(f"record-heading-id-mismatch:{experiment_id}")
            continue
        record_title = heading.group("title").strip()
        if not record_title:
            findings.append(f"missing-record-title:{experiment_id}")
            continue
        index_title = _rendered_index_title(single_rows[experiment_id]["Title"])
        if index_title != record_title:
            findings.append(f"title-mismatch:{experiment_id}")
    return findings


def consistency_findings(
    index_text: str,
    records: Mapping[str, str],
    *,
    check_titles: bool = True,
) -> list[str]:
    rows, findings = parse_index(index_text)
    record_groups: dict[str, list[tuple[str, str]]] = {}
    for filename, text in records.items():
        match = EXPERIMENT_FILENAME_RE.fullmatch(filename)
        if match is None:
            findings.append(f"invalid-record-filename:{filename}")
            continue
        record_groups.setdefault(match.group(1), []).append((filename, text))

    row_counts = Counter(row["ID"] for row in rows)
    for experiment_id, count in sorted(row_counts.items()):
        if count > 1:
            findings.append(f"duplicate-index-id:{experiment_id}")
    for experiment_id, group in sorted(record_groups.items()):
        if len(group) > 1:
            findings.append(f"duplicate-record-id:{experiment_id}")

    row_ids = set(row_counts)
    record_ids = set(record_groups)
    for experiment_id in sorted(record_ids - row_ids):
        findings.append(f"missing-index-entry:{experiment_id}")
    for experiment_id in sorted(row_ids - record_ids):
        findings.append(f"orphan-index-entry:{experiment_id}")

    single_rows = {row["ID"]: row for row in rows if row_counts[row["ID"]] == 1}
    for experiment_id in sorted(row_ids & record_ids):
        if experiment_id not in single_rows or len(record_groups[experiment_id]) != 1:
            continue
        _, text = record_groups[experiment_id][0]
        status_values = metadata_values(text, METADATA_RE).get("Status", [])
        if len(status_values) != 1:
            findings.append(f"unreadable-record-status:{experiment_id}")
        elif single_rows[experiment_id]["Status"] != status_values[0]:
            findings.append(f"status-mismatch:{experiment_id}")
        decision = _record_decision(text)
        if decision is None:
            findings.append(f"unreadable-record-verdict:{experiment_id}")
        elif single_rows[experiment_id]["Verdict"] != decision:
            findings.append(f"verdict-mismatch:{experiment_id}")

    if check_titles:
        findings.extend(_title_findings(rows, row_counts, record_groups))

    return sorted(set(findings))


def validate_tree(root: Path) -> list[str]:
    experiment_dir = root / "experiments"
    index_text = (experiment_dir / "README.md").read_text(encoding="utf-8")
    records = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(experiment_dir.glob("EXP-*.md"))
    }
    return consistency_findings(index_text, records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    findings = validate_tree(args.root.resolve())
    if findings:
        for finding in findings:
            print(f"experiments/README.md: {finding}")
        print(f"experiment-index: FAIL ({len(findings)} finding(s))")
        return 1
    record_count = len(list((args.root.resolve() / "experiments").glob("EXP-*.md")))
    print(f"experiment-index: PASS ({record_count} record(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
