# EXP-031 — Stable-validator-native expert integration

- **Schema**: strict-v1
- **Date**: 2026-08-31
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned synthetic manifest, routing, rejection, and rollback fixture

## Question

Can expert composition replace the quarantined v2 validation path with the promoted stable
validator without changing any locked routing, rejection, or rollback behavior?

## Hypothesis

The stable-validator-native candidate will exactly match the EXP-030 promotion-candidate
baseline over the complete integration trial at pinned date `2026-08-31`; preserve 8/8 target
outputs, 3/3 regressions, both package orders, and both probe pairs; reject all eight ordered
invalid compositions with eight clean states; and restore all 16 post-unload responses.

## Baseline

The baseline is EXP-030's `PromotionCandidateManifestKernel`, which gates EXP-027 composition
through the frozen pre-promotion candidate and then delegates to EXP-027's quarantined path.
The candidate calls the promoted `validate_manifest` function directly on each v2 manifest,
projects an accepted manifest to the locked v1 router input, and does not call the quarantined
`candidate_errors` or `promotion_candidate_errors` functions.

## Protocol

1. Pin the complete EXP-027 integration fixture by SHA-256 and replace only its reference date
   with the explicit `2026-08-31` date carried by this experiment fixture.
2. Run the complete integration trial through the EXP-030 baseline and stable-native candidate,
   covering eight held-out targets, three regressions, two package orders, two probes, four
   invalid mutations in both orders, clean-state checks, and 16 unload comparisons.
3. Require exact equality between the complete baseline and candidate trials and score the
   candidate independently against the locked outputs and error strings.
4. Repeat the paired trial in process and require identical outputs.
5. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned public-template validation, public-safety checks, and staged-diff review.

Only the Python standard library and repository-owned synthetic fixtures are permitted. No
stable validator, public template, historical evaluator, model, private datum, external service,
training, network call, package migration, or production runtime may change.

## Metrics

- exact complete-trial parity between the promotion-candidate baseline and stable-native path;
- exact target and regression parity and correctness over eight and three held-out cases;
- package-order invariance and two probe-pair matches;
- eight invalid-composition rejections, eight clean states, and 16 rollback comparisons;
- repeatability across two paired in-process trials;
- combined fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if the complete trials are exactly equal; target parity and correctness are 8/8;
regression parity and correctness are 3/3; both orders agree; both probe pairs match; all eight
invalid compositions are rejected with eight clean states; rollback matches 16/16; both paired
trials repeat; combined fixtures remain below 16 KiB; evaluation finishes below one second with
zero external calls; and every repository check passes.

Stop after eight targets, three regressions, two orders, two probes, four mutations in both
orders, 16 unload comparisons, two paired in-process trials, and one measured invocation. Stop
immediately on a parity gap, false accept, partial installation, rollback mismatch, source-hash
drift, budget overrun, wall-clock or network requirement, stable-contract mutation, public-
template mutation, or repository-test failure. Do not patch and rerun a failed measured protocol
in this experiment.

## Results

The stable-validator-native candidate exactly matched the EXP-030 promotion-candidate baseline
over the complete paired trial. Target parity and correctness were 8/8, regression parity and
correctness were 3/3, both package orders agreed, and both probe pairs matched.

All eight ordered invalid compositions were rejected with their exact locked errors and left
eight clean states. Unload restored all 16 baseline target responses. The two paired in-process
trials were identical. Combined fixture size was 1,745 bytes, the evaluator made zero external
calls, and its single measured invocation completed in 0.011847 seconds.

## Interpretation

**Observation:** within the locked synthetic configuration, direct stable v2 validation produced
the same targets, regressions, probe results, invalid-composition errors, clean states, package-
order behavior, and unload responses as the frozen promotion-candidate path.

**Inference:** the promoted stable validator can replace the quarantined validation dependency
inside this exact expert-composition harness without changing its tested behavior. This removes a
quarantined validation dependency from the integration path; it is not a new behavioral-
capability result, a public-template migration, or evidence of self-improvement.

## Limitations

The protocol can test only deterministic validation-path substitution, exact synthetic routing,
transactional rejection, and unload behavior. It cannot establish declaration authenticity,
trusted clocks, authorization correctness, semantic routing, scalable performance, runtime
safety, natural-language capability, or self-improvement.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
distinguishes structural validation from application semantics, and the primary [TUF
specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
motivates using one fixed time throughout an update workflow. Neither source defines Morpheus's
manifest projection, routing policy, transaction boundary, or synthetic expectations.

## Decision

`pass`
