# EXP-028 — Stable expert-manifest v2 promotion

- **Schema**: strict-v1
- **Date**: 2026-08-28
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic expert manifests, routing cases, and repository-owned v1 fixtures

## Question

Can the opt-in `expert-package-v2` root contract move into the stable validator while exactly
preserving the quarantined structural decisions, EXP-027 routing behavior, transactional
rejection, rollback, and historical v1 validation on the locked fixtures?

## Hypothesis

The stable candidate will exactly match EXP-026 on all ten structural cases and four historical
v1 sources, exactly match the complete EXP-027 trial, preserve 8/8 targets, 3/3 regressions and
16/16 unload responses, and reject all eight ordered invalid compositions with clean state.

## Baseline

The baseline is the frozen quarantined v2 contract from EXP-026 and the manifest-integrated
kernel from EXP-027. The candidate changes only the stable manifest validator to dispatch by
the explicit v1 or v2 schema; valid v2 packages are then passed to the unchanged EXP-027 kernel.
The public template remains v1, so validator promotion is not coupled to package migration.

## Protocol

1. Pin the complete EXP-026 structural fixture and EXP-027 integration fixture by SHA-256.
2. Replay all ten v2 structural cases and require exact error-list equality between the
   quarantined and stable validators.
3. Replay all four repository-owned valid v1 sources at the pinned date `2026-08-28` and require
   acceptance plus exact error-list equality.
4. Gate the unchanged EXP-027 kernel through the stable validator, then replay its eight held-out
   targets, three regressions, two package orders, probes, four invalid mutations in both orders,
   clean-state checks, and unload comparisons.
5. Require the complete stable-gated trial to equal the frozen quarantined trial exactly and
   repeat the complete trial in process.
6. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned public-template validation, public-safety checks, and staged-diff review.

Only the Python standard library and repository-owned synthetic fixtures are permitted. No model,
external service, private datum, training, network call, package migration, or production runtime
is allowed.

## Metrics

- exact v2 decision and error-list parity across ten structural cases;
- exact v1 acceptance and error-list parity across four historical sources;
- exact target and regression parity across eight and three held-out cases;
- eight invalid-composition rejections, eight clean states, and 16 unload comparisons;
- complete trial equality and repeatability across two in-process trials;
- fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if v2 parity and classification are 10/10 with zero false accepts; v1 acceptance and
parity are 4/4; target and regression parity are 8/8 and 3/3; all eight invalid compositions are
rejected with eight clean states; rollback is 16/16; the stable and quarantined complete trials
are identical; both in-process trials match; the delta fixture is below 16 KiB; evaluation
finishes below one second with zero external calls; and every repository check passes.

Stop after ten structural cases, four v1 sources, the locked EXP-027 trial, two in-process trials,
and one measured invocation. Stop immediately on any parity gap, false accept, partial install,
rollback mismatch, source-hash drift, budget overrun, network requirement, template migration, or
repository-test failure. Do not patch and rerun a failed measured protocol in this experiment.

## Results

The promotion candidate exactly matched the quarantined EXP-026 contract on all ten structural
cases, classified 10/10 correctly, and made zero false accepts. The candidate-gated integration
also preserved 8/8 target outputs, 3/3 regressions, all eight invalid-composition rejections and
clean states, 16/16 unload responses, complete EXP-027 trial equality, and repeatability.

The run failed the historical v1 criterion. Only 3/4 sources were accepted with exact parity at
the promotion date. Diagnostic inspection after the stop identified the locked
`expiry-contract-base` source, whose `expires_on` value is `2026-08-09`; it is structurally valid
but expired at the pinned `2026-08-28` date. The earlier quarantine comparison omitted a reference
date and therefore measured structural parity rather than current-date acceptance.

The delta fixture occupied 444 bytes, the evaluator made zero external calls, and its single
measured invocation completed in 0.012912 seconds. The stable validator and public v1 template
were not promoted or changed.

## Interpretation

**Observation:** the candidate reproduced all locked v2 structural and routing behavior, but the
promotion protocol's 4/4 current-date v1 requirement failed at 3/4 because one historical source
had legitimately expired.

**Inference:** the historical corpus currently mixes structural compatibility examples with
time-sensitive acceptance expectations. That ambiguity must be resolved in a separately
preregistered temporal-corpus experiment before stable v2 promotion can be reconsidered. The
otherwise exact synthetic parity does not override the declared stop criterion.

## Limitations

The protocol is limited to structural validation and exact synthetic replay. It cannot establish
declaration trust, authorization correctness, semantic routing, migration safety, concurrent
atomicity, scalable performance, runtime safety, natural-language capability, or self-improvement.

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines hierarchical paths as slash-separated segments and motivates the narrow root boundary.
The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
motivates explicit structural constraints and schema-version dispatch. Neither source defines
Morpheus's root ownership, wildcard policy, compatibility expectations, or synthetic labels.

## Decision

`fail`
