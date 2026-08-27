# EXP-027 — Manifest-integrated root routing

- **Schema**: strict-v1
- **Date**: 2026-08-27
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic expert manifests, packages, scope requests, and repository-owned v1 fixtures

## Question

Can package-owned roots move from EXP-025 sidecar entries into opt-in v2 manifests without
changing the locked routing behavior, while invalid manifests are rejected before installation
and historical v1 validation remains unchanged?

## Hypothesis

The manifest-integrated candidate will exactly match the frozen EXP-025 sidecar baseline on all
eight held-out targets, three regressions, two probes, and both package orders; restore all 16
post-unload target responses; reject four invalid manifest mutations in both orders with eight
clean states; and preserve exact validation parity on four historical v1 sources.

## Baseline

The baseline is the unchanged EXP-025 `PackageRootOwnershipKernel` over its SHA-256-pinned source
fixture, where each root is supplied beside its v1 package. The candidate receives the same two
packages and data, moves only that root into an opt-in v2 manifest, applies EXP-026's quarantined
contract plus pinned-date expiry, projects the accepted manifest to v1, and reuses the unchanged
EXP-025 router. This tests integration parity rather than a routing-policy improvement.

## Protocol

1. Pin the complete EXP-025 routing fixture and EXP-026 manifest fixture by SHA-256.
2. Deterministically convert the two valid sidecar packages into opt-in v2 manifests by moving
   each sidecar root into its package manifest without changing scopes, records, or test IDs.
3. Compose baseline and candidate in fixture order and reverse order; compare eight held-out
   targets, three regressions, the cross-root and absent probes, and unload responses.
4. Apply four locked mutations: missing root, wildcard root, literal include/root mismatch, and
   expiry before the pinned date. Test both package orders and require exact rejection before any
   observable routing state is installed.
5. Replay EXP-026's four repository-owned v1 sources and require exact error-list parity with the
   unchanged stable validator.
6. Repeat the complete trial in process, then run exactly one measured evaluator invocation,
   followed by repository tests, record and index validators, pinned expert-template validation,
   public-safety checks, and staged-diff review.

Only the Python standard library and repository-owned synthetic fixtures are permitted. No
stable validator, template, historical evaluator, model, external service, private datum,
training, network call, or production runtime is allowed.

## Metrics

- exact target-output parity and locked-answer accuracy across eight held-out cases;
- exact regression parity and accuracy across three cases;
- package-order invariance, probe parity, and 16 post-unload comparisons;
- exact invalid-manifest rejections and clean-state counts across eight ordered attempts;
- exact historical v1 error-list parity and acceptance across four sources;
- repeatability across two in-process trials;
- fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if target parity and candidate accuracy are 8/8; regression parity and accuracy are
3/3; both orders agree; both probe pairs match; unload restores 16/16 responses; all eight
ordered invalid manifests produce their exact locked errors and clean states; all four historical
v1 sources remain accepted with exact error-list parity; both trials match; the delta fixture is
below 16 KiB; evaluation finishes below one second with zero external calls; and every repository
check passes.

Stop after eight targets, three regressions, two probes, two orders, four mutations in both
orders, four historical sources, two in-process trials, and one measured invocation. Stop
immediately on a parity gap, partial installation, v1 validation change, order dependence,
rollback mismatch, source-hash drift, budget overrun, network requirement, stable-contract
mutation, or repository-test failure. Do not patch and rerun a failed measured protocol in this
experiment.

## Results

The candidate exactly matched the frozen sidecar baseline on all eight held-out targets and all
three regressions. It also produced every locked target and regression answer, matched both
cross-root and absent-scope probes in both package orders, remained order invariant, and restored
all 16 post-unload target responses.

All four invalid manifest mutations were rejected with their exact locked errors in both package
orders, for 8/8 rejections and 8/8 clean post-rejection states. The missing, wildcard, and literal
root-mismatch cases were rejected by the quarantined structural contract; the expired case was
rejected by the pinned-date stable expiry rule after projection. All four historical v1 sources
remained accepted with exact error-list parity. The two in-process trials were identical.

The delta fixture occupied 1,460 bytes, the evaluator made zero external calls, and its single
measured invocation completed in 0.005942 seconds.

## Interpretation

**Observation:** within the locked synthetic configuration, moving package-owned roots from the
EXP-025 sidecar into opt-in v2 manifests caused no output difference across targets, regressions,
probes, orders, or rollback. Invalid manifests were rejected before observable routing state was
installed, while the checked v1 validation outcomes were unchanged.

**Inference:** the separately demonstrated EXP-025 routing behavior and EXP-026 structural
contract can be composed behind a manifest-to-v1 projection without changing the tested behavior.
This supports a later stable-promotion experiment, but this parity result alone does not justify
changing the public template or validator.

## Limitations

The protocol can test only structural integration and exact synthetic routing parity. It cannot
establish declaration trust, authorization correctness, semantic routing, migration safety,
concurrent atomicity, scalable performance, runtime safety, natural-language capability, or
self-improvement.

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines hierarchical paths as slash-separated segments and motivates the narrow root boundary.
The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
motivates separating required properties from value constraints. Neither source defines
Morpheus's root ownership, manifest migration, routing, transaction, or synthetic expectations.

## Decision

`pass`
