# EXP-022 — Multi-candidate expert exclusion cardinality

- **Schema**: strict-v1
- **Date**: 2026-08-22
- **Status**: complete
- **Compute**: C0
- **Data**: eleven predeclared synthetic held-out requests and four synthetic expert packages

## Question

Does the unchanged specificity-floor router preserve its exclusion behavior when three expert
packages tie at the highest include specificity, producing the correct selection, ambiguity, or
denial as exclusions reduce the eligible set from three to one, two, or zero?

## Hypothesis

The frozen EXP-021 pre-exclusion-ambiguity baseline will score 4/8 against the locked policy
outputs because it will reject all six three-candidate ties before checking package-owned
exclusions. The unchanged EXP-020 candidate will score 8/8 by selecting the sole survivor in one
exact and one wildcard 3-to-1 transition, preserving ambiguity in one exact and one wildcard
3-to-2 transition, denying one exact and one wildcard 3-to-0 transition, retaining both
specificity-floor denials and 3/3 regressions, remaining invariant across all 24 package
permutations, and restoring every unloaded response.

## Baseline

The baseline is the frozen EXP-021 pre-exclusion-ambiguity policy. It fixes the highest include
score but returns the explicit ambiguity response whenever more than one package ties at that
score, before applying package-owned exclusions. The candidate is the unchanged EXP-020 router:
it fixes the same specificity floor, filters only top-score packages by their own exclusions,
then selects one survivor, rejects multiple survivors as ambiguous, or rejects zero survivors as
excluded. Neither policy considers a broader include below the fixed floor.

## Protocol

1. Lock four synthetic quarantined packages, eight target requests, three unrelated regression
   requests, one segment-boundary probe, and one absent-scope probe before execution.
2. Derive all 24 permutations of the four locked package IDs and run both policies in every order.
3. Require every non-floor target to have exactly three pre-exclusion top-score candidates.
4. Require the candidate to select the sole survivor for exact and wildcard 3-to-1 cases, retain
   ambiguity for exact and wildcard 3-to-2 cases, and deny exact and wildcard 3-to-0 cases.
5. Require both policies to reject one exact and one wildcard most-specific self-exclusion
   without falling back to the broader loaded package.
6. Require 3/3 unrelated echo regressions, boundary and absence rejection in every order, and
   equality with all eight unloaded responses after rollback in every order.
7. Repeat the complete 24-order trial in process and require byte-for-byte identical decisions.
8. Run exactly one measured evaluator invocation, then repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Matching is exact and
case-sensitive by slash-separated segment; `*` must occupy one complete segment, match exactly
one segment, and occur at most once per pattern. No model, external service, private datum,
training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over pre-exclusion ambiguity;
- observed top-score and post-exclusion eligible cardinalities for every target and order;
- 3-to-1 selections, 3-to-2 ambiguity preservation, and 3-to-0 denials;
- specificity-floor denial count;
- exact-match regression accuracy and regression drop;
- baseline and candidate invariance across all 24 package permutations;
- boundary and absent-scope rejection across all orders;
- post-unload equality across all targets and orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline emits all eight locked baseline outputs, scores 4/8 against candidate
targets, and produces six pre-exclusion ambiguities; every declared cardinality must be observed
in all 24 orders; the candidate must score 8/8 for an absolute gain of 0.5, select both 3-to-1
survivors, preserve both 3-to-2 ambiguities, return both 3-to-0 denials and both specificity-floor
denials, preserve 3/3 regressions with zero drop, keep both policies order invariant, reject
boundary and absent scopes in 24/24 orders each, restore 192/192 unloaded target responses,
repeat identically, finish within 1 second, keep the fixture below 16 KiB, make zero external
calls, and pass all repository checks.

Stop after eleven held-out requests, all 24 package permutations, two in-process trials, and one
measured evaluator invocation. Stop immediately on arbitrary 3-to-2 selection, fallback below
the specificity floor, loss of a sole 3-to-1 survivor, incorrect cardinality, regression loss,
boundary failure, budget overrun, network requirement, baseline mutation, or repository-test
failure.

## Results

The baseline emitted all eight locked baseline outputs in every order, returned ambiguity for
all six three-candidate ties, and scored 4/8 against the candidate policy outputs. The unchanged
candidate scored 8/8 for an absolute gain of 0.5. It observed every locked cardinality in every
order, selected both 3-to-1 survivors, preserved both 3-to-2 ambiguities, returned both 3-to-0
denials, and retained both specificity-floor denials.

The unloaded and candidate conditions each scored 3/3 on unrelated regressions. Baseline and
candidate responses were invariant across all 24 package permutations, absent scopes were
rejected in 24/24 orders, unload restored 192/192 target responses, and two complete in-process
trials were identical.

The acceptance criterion failed because the segment-boundary probe was rejected in 0/24 orders.
The first-segment wildcard include `*/blue/item` matched the neighboring `syntheticx/blue/item`
scope, so all orders returned the expert value instead of `route-error:scope-not-found`. The
fixture was 10,257 bytes, the evaluator made 0 external calls, and the single measured invocation
completed in 0.055064 seconds. Repository checks are reported separately after this locked
negative result and do not alter it. The repository suite then passed 152 tests; 23 experiment
records and 23 index-record matches validated; the expert template validated at the pinned date;
and the public-safety check passed.

## Interpretation

**Observation:** the three-candidate cardinality transitions, regressions, specificity floor,
order invariance, absence, rollback, repeatability, size, latency, and cost thresholds passed,
but the predeclared boundary threshold failed in every order.

**Inference:** within this synthetic grammar, the unchanged candidate generalizes its cardinality
decision from two to three tied packages, but the experiment exposes that an unrestricted
first-segment wildcard crosses the intended top-level scope boundary. The candidate is not
accepted. This is a narrow routing-grammar failure, not evidence about authorization-system
correctness, semantic policy interpretation, learned routing, natural-language capability,
runtime safety, or self-improvement.

## Limitations

The protocol is limited to slash-separated synthetic labels, at most one whole-segment wildcard
per pattern, exact strings, four tiny key-value packages, and a deterministic lookup kernel. It
cannot establish authorization-system correctness, semantic policy interpretation, learned
routing, natural-language capability, concurrent atomicity, runtime safety, or useful behavior
outside the locked requests.

## Prior evidence

The primary [XACML 3.0 specification](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html#_Toc325047268)
defines combining algorithms including deny-overrides and only-one-applicable, motivating an
explicit order for exclusion and applicability decisions. The primary
[URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated path segments and motivates only the segment boundary. Neither standard
defines Morpheus package-owned exclusions, specificity scoring, or the expected synthetic result.

## Decision

`fail`
