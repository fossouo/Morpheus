# EXP-015 — Exact scope expert routing

- **Schema**: strict-v1
- **Date**: 2026-08-13
- **Status**: complete
- **Compute**: C0
- **Data**: seven predeclared synthetic held-out requests and three synthetic expert packages

## Question

Can an unchanged deterministic kernel select a quarantined expert from an exact declared scope,
without a caller-supplied package identifier, while rejecting overlapping and absent scopes,
preserving unrelated behavior, order invariance, and unload rollback?

## Hypothesis

The EXP-014 explicit-qualification baseline will return `package-id-required` for all four
scope-only targets and score 0/4. The candidate will score 4/4, preserve 3/3 regressions, return
the same responses in both compatible package orders, reject both overlapping-scope orders before
state assignment, reject one absent-scope probe in both orders, and restore all four unloaded
responses after unload.

## Baseline

The baseline retains EXP-014's requirement that the caller name a package. It validates and loads
the same compatible packages but cannot choose one from a request containing only `scope` and
`local_id`. The candidate differs only by constructing an exact map from each manifest's declared
`scope.include` strings to package identity during transactional composition.

## Protocol

1. Lock three synthetic packages, four scope-only target requests, three unrelated regression
   requests, two compatible package orders, two reversed overlapping-scope orders, and one absent
   scope before execution.
2. Load the two compatible packages in both orders. Measure the explicit-qualification baseline
   on the four targets, then measure candidate targets and regressions.
3. Require identical candidate responses across compatible orders and explicit rejection of the
   absent scope in both orders.
4. Attempt both overlapping-scope package orders. Require an explicit ambiguity rejection before
   any state assignment.
5. Unload the candidate and remeasure the four targets.
6. Repeat the complete trial in process and require byte-for-byte identical decisions.
7. Run exactly one measured evaluator invocation, then run repository tests, record and index
   validators, template validation at a pinned date, public-safety check, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Matching is exact and
case-sensitive. No model, external service, private datum, training procedure, network call, or
production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over explicit qualification;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with baseline;
- overlapping-scope rejections and unchanged-state counts across two load orders;
- absent-scope rejections across two compatible load orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline policy produces all four locked `package-id-required` responses and
scores 0/4 against target values, the candidate scores 4/4 for an absolute gain of 1.0, both
regression conditions score 3/3 with zero drop, reversing compatible order changes no response,
both overlapping-scope orders are rejected with 2/2 clean states, the absent scope is rejected in
both compatible orders, unload restores 4/4 unloaded responses, repeated trials are identical,
the measured invocation finishes within 1 second, the fixture is below 16 KiB, external calls
remain zero, and all repository checks pass.

Stop after seven held-out requests, two compatible orders, two conflict orders, two in-process
trials, and one measured evaluator invocation. Stop immediately on fixture inconsistency,
ambiguous selection, partial state mutation, budget overrun, network requirement, baseline
mutation, or test failure.

## Results

The explicit-qualification baseline produced all four locked `package-id-required` responses and
scored 0/4 against the target values. The exact-scope candidate scored 4/4, an absolute target
accuracy gain of 1.0. Both unloaded and loaded conditions scored 3/3 on the held-out regressions,
for zero regression drop.

Reversing compatible package order changed no target or regression response. Both overlapping-
scope orders were rejected before state assignment with 2/2 clean states, and the absent scope was
rejected in both compatible orders. Unload restored all 4 unloaded target responses. Two complete
in-process trials were identical. The fixture was 4,950 bytes, the evaluator made 0 external calls,
and the single measured invocation completed in 0.000487 seconds.

Final checks reported 103 passing tests, 16 valid experiment records, 16 index-to-record matches,
a valid public expert-package template at the pinned date, and zero public-safety findings.

## Interpretation

**Observation:** every predeclared behavioral, regression, ambiguity, absence, order, rollback,
repeatability, size, latency, and cost threshold passed.

**Inference:** within this exact-label synthetic protocol, declared-scope routing removes the
tested need for callers to know package identity while remaining fail-closed on the two tested
selection failures. This is a measured routing behavior relative to EXP-014's explicit interface,
not evidence of semantic expert discovery, natural-language routing, or self-improvement.

## Limitations

The protocol is limited to exact, caller-supplied synthetic scope labels, exact string identifiers,
tiny key-value packages, and a deterministic lookup kernel. It cannot establish semantic intent
classification, learned routing, natural-language capability, concurrent atomicity, runtime
safety, or useful behavior outside the locked requests.

## Prior evidence

The primary [Switch Transformer paper](https://arxiv.org/abs/2101.03961) motivates selecting
expert parameters from an input. The primary
[RouterRetriever paper](https://arxiv.org/abs/2409.02685) studies query-driven selection among
domain-specific retrieval experts. Neither establishes exact manifest-scope routing or the result
of this synthetic protocol.

## Decision

`pass`
