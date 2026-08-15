# EXP-017 — Wildcard scope expert routing

- **Schema**: strict-v1
- **Date**: 2026-08-15
- **Status**: complete
- **Compute**: C0
- **Data**: nine predeclared synthetic held-out requests and four synthetic expert packages

## Question

Can an unchanged deterministic kernel route a caller-supplied hierarchical scope through a
minimal single-segment wildcard grammar, rank matches by depth then literal-segment count, and
reject request-time equal-specificity ties without weakening boundaries, unrelated behavior,
order invariance, or unload rollback?

## Hypothesis

The frozen EXP-016 literal-prefix baseline will score 2/6 on the locked target values because
four requests require a wildcard match. The candidate will score 6/6, preserve 3/3 regressions,
select the literal pattern over an equally deep wildcard pattern in both package orders, reject
an equal-depth and equal-literal-count wildcard tie in both package orders without changing
subsequent control responses, reject boundary and absent probes, and restore all six unloaded
responses after unload.

## Baseline

The baseline is the frozen EXP-016 hierarchical router. It validates and loads the same two
compatible packages, but treats `*` as an ordinary literal segment. The candidate differs only
by allowing at most one complete `*` segment per declared scope, matching it to exactly one
request segment, and ranking matches lexicographically by declared depth and then number of
literal segments.

## Protocol

1. Lock four synthetic packages, six target requests, three unrelated regression requests, two
   compatible package orders, two literal-specificity orders, two request-time tie orders, one
   segment-boundary probe, and one absent-scope probe before execution.
2. Load the compatible pair in both orders. Measure the literal-prefix baseline on the six
   targets, then measure candidate targets and regressions.
3. Compose the literal-specificity pair in both orders and require the exact literal pattern to
   win over the equally deep wildcard pattern.
4. Compose the tie pair in both orders, issue the ambiguous request, require an explicit
   fail-closed response, then require an unambiguous control response to remain unchanged.
5. Require identical candidate responses across compatible orders and explicit rejection of
   the boundary and absent probes in both orders; unload and remeasure all six targets.
6. Repeat the complete trial in process and require byte-for-byte identical decisions.
7. Run exactly one measured evaluator invocation, then run repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Matching is exact and
case-sensitive per segment; `*` must occupy a whole segment, matches exactly one segment, and may
occur at most once in a declared scope. No model, external service, private datum, training
procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over literal-prefix routing;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with the unloaded baseline;
- literal-specificity selections across two package orders;
- request-time equal-specificity rejections and unchanged-control counts across two orders;
- boundary and absent-scope rejections across two compatible orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline produces all six locked policy outputs and scores 2/6 against target
values, the candidate scores 6/6 for an absolute gain of 0.666667, both regression conditions
score 3/3 with zero drop, reversing compatible order changes no response, both literal-specificity
orders select the literal pattern, both equal-specificity orders return the explicit ambiguity
error and retain 2/2 control responses, boundary and absent scopes are each rejected in both
compatible orders, unload restores 6/6 unloaded responses, repeated trials are identical, the
measured invocation finishes within 1 second, the fixture is below 16 KiB, external calls remain
zero, and all repository checks pass.

Stop after nine held-out requests, two compatible orders, two specificity orders, two tie orders,
two in-process trials, and one measured evaluator invocation. Stop immediately on fixture
inconsistency, partial-segment wildcard matching, arbitrary tie selection, state mutation after
ambiguity, budget overrun, network requirement, baseline mutation, or test failure.

## Results

The literal-prefix baseline produced all six locked policy outputs and scored 2/6 against the
target values. The wildcard candidate scored 6/6, an absolute target accuracy gain of 0.666667.
Both unloaded and loaded conditions scored 3/3 on the held-out regressions, for zero regression
drop.

Both package orders selected the exact literal pattern over the equally deep wildcard pattern.
Both equal-depth and equal-literal-count wildcard orders returned the explicit ambiguity error;
the unambiguous control response remained correct in both loaded states. Reversing compatible
package order changed no response. The segment-boundary and absent-scope probes were each rejected
in both compatible orders. Unload restored all 6 unloaded target responses, and two complete
in-process trials were identical.

The fixture was 7,878 bytes, the evaluator made 0 external calls, and the single measured
invocation completed in 0.000973 seconds. The repository suite passed 117 tests; 18 experiment
records and 18 index-record matches validated; the expert template validated at the pinned date;
and the public-safety check passed.

## Interpretation

**Observation:** every predeclared behavioral, regression, specificity, ambiguity, boundary,
absence, order, rollback, repeatability, size, latency, cost, and repository threshold passed.

**Inference:** within this synthetic grammar, a single whole-segment wildcard adds the tested
routing behavior relative to EXP-016's literal-prefix router, while the depth-then-literal ranking
and explicit tie response retain the tested deterministic boundaries. This is a measured lookup
routing behavior, not evidence of semantic expert discovery, learned routing, natural-language
capability, or self-improvement.

## Limitations

The protocol is limited to slash-separated synthetic labels, one whole-segment wildcard per
declared scope, exact string identifiers, tiny key-value packages, and a deterministic lookup
kernel. It cannot establish semantic intent classification, learned routing, natural-language
capability, concurrent atomicity, runtime safety, or useful behavior outside the locked requests.

## Prior evidence

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated path segments and motivates only the segment boundary used here. The
primary [CDNI Metadata specification](https://www.rfc-editor.org/rfc/rfc8006.html#section-4.1.5)
defines a case-sensitive path pattern with `*`, but its wildcard may span characters and slashes;
Morpheus deliberately tests the narrower rule of exactly one complete segment. Neither standard
defines expert routing, the depth-then-literal ranking, or the result of this synthetic protocol.

## Decision

`pass`
