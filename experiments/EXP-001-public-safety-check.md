# EXP-001 — Public-safety boundary checker

- **Date**: 2026-07-30
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic strings only

## Hypothesis

A deterministic repository check can block common accidental disclosures before a
public commit.

## Protocol

Run:

```bash
python3 -m unittest discover -s tests
python3 scripts/check_public_safety.py .
```

Synthetic tests cover private IPv4 ranges, local absolute paths, common secret formats,
device identifiers, raw topology vocabulary, and explicitly allowed documentation
examples.

## Acceptance criteria

- All unsafe synthetic fixtures are detected.
- The repository itself produces zero findings.
- No network access is required.

## Result

Seven deterministic tests passed, and the checker reported zero findings in the initial
repository tree.

**Verdict: pass.**

## Publication rule

Only the aggregate pass/fail status is published. The checker must never print the
contents of a detected secret.
