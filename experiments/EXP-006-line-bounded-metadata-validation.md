# EXP-006 — Line-bounded metadata validation

- **Schema**: strict-v1
- **Date**: 2026-08-04
- **Status**: complete
- **Compute**: C0
- **Data**: sixteen predeclared synthetic metadata-line cases

## Question

Can a line-bounded parser reject blank values across all required metadata fields and exact
`Data` placeholders without changing the decisions for a valid record?

## Hypothesis

On sixteen predeclared synthetic cases, the candidate will classify every case correctly,
produce zero false accepts, and capture no later-line content as a blank metadata value. The
prior contract will falsely accept at least seven invalid records and will capture non-empty
later-line content in all ten empty or whitespace-only field cases.

## Baseline

The baseline is the validator used by EXP-005: its metadata expression permits `\s*` around
values and has no stable placeholder-value rule. The candidate changes only metadata parsing
to explicit same-line characters, adds exact normalized placeholders for `Data`, and preserves
the existing title, filename, type, section, and decision checks.

## Protocol

1. Lock one valid record, empty and whitespace-only mutations for each of the five required
   fields, and five exact `Data` placeholder mutations before evaluation.
2. Evaluate baseline and candidate decisions on the same labels.
3. For the ten blank cases, count whether each parser captures non-empty content for the
   mutated field; such a capture is a line-spill error.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run the repository tests, record validator, public-safety check, and staged-diff review.

Only the Python standard library is permitted. The evaluator makes no network or model calls.

## Metrics

- candidate accuracy and false accepts across sixteen cases;
- baseline false accepts across fifteen invalid cases;
- candidate and baseline line-spill counts across ten blank cases;
- repeatability across two in-process evaluations;
- wall-clock duration for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- repository test, record-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 16/16, candidate false accepts and line spills are zero,
baseline false accepts are at least 7, baseline line spills are at least 10, repeated decisions
are identical, one evaluator invocation finishes within 1 second, the fixture is smaller than
16 KiB, and all repository checks pass.

Stop after sixteen cases and one measured evaluator invocation. Stop immediately on an
unexpected schema error, budget overrun, network requirement, or test failure.

## Results

The candidate classified all 16 cases correctly with 0 false accepts and 0 line spills. The
baseline falsely accepted 7 of the 15 invalid cases and captured non-empty later-line content
for all 10 empty or whitespace-only field mutations.

The two in-process candidate evaluations were identical. The fixture was 1,332 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.009369
seconds. Final repository checks reported 42 passing tests, 7 valid experiment records, and
zero public-safety findings.

## Interpretation

**Observation:** every predeclared acceptance threshold passed. The explicit `[ \t]*` and
`[^\r\n]*?` classes kept each captured value on its metadata line, and exact normalized `Data`
markers were rejected.

**Inference:** the candidate is suitable for promotion as the stable `strict-v1` metadata
parser and structural placeholder rule. This does not show that an accepted `Data` description
is accurate or adequate.

## Limitations

The fixture is synthetic and tests only structural line isolation plus five exact `Data`
markers. It cannot establish truthfulness, completeness, scientific quality, or genuine
temporal preregistration.

## Prior evidence

The [Python `re` documentation](https://docs.python.org/3/library/re.html) specifies that
`\s` includes newline characters and that, under `MULTILINE`, `$` matches before a newline.
The candidate therefore uses explicit horizontal whitespace and non-newline value classes;
this source supports the parser mechanism, not the experiment outcome.

## Decision

`pass`
