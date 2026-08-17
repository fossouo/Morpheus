# EXP-019 — Package-owned expert exclusion routing

- **Schema**: strict-v1
- **Date**: 2026-08-17
- **Status**: complete
- **Compute**: C0
- **Data**: nine predeclared synthetic held-out requests and four synthetic expert packages

## Question

Can a deterministic expert router prevent one package's exclusion from suppressing an otherwise
eligible package, while still failing closed when every applicable package excludes the request
and retaining specificity, ambiguity, regressions, order invariance, boundaries, and unload
rollback?

## Hypothesis

The frozen EXP-018 global deny-overrides baseline will score 4/6 against the locked target values
because it will deny two requests that an unrelated package can serve. The candidate will score
6/6 by recovering one exact and one wildcard cross-package route, deny both requests for which
all applicable packages exclude themselves, preserve 3/3 regressions, select the literal include
in both specificity orders, reject an equal-specificity tie in both orders without changing the
control response, reject boundary and absent probes, and restore all six unloaded responses.

## Baseline

The baseline is the frozen EXP-018 router. It validates and loads the same compatible packages,
but combines every loaded exclusion into one global deny list evaluated before include ranking.
The candidate differs only by retaining exclusion ownership: it first finds include candidates,
removes a candidate only when an exclusion declared by that same package matches, then ranks the
remaining candidates by EXP-017's depth-and-literal rule. It returns the explicit exclusion error
when includes matched but every applicable package was removed.

## Protocol

1. Lock four synthetic packages, six target requests, three unrelated regression requests, two
   compatible package orders, two literal-specificity orders, two request-time tie orders, one
   segment-boundary probe, and one absent-scope probe before execution.
2. Load the compatible pair in both orders. Measure the EXP-018 global-deny baseline on all six
   targets, then measure candidate targets and regressions.
3. Require the candidate to recover one exact and one wildcard request for the non-excluding
   package, while the baseline returns the explicit exclusion error for both.
4. Require one exact and one wildcard request excluded by every matching package to retain the
   explicit exclusion error; do not treat an unrelated non-matching package as applicable.
5. Compose the probe pair in both orders. Require the literal include to win the specificity
   request, the equal-specificity request to fail closed, and the post-ambiguity control response
   to remain unchanged.
6. Require identical candidate responses across compatible orders, explicit boundary and absent
   rejections, unload equality with all six unloaded responses, and atomic rejection of invalid
   owned exclusion patterns.
7. Repeat the complete trial in process and require byte-for-byte identical decisions.
8. Run exactly one measured evaluator invocation, then repository tests, record and index
   validators, template validation at a pinned date, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. Include and exclusion
matching is exact and case-sensitive per segment; `*` must occupy one complete segment, matches
exactly one segment, and may occur at most once per pattern. No model, external service, private
datum, training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over global deny-overrides routing;
- global-baseline cross-package over-denials and candidate exact/wildcard recovery counts;
- fail-closed denial count when all applicable packages exclude the request;
- exact-match regression accuracy and regression drop;
- compatible composition order invariance and post-unload equality with the unloaded baseline;
- literal-specificity selections, equal-specificity rejections, and post-ambiguity controls;
- boundary and absent-scope rejections across two compatible orders;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the baseline produces all six locked policy outputs, scores 4/6 against candidate
targets, and makes both locked cross-package over-denials; the candidate must score 6/6 for an
absolute gain of 0.333333, recover both cross-package routes, deny both all-applicable-excluded
requests, preserve 3/3 regressions with zero drop, remain identical across compatible orders,
select the literal include in 2/2 orders, reject the equal-specificity tie in 2/2 orders, retain
2/2 control responses, reject boundary and absent scopes in 2/2 orders each, restore 6/6 unloaded
responses, repeat identically, finish within 1 second, keep the fixture below 16 KiB, make zero
external calls, and pass all repository checks.

Stop after nine held-out requests, two compatible orders, two specificity orders, two tie orders,
two in-process trials, and one measured evaluator invocation. Stop immediately on a returned
self-excluded value, suppression of an eligible non-excluding package, arbitrary tie selection,
state mutation after ambiguity, boundary failure, budget overrun, network requirement, baseline
mutation, or test failure.

## Results

The global EXP-018 baseline produced all six locked policy outputs, made both cross-package
over-denials, and scored 4/6 against the candidate target values. The package-owned candidate
scored 6/6, an absolute target accuracy gain of 0.333333. It recovered the one exact and one
wildcard route for the non-excluding package while returning the explicit exclusion error for
both requests excluded by every applicable package.

Both unloaded and loaded conditions scored 3/3 on the held-out regressions, for zero regression
drop. Both package orders selected the literal include on the specificity probe, returned the
explicit ambiguity response on the equal-specificity probe, and preserved the following control
response. Reversing compatible order changed no response. Boundary and absent probes were each
rejected in both orders, unload restored all 6 unloaded target responses, invalid owned
exclusion patterns were rejected before state mutation, and two complete in-process trials were
identical.

The fixture was 8,356 bytes, the evaluator made 0 external calls, and the single measured
invocation completed in 0.001380 seconds. The repository suite passed 131 tests; 20 experiment
records and 20 index-record matches validated; the expert template validated at the pinned date;
and the public-safety check passed. These checks followed the locked evaluator result and do not
alter it.

## Interpretation

**Observation:** every predeclared target, cross-package recovery, all-excluded denial,
regression, specificity, ambiguity, boundary, absence, order, rollback, repeatability, size,
latency, and cost threshold passed.

**Inference:** within this synthetic grammar, retaining exclusion ownership prevents the two
locked cross-package over-denials without weakening the tested fail-closed and deterministic
behaviors. This is a measured routing-policy behavior, not evidence of authorization-system
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
defines both deny-overrides and only-one-applicable combining behavior, motivating the need to
make policy-combination scope explicit. The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated path segments and motivates only the segment boundary. Neither standard
defines Morpheus expert-package ownership, its filtering rule, or the expected synthetic result.

## Decision

`pass`
