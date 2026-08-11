# EXP-013 — Transactional expert composition

- **Schema**: strict-v1
- **Date**: 2026-08-11
- **Status**: complete
- **Compute**: C0
- **Data**: seven predeclared synthetic held-out requests and three synthetic expert packages

## Question

Can an unchanged deterministic kernel compose two compatible quarantined experts with
order-invariant behavior and unload rollback, while atomically rejecting a cross-package
knowledge-identifier conflict in either load order?

## Hypothesis

For the compatible pair, the unloaded baseline will score 0/4 and the composed candidate 4/4
on held-out targets, both will score 3/3 on held-out regressions, reversing package order will
not change responses, and unload will restore all four baseline target responses. For the
conflicting pair, the candidate will reject both orders without changing kernel state, while a
sequential last-write-wins baseline will return two distinct conflict-probe responses.

## Baseline

The behavioral baseline is the EXP-012 stable kernel with no expert loaded. The conflict
baseline validates each package independently and then writes its knowledge records in load
order, allowing later records to overwrite earlier records with the same identifier. The
candidate validates all packages and identifiers before one state assignment; it differs only
by an atomic cross-package collision check.

## Protocol

1. Lock three synthetic packages, four compatible-pair target requests, three unrelated
   regression requests, two reversed conflict orders, and one conflict probe before execution.
2. Measure the unloaded kernel, compose the compatible pair, measure the same seven requests,
   unload, and remeasure the four targets.
3. Repeat compatible composition in reversed order and require identical target and regression
   responses.
4. Attempt the conflicting pair in both orders. Require an explicit collision rejection and the
   original unloaded probe response after each attempt.
5. Run the same orders through the frozen last-write-wins baseline and require the two locked,
   different probe responses.
6. Repeat the complete trial in process and require identical decisions.
7. Run exactly one measured evaluator invocation, then run the repository tests, record and
   index validators, template validation at a pinned date, public-safety check, and staged diff
   review.

Only the Python standard library is permitted. Fixtures are synthetic. No model, external
service, private datum, training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match compatible target accuracy and absolute gain over the unloaded baseline;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with baseline;
- conflict rejections and unchanged-state counts across two load orders;
- distinct last-write-wins baseline outputs across the same conflict orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if compatible target accuracy moves from 0/4 to 4/4, both regression conditions
score 3/3 with zero drop, reversing compatible order changes no response, unload restores 4/4
baseline target responses, both conflict orders are rejected with 2/2 clean post-rejection
states, the last-write-wins baseline produces the two locked distinct outputs, repeated trials
are identical, the measured invocation finishes within 1 second, the fixture is below 16 KiB,
external calls remain zero, and all repository checks pass.

Stop after seven held-out requests, two conflict orders, two in-process trials, and one measured
evaluator invocation. Stop immediately on fixture inconsistency, partial candidate mutation,
budget overrun, network requirement, unexpected baseline mutation, or test failure.

## Results

For the compatible pair, the unloaded baseline scored 0/4 and the composed candidate scored
4/4 on held-out targets, an absolute accuracy gain of 1.0. Both conditions scored 3/3 on the
held-out regressions, for zero regression drop. Reversing the compatible package order changed
no target or regression response, and unload restored all 4 baseline target responses.

Both conflict orders were rejected with the kernel still returning its unloaded response, for
2/2 explicit rejections and 2/2 clean post-rejection states. The last-write-wins baseline
returned the two locked, distinct values according to which package was loaded last. Two
complete in-process trials were identical. The fixture was 4,326 bytes, the evaluator made 0
external calls, and the single measured invocation completed in 0.000573 seconds. Final checks
reported 89 passing tests, 14 valid experiment records, 14 index-to-record matches, a valid
public expert-package template at the pinned date, and zero public-safety findings.

## Interpretation

**Observation:** every predeclared behavioral, conflict, rollback, order, repeatability, size,
latency, and cost threshold passed. The candidate performed one state assignment only for the
compatible pair and retained unloaded state after each detected collision.

**Inference:** within this exact-key synthetic protocol, preflight collision detection removes
the tested last-write-wins load-order ambiguity while preserving compatible expert composition
and rollback. EXP-013 is the second successful run in the bounded EXP-012 through EXP-014
checkpoint. This is not evidence of semantic conflict resolution, concurrent transactions,
natural-language routing, or self-improvement.

## Limitations

The protocol is limited to exact string identifiers, tiny synthetic key-value packages, and a
deterministic lookup kernel. It cannot establish semantic conflict detection, natural-language
expert routing, concurrent atomicity, runtime safety, or useful behavior outside the locked
requests.

## Prior evidence

The primary [Retrieval-Augmented Generation paper](https://arxiv.org/abs/2005.11401) motivates
explicit non-parametric memory, and the primary [Switch Transformer paper](https://arxiv.org/abs/2101.03961)
motivates composing specialized expert capacity. Neither establishes the transactional
cross-package policy or the result of this synthetic protocol.

## Decision

`pass`
