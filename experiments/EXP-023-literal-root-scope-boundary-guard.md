# EXP-023 — Literal-root scope boundary guard

- **Schema**: strict-v1
- **Date**: 2026-08-23
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic scope patterns and the locked EXP-022 synthetic fixture with declared transformations

## Question

Does requiring the first segment of every include and exclude scope pattern to be literal prevent
the EXP-022 cross-root wildcard failure without weakening three-candidate exclusion cardinality,
specificity-floor denial, regressions, order invariance, or unload rollback?

## Hypothesis

The unrestricted EXP-022 grammar will accept both locked leading-wildcard adversarial patterns
and will route the neighboring-root boundary probe after composing the original package. A
literal-root candidate will classify all six grammar cases correctly, reject the unsafe package
transactionally in all 24 package permutations, and, after the eight declared literal-root
repairs to the EXP-022 fixture, preserve 8/8 target outputs, every 3-to-1/2/0 transition, both
specificity-floor denials, 3/3 regressions, 24/24 boundary and absence rejections, and 192/192
post-unload responses.

## Baseline

The grammar baseline is the unchanged whole-segment wildcard parser used through EXP-022: it
permits one `*` in any segment, including the first. Its behavioral baseline is the unchanged
EXP-021 pre-exclusion-ambiguity policy, which scores 4/8 on the locked routing targets. The
candidate keeps EXP-020 specificity-floor routing and adds only a pre-composition rule that the
first include or exclude segment cannot be `*`.

## Protocol

1. Lock six exact grammar cases: one invalid leading-wildcard include, one invalid
   leading-wildcard exclude, two valid internal-wildcard patterns, and two valid literal patterns.
2. Pin the EXP-022 fixture by SHA-256 and declare exactly eight replacements that change only the
   leading `*` segment in one package's includes and exclusions to the literal `synthetic` root.
3. Reproduce the original unsafe composition with the pinned fixture: require the unrestricted
   baseline to accept it and route the neighboring-root probe to an expert value.
4. Attempt the same unsafe composition with the candidate in all 24 package permutations; require
   rejection before any knowledge, include, or exclusion state is installed.
5. Apply the eight locked replacements, then run the candidate and the frozen behavioral baseline
   across all 24 permutations and the same eight targets, three regressions, boundary probe,
   absence probe, cardinality checks, and unload checks as EXP-022.
6. Repeat the full trial in process and require byte-for-byte identical decisions.
7. Run exactly one measured evaluator invocation, then repository tests, record and index
   validators, pinned expert-template validation, public-safety checks, and staged diff review.

Only the Python standard library is permitted. All patterns and requests are synthetic. Matching
remains exact and case-sensitive by slash-separated segment; `*` occupies one full non-root
segment, matches exactly one segment, and occurs at most once per pattern. No model, external
service, private datum, training procedure, network call, or production runtime is permitted.

## Metrics

- grammar-case accuracy, false accepts, and absolute gain over unrestricted parsing;
- unsafe-package baseline acceptance and neighboring-root response;
- candidate rejection and clean-state counts across all 24 unsafe package permutations;
- exact-match routing accuracy and gain over pre-exclusion ambiguity;
- 3-to-1 selections, 3-to-2 ambiguities, 3-to-0 denials, and specificity-floor denials;
- exact-match regression accuracy and regression drop;
- order invariance, boundary rejection, absent-scope rejection, and post-unload equality;
- repeatability across two in-process trials;
- combined bytes of the new fixture and pinned source fixture, measured evaluator latency;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if the unrestricted grammar scores 4/6 with exactly two false accepts and the
candidate scores 6/6 with zero false accepts; the unrestricted router accepts the original unsafe
package and reproduces its neighboring-root expert response; the candidate rejects the unsafe
package with clean state in 24/24 permutations; the frozen behavioral baseline emits its eight
locked outputs and scores 4/8; the repaired candidate scores 8/8 for a 0.5 absolute gain and
preserves all declared cardinalities, two selections, two ambiguities, two cardinality denials,
two floor denials, 3/3 regressions, both policies' order invariance, 24/24 boundary and absence
rejections, and 192/192 rollback responses; both trials are identical; combined fixtures remain
below 16 KiB; the evaluator finishes below 1 second with zero external calls; and every repository
check passes.

Stop after six grammar cases, one unrestricted unsafe composition, 24 guarded unsafe
compositions, the 24 repaired routing permutations, two in-process trials, and one measured
evaluator invocation. Stop immediately on partial state after rejection, any lost EXP-022 passing
behavior, arbitrary selection, broader fallback, regression loss, boundary failure, budget
overrun, network requirement, historical evaluator mutation, or repository-test failure.

## Results

The unrestricted grammar scored 4/6 and falsely accepted both leading-wildcard cases. The
literal-root grammar scored 6/6 with zero false accepts, an absolute grammar accuracy gain of
0.333333. The unrestricted router accepted the original unsafe package and returned
`gamma-fern-59` for the neighboring-root probe. The guarded router rejected that package before
state installation in all 24 permutations; every rejected kernel retained empty knowledge,
include, and exclusion state and returned `route-error:scope-not-found` for the boundary probe.

The repaired routing fixture passed 24/24 boundary rejections, 24/24 absent-scope rejections,
3/3 regressions, order invariance, 192/192 post-unload responses, repeatability, and both
specificity-floor denials. It failed the locked behavioral outputs and cardinalities. Replacing
the third package's leading wildcard with `synthetic` raised those patterns from two to three
literal segments, so they no longer tied the other two packages at the same declared depth. The
behavioral baseline did not emit its locked outputs, scored 5/8 instead of 4/8, and produced zero
pre-exclusion ambiguities instead of six. The candidate also scored 5/8 instead of 8/8, selected
only one of two expected 3-to-1 survivors, preserved zero of two expected 3-to-2 ambiguities, and
retained both 3-to-0 and both floor denials. Its measured gain over that altered baseline was
zero, not 0.5.

The two in-process trials were identical. The pinned source plus delta fixture occupied 12,868
bytes, the evaluator made 0 external calls, and the single measured invocation completed in
0.054858 seconds. Repository checks are reported separately after this locked negative result
and do not alter it. The repository suite then passed 159 tests; 24 experiment records and 24
index-record matches validated; the expert template validated at the pinned date; and the
public-safety check passed.

## Interpretation

**Observation:** the literal-root rule blocks the known cross-root match transactionally and
preserves boundaries, regressions, permutations, rollback, repeatability, size, latency, and cost,
but its direct literal replacement changes wildcard specificity and fails three held-out routing
outputs.

**Inference:** within this exact synthetic scorer, wildcard position and literal-count ranking
are coupled. A first-segment-literal rule cannot be promoted by mechanically replacing the root
wildcard while keeping the existing `(depth, literal count)` score. This is a narrow negative
result; it does not show that all namespace guards fail, nor does it establish authorization-
system correctness, semantic policy interpretation, learned routing, natural-language
capability, runtime safety, or self-improvement.

## Limitations

The protocol cannot establish authorization-system correctness, semantic policy interpretation,
learned routing, natural-language capability, concurrent atomicity, runtime safety, or behavior
outside the locked synthetic requests.

## Prior evidence

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines slash-separated path segments and motivates treating the first segment as a distinct
boundary. The primary [XACML 3.0 specification](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html#_Toc325047268)
defines combining algorithms that motivate explicit applicability and exclusion order. Neither
standard defines Morpheus's literal-root rule, wildcard grammar, specificity score, or expected
synthetic outputs.

## Decision

`fail`
