#!/usr/bin/env python3
"""Fail closed on common accidental disclosures in a public research tree."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".csv", ".tsv", ".sh",
}

SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]


RULES = (
    Rule(
        "private-ipv4",
        re.compile(
            r"(?<![\d.])(?:10\.(?:\d{1,3}\.){2}\d{1,3}|"
            r"192\.168\.(?:\d{1,3}\.)\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})(?![\d.])"
        ),
    ),
    Rule("tailscale-ipv4", re.compile(r"(?<![\d.])100\.(?:\d{1,3}\.){2}\d{1,3}(?![\d.])")),
    Rule("mac-address", re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")),
    Rule("gpu-uuid", re.compile(r"\bGPU-[0-9a-fA-F-]{16,}\b")),
    Rule("unix-home-path", re.compile(r"(?<![\w])/(?:Users|home)/[^/\s]+/")),
    Rule("secret-assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*[\"']?[^\"'\s]{8,}"
    )),
    Rule("github-token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    Rule("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    Rule("ssh-private-key", re.compile(r"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----")),
)

ALLOW_MARKER = "public-safety: allow-example"


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", "Dockerfile"}:
            yield path


def scan_file(path: Path) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings
    for line_number, line in enumerate(lines, start=1):
        if ALLOW_MARKER in line:
            continue
        for rule in RULES:
            if rule.pattern.search(line):
                findings.append((line_number, rule.name))
    return findings


def scan_tree(root: Path) -> list[tuple[Path, int, str]]:
    results: list[tuple[Path, int, str]] = []
    for path in iter_text_files(root):
        for line_number, rule_name in scan_file(path):
            results.append((path.relative_to(root), line_number, rule_name))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings = scan_tree(root)
    if findings:
        for path, line_number, rule_name in findings:
            print(f"{path}:{line_number}: blocked by {rule_name}")
        print(f"public-safety: FAIL ({len(findings)} finding(s); contents withheld)")
        return 1
    print("public-safety: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
