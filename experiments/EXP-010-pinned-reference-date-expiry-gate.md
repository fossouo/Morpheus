# EXP-010 — Pinned reference-date expiry gate

- **Schema**: strict-v1
- **Date**: 2026-08-08
- **Status**: complete
- **Compute**: C0
- **Data**: seven predeclared synthetic expert-package expiry cases

## Question

Can an explicit, pinned reference date reject expired expert-package manifests while the
existing syntax-only validator accepts them?

## Hypothesis

On seven predeclared synthetic cases, the candidate will classify every case correctly with
zero false accepts. The syntax-only baseline will falsely accept both well-formed but expired
cases.

## Baseline

The baseline is the EXP-009 structural validator without a reference date. It checks that
`expires_on` is a canonical calendar date but cannot distinguish a future date from an expired
one. The candidate applies the same structural checks and additionally compares `expires_on`
with the fixture's explicit reference date.

## Protocol

1. Pin one reference date in the fixture before evaluation.
2. Lock seven cases: future date, same-day date, previous-day date, year-old date, invalid
   calendar date, non-canonical compact date, and non-string value.
3. Define the package's date-only policy as inclusive: `expires_on` is valid on the reference
   date and expired only when it is earlier.
4. Compare the syntax-only baseline and date-aware candidate against the same labels.
5. Repeat the candidate evaluation in-process and require identical decisions.
6. Run exactly one measured evaluator invocation, then run the repository tests, record and
   index validators, template validation with the same pinned date, public-safety check, and
   staged diff review.

Only the Python standard library is permitted. The evaluator receives the reference date as
data and must not read a wall clock. No expert content is loaded or executed.

## Metrics

- candidate accuracy and false accepts across seven cases;
- syntax-only baseline false accepts across five invalid cases;
- repeatability across two in-process evaluations;
- wall-clock latency for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- compute class C0 and external-call count as cost metrics;
- repository test, record-validation, index-validation, template-validation, and public-safety
  status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 7/7, candidate false accepts are zero, baseline false
accepts are at least 2, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, external calls remain zero, and all
repository checks pass.

Stop after seven cases and one measured evaluator invocation. Stop immediately on an unexpected
fixture error, wall-clock dependency, budget overrun, network requirement, or test failure.

## Results

The candidate classified all 7 cases correctly and produced 0 false accepts among the 5
invalid cases. The syntax-only baseline falsely accepted both well-formed expired cases.

The two in-process candidate evaluations were identical. The fixture was 1,428 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.000597 seconds.
Final checks reported 69 passing tests, 11 valid experiment records, 11 index-to-record
matches, a valid public template at the pinned reference date, and zero public-safety findings.

## Interpretation

**Observation:** every synthetic evaluation threshold passed. A future date and the pinned
same-day boundary were accepted; both earlier dates and all three structural date faults were
rejected.

**Inference:** the explicit reference-date comparison is suitable for promotion as a narrow
date-only quarantine gate. This does not establish that the supplied reference date is correct
or trustworthy.

## Limitations

The fixture is synthetic and the policy is date-only. It does not establish clock trust,
timestamp precision, signature validity, artifact integrity, runtime compatibility, or package
usefulness.

## Prior evidence

[The Update Framework specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
fixes one time at the start of an update workflow and evaluates expiration against that value.
This motivates an explicit reference value but does not establish Morpheus's inclusive,
date-only policy. The Python standard library documents canonical date output and date
comparison in [`datetime.date`](https://docs.python.org/3/library/datetime.html#datetime.date).

## Decision

`pass`
