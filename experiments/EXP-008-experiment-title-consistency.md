# EXP-008 — Experiment-title consistency

- **Schema**: strict-v1
- **Date**: 2026-08-06
- **Status**: complete
- **Compute**: C0
- **Data**: seven predeclared synthetic index-title and record-heading cases

## Question

Can a deterministic index check reject title and record-heading inconsistencies that the
EXP-007 coverage-and-metadata contract accepts?

## Hypothesis

On seven predeclared synthetic cases, the candidate will classify every case correctly with
zero false accepts. The EXP-007 baseline, frozen with title checking disabled, will falsely
accept all five invalid title or heading cases.

## Baseline

The baseline is the promoted EXP-007 consistency check for index coverage, identifier
uniqueness, status, and verdict, invoked with its new title check disabled. The candidate adds
an exact comparison between the index title and the single record heading after decoding the
escaped-pipe form supported by the repository's table parser.

## Protocol

1. Lock two valid cases and five single-fault invalid cases before evaluation.
2. Cover a plain matching title, a matching GFM escaped-pipe title, a title mismatch, a record
   heading identifier mismatch, and missing, duplicate, and empty record titles.
3. Compare the frozen EXP-007 baseline and candidate against the same labels.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run exactly one measured evaluator invocation, then run the repository tests, record
   validator, index validator, public-safety check, and staged diff review.

Only the Python standard library is permitted. The evaluator makes no network or model calls.

## Metrics

- candidate accuracy and false accepts across seven cases;
- EXP-007 baseline false accepts across five invalid cases;
- repeatability across two in-process evaluations;
- wall-clock latency for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- compute class C0 and external-call count as cost metrics;
- repository test, record-validation, index-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 7/7, candidate false accepts are zero, baseline false
accepts are at least 5, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, external calls remain zero, and all
repository checks pass.

Stop after seven cases and one measured evaluator invocation. Stop immediately on an unexpected
schema error, budget overrun, network requirement, or test failure.

## Results

The candidate classified all 7 cases correctly and produced 0 false accepts among the 5
invalid cases. The frozen EXP-007 baseline falsely accepted all 5 invalid title or heading
cases.

The two in-process candidate evaluations were identical. The fixture was 877 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.000629
seconds. Final checks reported 56 passing tests, 9 valid experiment records, 9
index-to-record matches, and zero public-safety findings.

## Interpretation

**Observation:** every synthetic acceptance threshold passed, including the escaped-pipe
equivalence and the five structural or equality faults ignored by the baseline.

**Inference:** the candidate is suitable for repository promotion as a narrow title-consistency
extension. This does not show that titles are semantically meaningful or that the records are
truthful.

## Limitations

The fixture is synthetic and exercises only the repository's exact plain-text heading contract
plus escaped pipes in table cells. It is not a general GFM inline parser and cannot establish
the truth or scientific quality of an experiment title.

## Prior evidence

The [GitHub Flavored Markdown specification](https://github.github.com/gfm/#example-200)
demonstrates that a pipe can appear inside a table cell when escaped with a backslash. The
candidate implements only that narrow rendering equivalence.

## Decision

`pass`
