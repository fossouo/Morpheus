# EXP-003 — Machine-checkable experiment record

- **Schema**: strict-v1
- **Date**: 2026-08-01
- **Status**: complete
- **Compute**: C0
- **Data**: seven predeclared synthetic record cases

## Question

Can a deterministic structural validator reject malformed strict experiment records that
a title-only baseline accepts?

## Hypothesis

On seven predeclared synthetic cases, the strict validator will classify every case
correctly with zero false accepts. A baseline that checks only the title and filename will
falsely accept at least four malformed records.

## Baseline

The baseline checks only that the document begins with an `EXP-NNN` title whose identifier
matches the filename. It does not inspect metadata, sections, status, or decision values.

The candidate validator applies an opt-in `strict-v1` contract. Legacy records remain
readable but are not silently represented as having been preregistered under this contract.

## Protocol

1. Lock one valid complete record and six single-fault mutations before evaluation.
2. Cover a missing hypothesis, missing baseline, duplicated metrics section, invalid status,
   mismatched identifier, and missing decision.
3. Evaluate the title-only baseline and strict validator against the same expected labels.
4. Repeat the strict evaluation in-process and require byte-identical decisions.
5. Run the repository unit tests, repository-level record validator, and public-safety check.

Only the Python standard library is permitted. The evaluator makes no network or model
calls.

## Metrics

- strict decision accuracy across seven cases;
- strict false-accept count across six invalid cases;
- title-only baseline false-accept count across six invalid cases;
- repeatability across two in-process evaluations;
- wall-clock duration for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- repository test, record-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if:

- strict accuracy is 7/7;
- strict false accepts are 0;
- title-only baseline false accepts are at least 4;
- repeated strict decisions are identical;
- one evaluator invocation finishes within 1 second;
- the fixture is smaller than 16 KiB;
- all repository tests, record validation, and public-safety checks pass.

Stop after seven cases and one measured evaluator invocation. Stop immediately on an
unexpected schema error, budget overrun, network requirement, or test failure.

## Results

The strict validator classified all 7 cases correctly and produced 0 false accepts among
the 6 invalid records. The title-only baseline falsely accepted 5 invalid records: the cases
with a missing hypothesis, missing baseline, duplicated metrics section, invalid status, and
missing decision.

The two in-process strict evaluations were identical. The fixture was 634 bytes, the
evaluator made 0 external calls, and the measured command completed in 0.000657 seconds.
The final repository checks reported 21 passing tests, 4 valid experiment records, and zero
public-safety findings.

## Interpretation

**Observation:** the strict contract detected every predeclared single-fault mutation while
the title-only baseline missed five structural faults.

**Inference:** for this deterministic fixture, opt-in validation makes required metadata and
sections machine-checkable and prevents omissions that title recognition alone permits. The
validator cannot establish scientific quality, truthful content, or whether a claim was
genuinely fixed before execution.

## Limitations

The fixture is synthetic and checks document structure rather than experimental truth. The
contract is opt-in so that historical records are not retrospectively presented as strict
preregistrations.

## Prior evidence

The [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines required properties as structural assertions. `strict-v1` applies the narrower idea
of required fields to Markdown experiment records; it is not a JSON Schema implementation.

## Decision

`pass`
