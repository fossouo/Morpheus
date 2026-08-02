# EXP-004 — Section-body validation

- **Schema**: strict-v1
- **Date**: 2026-08-02
- **Status**: complete
- **Compute**: C0
- **Data**: nine predeclared synthetic section-body cases

## Question

Can deterministic content checks reject empty and known placeholder section bodies that a
section-presence baseline accepts?

## Hypothesis

On nine predeclared synthetic cases, the candidate validator will classify every case
correctly with zero false accepts. A baseline that checks only that every required section
heading appears exactly once will falsely accept at least seven invalid records.

## Baseline

The baseline requires each `strict-v1` section heading exactly once but does not inspect its
body. This isolates the incremental value of checking section content from the existing title,
metadata, and section-presence contract.

## Protocol

1. Lock one valid record and eight single-fault mutations before evaluation.
2. Cover an empty body, a whitespace-only body, three short markers, and three unchanged
   prompts from the experiment template.
3. Compare the presence-only baseline with the content-aware candidate on the same labels.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run the repository unit tests, repository-level record validator, and public-safety check.

The candidate recognizes only empty bodies, four normalized short markers (`TBD`, `TODO`,
`pending`, and `N/A`), and exact normalized template prompts. It does not attempt general
semantic validation. Only the Python standard library is permitted; the evaluator makes no
network or model calls.

## Metrics

- candidate decision accuracy across nine cases;
- candidate false-accept count across eight invalid cases;
- presence-only baseline false-accept count across eight invalid cases;
- repeatability across two in-process evaluations;
- wall-clock duration for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- repository test, record-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 9/9, candidate false accepts are 0, baseline false
accepts are at least 7, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, and all repository checks pass.

Stop after nine cases and one measured evaluator invocation. Stop immediately on an
unexpected schema error, budget overrun, network requirement, or test failure.

## Results

The content-aware candidate classified all 9 cases correctly and produced 0 false accepts
among the 8 invalid records. The section-presence baseline falsely accepted all 8 invalid
records.

The two in-process candidate evaluations were identical. The fixture was 830 bytes, the
evaluator made 0 external calls, and the measured command completed in 0.003017 seconds. The
final repository checks reported 28 passing tests, 5 valid experiment records, and zero
public-safety findings.

## Interpretation

**Observation:** exact content checks rejected every predeclared empty, marker-only, and
unchanged-template body while the presence-only baseline accepted them.

**Inference:** for this deterministic fixture, requiring a non-placeholder body closes a
specific structural gap in `strict-v1`. It does not show that accepted prose is meaningful,
true, complete, or written before execution.

## Limitations

The fixture is synthetic. Exact marker detection cannot establish scientific quality,
truthfulness, completeness, or genuine temporal preregistration.

## Prior evidence

The [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
separates property presence from string length: omitting `minLength` behaves like a minimum of
zero. The candidate applies the narrower principle that a required experiment section also
needs a non-placeholder body; it is not a JSON Schema implementation.

## Decision

`pass`
