# EXP-024 — Declared-root routing fence

- **Schema**: strict-v1
- **Date**: 2026-08-24
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic scope requests and the SHA-256-pinned EXP-022 fixture

## Question

Does checking a separately declared allowed root before wildcard scope routing prevent the
EXP-022 cross-root failure without changing pattern specificity, three-candidate exclusion
cardinality, regressions, order invariance, or unload rollback?

## Hypothesis

The unrestricted EXP-022 router will return expert-derived responses for all four locked
cross-root requests. A declared-root candidate will reject all four before pattern matching in
all 24 package permutations while restoring the original 8/8 target outputs, every 3-to-1/2/0
transition, both specificity-floor denials, 3/3 regressions, boundary and absence rejection,
and 192/192 post-unload responses.

## Baseline

The boundary baseline is the unchanged EXP-022 specificity-floor router with its unrestricted
one-whole-segment wildcard grammar. The behavioral baseline is EXP-022's pre-exclusion-ambiguity
policy, which is expected to score 4/8 on the locked targets. The candidate changes neither
packages nor specificity: it adds only one literal single-segment allowed-root check before
scope matching.

## Protocol

1. Pin the unmodified EXP-022 fixture by SHA-256 and set the explicit allowed-root set to the
   single synthetic label `synthetic`.
2. Lock four held-out requests under two undeclared neighboring roots, covering wildcard routes
   that previously returned an expert value or an exclusion response.
3. Compose the four unchanged quarantined packages in all 24 permutations and compare the
   unrestricted router with the declared-root candidate on the four boundary requests.
4. In the same permutations, compare the frozen pre-exclusion baseline with the candidate on
   all eight EXP-022 targets, three regressions, cardinality checks, boundary and absence probes,
   and unload rollback.
5. Repeat the full trial in process and require byte-for-byte identical decisions.
6. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned expert-template validation, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Roots, patterns, requests, and expert values are
synthetic. Matching remains exact and case-sensitive by slash-separated segment. No model,
external service, private datum, training procedure, network call, or production runtime is
permitted.

## Metrics

- cross-root accuracy, false accepts, rejection count, and gain over unrestricted routing;
- exact-match target accuracy and gain over pre-exclusion ambiguity;
- 3-to-1 selections, 3-to-2 ambiguities, 3-to-0 denials, and specificity-floor denials;
- exact-match regression accuracy and regression drop;
- order invariance, original boundary rejection, absent-scope rejection, and rollback equality;
- repeatability across two in-process trials;
- combined fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if the unrestricted router emits all four locked cross-root baseline responses and
falsely accepts 4/4 relative to root isolation; the candidate rejects 4/4 in every one of 24
orders for an absolute accuracy gain of 1.0; the frozen behavioral baseline emits its declared
outputs and scores 4/8; the candidate scores 8/8 for a 0.5 absolute target gain and preserves
all declared cardinalities, two selections, two ambiguities, two cardinality denials, two floor
denials, 3/3 regressions, order invariance, 24/24 original boundary and absence rejections, and
192/192 rollback responses; both trials are identical; combined fixtures stay below 16 KiB;
the evaluator finishes below one second with zero external calls; and every repository check
passes.

Stop after four cross-root cases, all 24 package permutations, two in-process trials, and one
measured evaluator invocation. Stop immediately on a leaked undeclared root, altered specificity
or cardinality, arbitrary selection, broader fallback, regression loss, boundary failure, budget
overrun, network requirement, historical evaluator mutation, or repository-test failure.

## Results

The unrestricted router emitted all four locked cross-root baseline responses and falsely
accepted 4/4 relative to the declared-root policy. The candidate rejected 4/4, and the same four
responses were rejected in every one of the 24 package permutations, for an absolute cross-root
accuracy gain of 1.0.

The frozen pre-exclusion baseline emitted its locked outputs, produced six ambiguities, and
scored 4/8. The candidate scored 8/8 for an absolute target gain of 0.5. It preserved both 3-to-1
selections, both 3-to-2 ambiguities, both 3-to-0 denials, both specificity-floor denials, 3/3
regressions, all cardinality expectations, order invariance, 24/24 original boundary rejections,
24/24 absence rejections, and 192/192 post-unload responses.

The two in-process trials were identical. The pinned source plus delta fixture occupied 11,723
bytes, the evaluator made zero external calls, and its single measured invocation completed in
0.064795 seconds. The first repository-suite invocation exposed an error in a negative unit test:
it omitted the source bytes required by the pinned-hash validator and therefore stopped at the
hash check before exercising invalid roots. Only the test call was corrected; the measured
evaluator and locked fixture were not changed or rerun. Final repository checks are reported
after that correction and do not alter the measured result. The final suite passed 166 tests;
25 experiment records and 25 index-record matches validated; the expert template validated at
the pinned date; and the public-safety check passed.

## Interpretation

**Observation:** within the locked synthetic configuration, a separate root fence removes the
known cross-root wildcard behavior without rewriting patterns or changing their specificity,
and the original held-out cardinality behavior is retained.

**Inference:** namespace containment and within-namespace pattern specificity can be represented
as separate layers in this small router. This supports testing an explicit root declaration in
the expert-package contract before any stable-runtime promotion. It does not show that an
untrusted declaration is correct or that the fence is an authorization system.

## Limitations

The protocol cannot establish authorization-system correctness, trust in the root declaration,
semantic policy interpretation, learned routing, natural-language capability, concurrent
atomicity, scalable performance, runtime safety, or behavior outside the locked synthetic cases.

## Prior evidence

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines hierarchical paths as slash-separated segments and motivates treating a leading segment
as an explicit boundary. The primary [XACML 3.0 specification](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html#_Toc325047268)
defines policy applicability and combining behavior that motivate separating a boundary decision
from a later routing decision. Neither standard defines Morpheus's root declaration, wildcard
grammar, specificity score, or expected synthetic responses.

## Decision

`pass`
