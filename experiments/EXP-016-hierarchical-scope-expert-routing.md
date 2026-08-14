# EXP-016 — Hierarchical scope expert routing

- **Schema**: strict-v1
- **Date**: 2026-08-14
- **Status**: complete
- **Compute**: C0
- **Data**: eight predeclared synthetic held-out requests and three synthetic expert packages

## Question

Can an unchanged deterministic kernel route a hierarchical caller-supplied scope to the most
specific declared segment prefix, while rejecting equal-specificity ties, near-prefixes, and
absent scopes, preserving unrelated behavior, order invariance, and unload rollback?

## Hypothesis

The EXP-015 exact-only baseline will score 2/5 on the locked target values because only two
requests exactly equal a declared scope. The longest-prefix candidate will score 5/5, preserve
3/3 regressions, return the same responses in both compatible package orders, reject both
equal-specificity tie orders before state assignment, reject the near-prefix and absent probes
in both compatible orders, and restore all five unloaded responses after unload.

## Baseline

The baseline is the frozen EXP-015 exact-scope kernel. It validates and loads the same compatible
packages but selects a package only when the request scope exactly equals one declared include
scope. The candidate differs only by treating slash-separated scope segments as a hierarchy and
selecting the matching declared prefix with the greatest segment depth.

## Protocol

1. Lock three synthetic packages, five target requests, three unrelated regression requests,
   two compatible package orders, two reversed equal-specificity tie orders, one near-prefix
   probe, and one absent-scope probe before execution.
2. Load the two compatible packages in both orders. Measure the exact-only baseline on the five
   targets, then measure candidate targets and regressions.
3. Require identical candidate responses across compatible orders and explicit rejection of the
   near-prefix and absent probes in both orders.
4. Attempt both equal-specificity package orders. Require explicit rejection before any state
   assignment.
5. Unload the candidate and remeasure the five targets.
6. Repeat the complete trial in process and require byte-for-byte identical decisions.
7. Run exactly one measured evaluator invocation, then run repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Matching is exact and
case-sensitive per segment; raw character prefixes are forbidden. No model, external service,
private datum, training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over exact-only routing;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with the unloaded baseline;
- equal-specificity rejections and unchanged-state counts across two load orders;
- near-prefix and absent-scope rejections across two compatible load orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the exact-only baseline produces all five locked policy outputs and scores 2/5
against target values, the candidate scores 5/5 for an absolute gain of 0.6, both regression
conditions score 3/3 with zero drop, reversing compatible order changes no response, both
equal-specificity orders are rejected with 2/2 clean states, the near-prefix and absent scopes
are each rejected in both compatible orders, unload restores 5/5 unloaded responses, repeated
trials are identical, the measured invocation finishes within 1 second, the fixture is below
16 KiB, external calls remain zero, and all repository checks pass.

Stop after eight held-out requests, two compatible orders, two tie orders, two in-process trials,
and one measured evaluator invocation. Stop immediately on fixture inconsistency, raw-prefix
selection, ambiguous selection, partial state mutation, budget overrun, network requirement,
baseline mutation, or test failure.

## Results

The exact-only baseline produced all five locked policy outputs and scored 2/5 against the target
values. The hierarchical candidate scored 5/5, an absolute target accuracy gain of 0.6. Both
unloaded and loaded conditions scored 3/3 on the held-out regressions, for zero regression drop.

Reversing compatible package order changed no target, regression, or rejection response. Both
equal-specificity orders were rejected before state assignment with 2/2 clean states. The
near-prefix and absent scope were each rejected in both compatible orders. Unload restored all
5 unloaded target responses. Two complete in-process trials were identical. The fixture was
6,490 bytes, the evaluator made 0 external calls, and the single measured invocation completed
in 0.000703 seconds.

## Interpretation

**Observation:** every predeclared behavioral, regression, ambiguity, boundary, absence, order,
rollback, repeatability, size, latency, and cost threshold passed.

**Inference:** within this slash-segment synthetic protocol, longest-prefix selection adds the
tested descendant-scope behavior relative to EXP-015's exact-only router while retaining the
tested fail-closed boundaries. This is a measured deterministic routing behavior, not evidence
of semantic expert discovery, learned routing, natural-language capability, or self-improvement.

## Limitations

The protocol is limited to slash-separated synthetic scope labels, exact string identifiers,
tiny key-value packages, and a deterministic lookup kernel. It cannot establish semantic intent
classification, learned routing, natural-language capability, concurrent atomicity, runtime
safety, or useful behavior outside the locked requests. Equal-specificity conflicts are exact
duplicate declared prefixes detected during composition; the protocol does not test wildcard or
request-time ties.

## Prior evidence

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated hierarchical path segments; Morpheus borrows only that structural idea,
not URI resolution semantics. The primary
[RouterRetriever paper](https://arxiv.org/abs/2409.02685) studies query-driven selection among
domain-specific retrieval experts. Neither establishes longest-prefix expert routing or the
result of this synthetic protocol.

## Decision

`pass`
