# EXP-021 — Equal-specificity expert exclusion isolation

- **Schema**: strict-v1
- **Date**: 2026-08-21
- **Status**: complete
- **Compute**: C0
- **Data**: eleven predeclared synthetic held-out requests and three synthetic expert packages

## Question

When two expert packages tie at the highest include specificity, can package-owned exclusions
remove only the ineligible package before the ambiguity decision, while preserving ambiguity
between two eligible packages, all-excluded denial, the specificity floor, regressions, order
invariance, boundaries, and unload rollback?

## Hypothesis

A pre-exclusion-ambiguity baseline will score 4/8 against the locked policy outputs because it
will reject six equal-specificity ties before checking package-owned exclusions. The unchanged
EXP-020 candidate will score 8/8 by selecting the sole eligible package in one exact-exclusion
and one wildcard-exclusion case, preserving two genuinely ambiguous two-eligible cases,
returning the explicit exclusion error for two all-excluded cases and two specificity-floor
cases, retaining 3/3 regressions, rejecting boundary and absent scopes, remaining order
invariant, and restoring all eight unloaded responses.

## Baseline

The baseline uses the EXP-020 include score and specificity floor, but checks whether more than
one package ties at that floor before applying package-owned exclusions. It therefore returns
the explicit ambiguity response for every top-score tie. The candidate is the frozen EXP-020
router: it fixes the top include score, filters only those tied packages by their own exclusions,
then selects one survivor, rejects multiple survivors as ambiguous, or rejects zero survivors as
excluded. Neither policy considers a broader include below the fixed floor.

## Protocol

1. Lock three synthetic quarantined packages, eight target requests, three unrelated regression
   requests, the package order and its reversal, one segment-boundary probe, and one absent-scope
   probe before execution.
2. Compare the baseline and unchanged EXP-020 candidate on one exact-exclusion and one wildcard-
   exclusion tie where exactly one top-score package remains eligible.
3. Require the candidate to retain ambiguity for one exact-labelled and one wildcard-labelled
   case where two top-score packages remain eligible.
4. Require the candidate to return the exclusion error for one exact-labelled and one wildcard-
   labelled case where every top-score package excludes itself.
5. Require both policies to reject one exact and one wildcard most-specific self-exclusion
   without falling back to the broader loaded package.
6. Require 3/3 unrelated echo regressions, order invariance, boundary and absence rejection, and
   equality with all eight unloaded responses after rollback.
7. Repeat the complete trial in process and require byte-for-byte identical decisions.
8. Run exactly one measured evaluator invocation, then repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Matching is exact and
case-sensitive by slash-separated segment; `*` must occupy one complete segment, match exactly
one segment, and occur at most once per pattern. No model, external service, private datum,
training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over pre-exclusion ambiguity;
- pre-exclusion ambiguity count and post-exclusion isolated-package selection count;
- two-eligible ambiguity preservation, all-excluded denial, and specificity-floor denial counts;
- exact-match regression accuracy and regression drop;
- baseline and candidate order invariance plus post-unload equality;
- boundary and absent-scope rejection across both package orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline emits all eight locked baseline outputs, scores 4/8 against candidate
targets, and produces six pre-exclusion ambiguities; the candidate must score 8/8 for an absolute
gain of 0.5, select both sole eligible packages, preserve both two-eligible ambiguities, return
both all-excluded denials and both specificity-floor denials, preserve 3/3 regressions with zero
drop, keep both policies invariant to package order, reject boundary and absent scopes in 2/2
orders each, restore 8/8 unloaded responses, repeat identically, finish within 1 second, keep the
fixture below 16 KiB, make zero external calls, and pass all repository checks.

Stop after eleven held-out requests, two package orders, two in-process trials, and one measured
evaluator invocation. Stop immediately on arbitrary selection between two eligible packages,
fallback below the specificity floor, loss of the sole eligible tied package, regression loss,
state change after an error, boundary failure, budget overrun, network requirement, baseline
mutation, or repository-test failure.

## Results

The pre-exclusion-ambiguity baseline emitted all eight locked baseline outputs, returned the
ambiguity response for six equal-specificity ties, and scored 4/8 against the candidate policy
outputs. The unchanged EXP-020 candidate scored 8/8, an absolute gain of 0.5. It selected the
sole eligible top-score package in both the exact-exclusion and wildcard-exclusion isolation
cases, retained the ambiguity response for both two-eligible cases, returned the exclusion error
for both all-excluded cases, and rejected both attempts to fall back below the specificity floor.

The unloaded and candidate conditions each scored 3/3 on unrelated regressions. Baseline and
candidate responses were invariant to reversing all three packages. Boundary and absent scopes
were rejected in both orders, unload restored all eight unloaded target responses, and two
complete in-process trials were identical.

The fixture was 8,371 bytes, the evaluator made 0 external calls, and the single measured
invocation completed in 0.002457 seconds. The repository suite passed 145 tests; 22 experiment
records and 22 index-record matches validated; the expert template validated at the pinned date;
and the public-safety check passed. These checks followed the locked evaluator result and do not
alter it.

## Interpretation

**Observation:** every predeclared target, isolation, ambiguity, all-excluded denial,
specificity-floor denial, regression, order, boundary, absence, rollback, repeatability, size,
latency, and cost threshold passed.

**Inference:** within this synthetic grammar, applying package-owned exclusions among packages
already tied at the highest include score distinguishes a sole eligible route from genuine
ambiguity and total exclusion without weakening the tested specificity floor. This is a measured
routing-policy behavior, not evidence of authorization-system correctness, semantic policy
interpretation, learned routing, natural-language capability, runtime safety, or self-improvement.

## Limitations

The protocol is limited to slash-separated synthetic labels, at most one whole-segment wildcard
per pattern, exact strings, three tiny key-value packages, and a deterministic lookup kernel. It
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

`pass`
