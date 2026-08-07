# EXP-009 — Expert-package manifest contract

- **Schema**: strict-v1
- **Date**: 2026-08-07
- **Status**: complete
- **Compute**: C0
- **Data**: ten predeclared synthetic expert-package manifest cases

## Question

Can a deterministic structural contract reject expert-package manifests that omit isolation,
evidence, expiry, quarantine, or rollback information while a required-key-only baseline accepts
them?

## Hypothesis

On ten predeclared synthetic cases, the candidate will classify every case correctly with zero
false accepts. The required-key-only baseline will falsely accept all nine invalid nested or
unexpected-field cases.

## Baseline

The baseline accepts any JSON object containing all nine required top-level keys. It does not
inspect nested structure, values, quarantine state, rollback, held-out regression tests, or
unexpected fields. The candidate validates those structural constraints without executing or
loading any package content.

## Protocol

1. Lock one valid minimal manifest and nine single-fault mutations before evaluation.
2. Cover an empty exclusion scope, empty provenance, missing held-out regression coverage,
   invalid expiry date, premature promotion, missing rollback, merged layer structure,
   malformed version, and an unexpected executable field.
3. Compare the key-only baseline and candidate against the same labels.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run exactly one measured evaluator invocation, then run the repository tests, record and
   index validators, public-safety check, and staged diff review.

Only the Python standard library is permitted. No expert is loaded, no model is called, and no
manifest action is executed.

## Metrics

- candidate accuracy and false accepts across ten cases;
- key-only baseline false accepts across nine invalid cases;
- repeatability across two in-process evaluations;
- wall-clock latency for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- compute class C0 and external-call count as cost metrics;
- repository test, record-validation, index-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 10/10, candidate false accepts are zero, baseline false
accepts are at least 9, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, external calls remain zero, and all
repository checks pass.

Stop after ten cases and one measured evaluator invocation. Stop immediately on an unexpected
schema error, budget overrun, network requirement, or test failure.

## Results

The candidate classified all 10 cases correctly and produced 0 false accepts among the 9
invalid cases. The required-key-only baseline falsely accepted all 9 invalid cases.

The two in-process candidate evaluations were identical. The fixture was 2,090 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.000630
seconds. Final checks reported 63 passing tests, 10 valid experiment records, 10
index-to-record matches, a valid public expert-package template, and zero public-safety
findings.

## Interpretation

**Observation:** every synthetic acceptance threshold passed. Each predeclared nested fault and
the unexpected top-level field was rejected while the valid minimal manifest was accepted.

**Inference:** the candidate is suitable for promotion as a narrow, quarantine-only structural
contract and public template. This does not show that an expert is useful, safe, truthful,
compatible, or loadable.

## Limitations

The fixture is synthetic. The candidate checks structure and a quarantine-only initial state;
it does not verify source truth, test quality, expiry policy, signatures, artifact integrity,
runtime compatibility, promotion evidence, or rollback execution.

## Prior evidence

[LoRA](https://arxiv.org/abs/2106.09685) demonstrates specialization through separate low-rank
matrices while keeping pretrained weights frozen. [Switch Transformers](https://arxiv.org/abs/2101.03961)
demonstrates input-dependent sparse expert selection. These results motivate keeping optional
adapters and expert identity explicit, but they do not establish this manifest contract.

## Decision

`pass`
