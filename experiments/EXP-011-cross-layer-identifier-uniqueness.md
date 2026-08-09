# EXP-011 — Cross-layer identifier uniqueness

- **Schema**: strict-v1
- **Date**: 2026-08-09
- **Status**: complete
- **Compute**: C0
- **Data**: eight predeclared synthetic expert-layer identity cases

## Question

Can exact identifier collisions across knowledge, experience, skill, tool, and adapter layers
be rejected deterministically while the existing per-layer uniqueness contract accepts them?

## Hypothesis

On eight predeclared synthetic cases, the candidate will classify every case correctly with
zero false accepts. The existing per-layer-only baseline will falsely accept all five
cross-layer collision cases.

## Baseline

The baseline is the EXP-010 structural validator with its existing layer rule frozen: strings
must be non-empty and unique inside each layer list, but the same string may occur in two or
more different layers. The candidate adds exact, case-sensitive identifier uniqueness across
all five layer lists and leaves the other manifest checks unchanged.

## Protocol

1. Lock eight cases before evaluation: two valid disjoint or sparse layouts, five exact
   cross-layer collisions, and one intra-layer duplicate already rejected by the baseline.
2. Compare the frozen per-layer baseline and the cross-layer candidate against the same labels.
3. Require deterministic owner ordering by the five existing layer names.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run exactly one measured evaluator invocation, then run the repository tests, record and
   index validators, template validation at the pinned date, public-safety check, and staged
   diff review.

Only the Python standard library is permitted. No expert content is loaded or executed, and no
model or external service is called.

## Metrics

- candidate accuracy and false accepts across eight cases;
- per-layer-only baseline false accepts across six invalid cases;
- repeatability across two in-process evaluations;
- wall-clock latency for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- compute class C0 and external-call count as cost metrics;
- repository test, record-validation, index-validation, template-validation, and public-safety
  status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 8/8, candidate false accepts are zero, baseline false
accepts are at least 5, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, external calls remain zero, and all
repository checks pass.

Stop after eight cases and one measured evaluator invocation. Stop immediately on an unexpected
fixture error, budget overrun, network requirement, or test failure.

## Results

The candidate classified all 8 cases correctly and produced 0 false accepts among the 6
invalid cases. The per-layer-only baseline falsely accepted all 5 cross-layer collision cases
and rejected the intra-layer duplicate.

The two in-process candidate evaluations were identical. The fixture was 2,998 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.000722 seconds.
Final checks reported 75 passing tests, 12 valid experiment records, 12 index-to-record
matches, a valid public expert-package template at the pinned date, and zero public-safety
findings.

## Interpretation

**Observation:** every synthetic acceptance threshold passed. Exact collisions between two or
three distinct layer lists were rejected, both valid layouts were accepted, and the existing
intra-layer duplicate rejection was preserved.

**Inference:** exact cross-layer identifier uniqueness is suitable for promotion as a narrow
structural quarantine rule. This does not establish that differently spelled identifiers are
semantically distinct.

## Limitations

The fixture is synthetic and checks exact string equality only. It cannot establish semantic
identity, namespace design, case-folding policy, package usefulness, or runtime safety.

## Prior evidence

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.3)
defines `uniqueItems` for the elements of one array instance. This motivates retaining the
existing intra-layer check but does not establish Morpheus's proposed cross-layer policy.

## Decision

`pass`
