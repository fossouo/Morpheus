# EXP-007 — Experiment-index consistency

- **Schema**: strict-v1
- **Date**: 2026-08-05
- **Status**: complete
- **Compute**: C0
- **Data**: eight predeclared synthetic index and record cases

## Question

Can a deterministic consistency check reject missing, duplicate, orphaned, or mismatched
experiment-index entries that a row-count baseline accepts?

## Hypothesis

On eight predeclared synthetic cases, the candidate will classify every case correctly with
zero false accepts. A baseline that compares only the number of index rows and experiment
records will falsely accept at least five of the seven invalid cases.

## Baseline

The baseline accepts when the number of syntactically recognizable `EXP-NNN` index rows equals
the number of experiment files. It does not compare identifiers, uniqueness, status, or
verdict. The candidate additionally requires every experiment identifier to occur exactly once,
rejects index-only and file-only identifiers, and compares indexed status and verdict with the
corresponding record.

## Protocol

1. Lock one valid three-record index and seven single-fault mutations before evaluation.
2. Cover a missing index row, a same-count duplicate identifier, a same-count orphan
   replacement, a status mismatch, a verdict mismatch, an invalid indexed status, and a
   missing record file.
3. Compare the count-only baseline and candidate against the same labels.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run the repository tests, record validator, index validator, public-safety check, and staged
   diff review.

Only the Python standard library is permitted. The evaluator makes no network or model calls.

## Metrics

- candidate accuracy and false accepts across eight cases;
- count-only baseline false accepts across seven invalid cases;
- repeatability across two in-process evaluations;
- wall-clock duration for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- repository test, record-validation, index-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 8/8, candidate false accepts are zero, baseline false
accepts are at least 5, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, and all repository checks pass.

Stop after eight cases and one measured evaluator invocation. Stop immediately on an unexpected
schema error, budget overrun, network requirement, or test failure.

## Results

The candidate classified all 8 cases correctly and produced 0 false accepts among the 7
invalid cases. The count-only baseline falsely accepted 5 invalid cases: the same-count
duplicate identifier, orphan replacement, status mismatch, verdict mismatch, and invalid
indexed status.

The two in-process candidate evaluations were identical. The fixture was 736 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.000957
seconds.

The first direct index-validator integration check exposed a missing repository-root import
path that unit-test imports did not expose. That invocation stopped before validation; the
path was corrected without rerunning the measured evaluator. Final checks reported 49 passing
tests, 8 valid experiment records, 8 index-to-record matches, and zero public-safety findings.

## Interpretation

**Observation:** every synthetic acceptance threshold passed, including the deliberately
same-count faults that the baseline could not distinguish.

**Inference:** the candidate is suitable for repository promotion as a structural consistency
gate. This does not show that indexed or recorded claims are truthful.

## Limitations

The fixture is synthetic and limited to the repository's four-column index contract. It cannot
establish scientific quality, truthful metadata, or genuine temporal preregistration.

## Prior evidence

The [GitHub Flavored Markdown specification](https://github.github.com/gfm/#tables-extension-)
defines a table as a header, delimiter row, and data rows whose cells are separated by pipes.
The candidate applies a narrower four-column contract to this repository's experiment index;
it is not a general GFM parser.

## Decision

`pass`
