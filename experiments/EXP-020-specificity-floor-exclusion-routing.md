# EXP-020 — Specificity-floor expert exclusion routing

- **Schema**: strict-v1
- **Date**: 2026-08-20
- **Status**: complete
- **Compute**: C0
- **Data**: eleven predeclared synthetic held-out requests and four synthetic expert packages

## Question

Can a deterministic expert router prevent fallback to a broader package when every most-specific
matching package excludes a request, while preserving cross-package delegation to an eligible
most-specific package, ambiguity handling, regressions, order invariance, boundaries, and unload
rollback?

## Hypothesis

The frozen EXP-019 baseline will score 6/8 against the locked target values because it will return
a broader package value for one exact and one wildcard case after the more-specific package
excludes itself. The candidate will score 8/8 by fixing the best pre-exclusion include score as a
specificity floor, denying both broader fallbacks, preserving two cross-package delegations, two
ordinary allows, and two all-applicable-excluded denials, retaining 3/3 regressions, selecting the
literal include in both specificity orders, rejecting an equal-specificity tie in both orders
without changing the control response, rejecting boundary and absent probes, and restoring all
eight unloaded responses.

## Baseline

The baseline is the frozen EXP-019 package-owned exclusion router. It finds matching includes,
removes each package whose own exclusion matches, then ranks all remaining candidates. This can
select a broader eligible package after a more-specific package is removed. The candidate differs
only by calculating the highest include score before exclusion filtering and allowing selection
only among packages at that score. If all candidates at the floor exclude themselves, it returns
the explicit exclusion error instead of considering a broader match.

## Protocol

1. Lock four synthetic packages, eight target requests, three unrelated regression requests, two
   compatible package orders, two literal-specificity orders, two request-time tie orders, one
   segment-boundary probe, and one absent-scope probe before execution.
2. Load the compatible pair in both orders. Measure the EXP-019 baseline on all eight targets,
   then measure the candidate targets and regressions.
3. Require both routers to preserve one exact and one wildcard delegation where a broader package
   excludes itself and an eligible more-specific package remains.
4. Require the candidate to deny one exact and one wildcard case where the most-specific package
   excludes itself, while the baseline returns a broader value.
5. Require both routers to retain one exact and one wildcard denial when every matching package
   excludes itself, and retain two ordinary allowed routes.
6. Compose the probe pair in both orders. Require literal specificity, fail-closed equal-score
   ambiguity, an unchanged post-ambiguity control, segment-boundary rejection, absent-scope
   rejection, compatible-order invariance, and unload equality.
7. Repeat the complete trial in process and require byte-for-byte identical decisions.
8. Run exactly one measured evaluator invocation, then repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Include and exclusion
matching is exact and case-sensitive per segment; `*` must occupy one complete segment, matches
exactly one segment, and may occur at most once per pattern. No model, external service, private
datum, training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over EXP-019 routing;
- baseline broader-fallback count and candidate specificity-floor denial count;
- exact and wildcard cross-package delegation preservation;
- all-applicable-excluded denial count;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with the unloaded baseline;
- literal-specificity selections, equal-specificity rejections, and post-ambiguity controls;
- boundary and absent-scope rejections across two compatible orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline produces all eight locked policy outputs, scores 6/8 against candidate
targets, and makes both locked broader fallbacks; the candidate must score 8/8 for an absolute gain
of 0.25, deny both broader fallbacks, preserve both cross-package delegations and both all-excluded
denials, preserve 3/3 regressions with zero drop, remain identical across compatible orders, select
the literal include in 2/2 orders, reject the equal-specificity tie in 2/2 orders, retain 2/2
control responses, reject boundary and absent scopes in 2/2 orders each, restore 8/8 unloaded
responses, repeat identically, finish within 1 second, keep the fixture below 16 KiB, make zero
external calls, and pass all repository checks.

Stop after eleven held-out requests, two compatible orders, two specificity orders, two tie
orders, two in-process trials, and one measured evaluator invocation. Stop immediately on a
broader fallback from the candidate, loss of an eligible most-specific delegation, arbitrary tie
selection, state mutation after ambiguity, boundary failure, budget overrun, network requirement,
baseline mutation, or test failure.

## Results

The frozen EXP-019 baseline produced all eight locked policy outputs, returned the broader package
value for both locked fallback cases, and scored 6/8 against the candidate target values. The
specificity-floor candidate scored 8/8, an absolute target accuracy gain of 0.25, and returned the
explicit exclusion error for both the exact and wildcard broader-fallback cases.

The candidate preserved both exact and wildcard cross-package delegations and both cases where
all applicable packages excluded themselves. Both unloaded and loaded conditions scored 3/3 on
the held-out regressions, for zero regression drop. Both package orders selected the literal
include on the specificity probe, returned the explicit ambiguity response on the equal-score
probe, and preserved the following control response. Reversing compatible order changed no
response. Boundary and absent probes were each rejected in both orders, unload restored all eight
unloaded target responses, and two complete in-process trials were identical.

The fixture was 9,510 bytes, the evaluator made 0 external calls, and the single measured
invocation completed in 0.002435 seconds. The repository suite passed 138 tests; 21 experiment
records and 21 index-record matches validated; the expert template validated at the pinned date;
and the public-safety check passed. These checks followed the locked evaluator result and do not
alter it.

## Interpretation

**Observation:** every predeclared target, broader-fallback denial, delegation, all-excluded
denial, regression, specificity, ambiguity, boundary, absence, order, rollback, repeatability,
size, latency, and cost threshold passed.

**Inference:** within this synthetic grammar, fixing the best pre-exclusion include score as a
floor prevents the two locked broader fallbacks without weakening the tested delegation and
determinism behaviors. This is a measured routing-policy behavior, not evidence of authorization-
system correctness, semantic policy interpretation, learned routing, natural-language capability,
runtime safety, or self-improvement.

## Limitations

The protocol is limited to slash-separated synthetic labels, at most one whole-segment wildcard
per pattern, exact strings, four tiny key-value packages, and a deterministic lookup kernel. It
cannot establish authorization-system correctness, semantic policy interpretation, learned
routing, natural-language capability, concurrent atomicity, runtime safety, or useful behavior
outside the locked requests.

## Prior evidence

The primary [XACML 3.0 specification](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html#_Toc325047268)
defines combining algorithms including deny-overrides and only-one-applicable, motivating explicit
policy-combination behavior. The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated path segments and motivates only the segment boundary. Neither standard
defines Morpheus expert-package ownership, a specificity floor, or the expected synthetic result.

## Decision

`pass`
