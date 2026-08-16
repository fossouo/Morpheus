# EXP-018 — Exclusion-precedence expert routing

- **Schema**: strict-v1
- **Date**: 2026-08-16
- **Status**: complete
- **Compute**: C0
- **Data**: eleven predeclared synthetic held-out requests and four synthetic expert packages

## Question

Can an unchanged deterministic kernel apply exact and whole-segment-wildcard scope exclusions
before expert lookup, while retaining include specificity, fail-closed ties, unrelated behavior,
order invariance, boundaries, and unload rollback?

## Hypothesis

The frozen EXP-017 router will score 3/8 against the locked target values because it ignores five
matching exclusions and returns expert values. The candidate will score 8/8, deny all three exact
and two wildcard exclusion cases before lookup, preserve 3/3 regressions, select the literal
include in both specificity orders, reject a non-excluded equal-specificity tie in both orders,
apply exclusion precedence to an otherwise tied request in both orders, preserve subsequent
control responses, reject boundary and absent probes, and restore all eight unloaded responses.

## Baseline

The baseline is the frozen EXP-017 wildcard router. It validates and loads the same compatible
packages and applies the same include matching and depth-then-literal specificity rule, but it
does not interpret `scope.exclude`. The candidate differs only by validating exclusions with the
same narrow pattern grammar and returning an explicit exclusion response before include ranking
or knowledge lookup when any loaded exclusion matches the request scope.

## Protocol

1. Lock four synthetic packages, eight target requests, three unrelated regression requests,
   two compatible package orders, two literal-specificity orders, two request-time tie orders,
   one tie-plus-exclusion request, one segment-boundary probe, and one absent-scope probe.
2. Load the compatible pair in both orders. Measure the EXP-017 baseline on the eight targets,
   then measure candidate targets and regressions.
3. Require candidate denial before lookup for three exact-exclusion and two wildcard-exclusion
   targets, while three non-excluded targets retain their locked values.
4. Compose the specificity pair in both orders and require the literal include to win. Compose
   the tie pair in both orders and require an explicit ambiguity response plus an unchanged
   unambiguous control response.
5. On the same tie pair, issue a request matching an exclusion and both tied includes; require
   the explicit exclusion response in both orders, establishing exclusion-before-ranking for
   this fixture.
6. Require identical candidate responses across compatible orders, explicit boundary and absent
   rejections, unload equality with all eight unloaded responses, and atomic rejection of invalid
   exclusion patterns.
7. Repeat the complete trial in process and require byte-for-byte identical decisions.
8. Run exactly one measured evaluator invocation, then repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Include and exclusion
matching is exact and case-sensitive per segment; `*` must occupy one complete segment, matches
exactly one segment, and may occur at most once per pattern. A matching pattern also covers
descendant request scopes. No model, external service, private datum, training procedure, network
call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over exclusion-blind EXP-017 routing;
- baseline values returned from excluded targets and candidate exact/wildcard denial counts;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with the unloaded baseline;
- literal-specificity selections, non-excluded tie rejections, unchanged post-tie controls, and
  exclusion-over-tie decisions across two package orders;
- boundary and absent-scope rejections across two compatible orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline produces all eight locked policy outputs, returns values for all five
excluded targets, and scores 3/8 against candidate target values; the candidate must score 8/8
for an absolute gain of 0.625, deny 3/3 exact and 2/2 wildcard exclusions, preserve 3/3
regressions with zero drop, remain identical across compatible orders, select the literal include
in 2/2 orders, reject the non-excluded tie in 2/2 orders, retain 2/2 control responses, apply
exclusion over the tie in 2/2 orders, reject boundary and absent scopes in 2/2 orders each,
restore 8/8 unloaded responses, repeat identically, finish within 1 second, keep the fixture below
16 KiB, make zero external calls, and pass all repository checks.

Stop after eleven held-out requests, two compatible orders, two specificity orders, two tie
orders, two in-process trials, and one measured evaluator invocation. Stop immediately on a
returned excluded value, partial-segment wildcard match, arbitrary tie selection, state mutation
after denial, boundary failure, budget overrun, network requirement, baseline mutation, or test
failure.

## Results

The exclusion-blind EXP-017 baseline produced all eight locked policy outputs, returned expert
values for all five excluded targets, and scored 3/8 against the candidate target values. The
candidate scored 8/8, an absolute target accuracy gain of 0.625. It denied all 3 exact-exclusion
and 2 wildcard-exclusion targets before lookup. Both unloaded and loaded conditions scored 3/3
on the held-out regressions, for zero regression drop.

Both package orders selected the exact literal include over the equally deep wildcard include.
Both non-excluded equal-specificity orders returned the explicit ambiguity error and retained the
unambiguous control response. Both tie-plus-exclusion orders returned the explicit exclusion
response. Reversing compatible package order changed no response. Boundary and absent probes
were each rejected in both orders, unload restored all 8 unloaded target responses, invalid
exclusion patterns were rejected before state mutation, and two complete in-process trials were
identical.

The fixture was 9,070 bytes, the evaluator made 0 external calls, and the single measured
invocation completed in 0.001321 seconds. The repository suite passed 124 tests; 19 experiment
records and 19 index-record matches validated; the expert template validated at the pinned date;
and the public-safety check passed. These checks followed the locked evaluator result and do not
alter it.

## Interpretation

**Observation:** every predeclared behavioral, regression, precedence, specificity, ambiguity,
boundary, absence, order, rollback, repeatability, size, latency, and cost threshold passed.

**Inference:** within this synthetic grammar, evaluating exclusions before include ranking and
lookup prevents the five locked exclusion-blind returns while retaining the tested deterministic
routing behavior. This is a measured scope-policy behavior, not evidence of a complete
authorization system, semantic policy interpretation, learned routing, natural-language
capability, runtime safety, or self-improvement.

## Limitations

The protocol is limited to slash-separated synthetic labels, at most one whole-segment wildcard
per pattern, exact strings, tiny key-value packages, and a deterministic lookup kernel. It cannot
establish semantic policy interpretation, authorization-system correctness, learned routing,
natural-language capability, concurrent atomicity, runtime safety, or useful behavior outside
the locked requests.

## Prior evidence

The primary [XACML 3.0 specification](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html#_Toc325047268)
defines a deny-overrides policy-combining algorithm and motivates only the tested precedence
direction. The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated path segments and motivates only the segment boundary. Neither standard
defines Morpheus expert scopes, its wildcard grammar, package composition, or the expected result
of this synthetic protocol.

## Decision

`pass`
