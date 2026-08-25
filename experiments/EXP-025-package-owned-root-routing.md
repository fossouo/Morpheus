# EXP-025 — Package-owned root routing

- **Schema**: strict-v1
- **Date**: 2026-08-25
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic expert packages, scope requests, and declaration mutations

## Question

Can a root declaration owned by each expert package constrain that package's leading wildcard
without preventing an unrelated package from routing inside a second declared root, and can
inconsistent declarations be rejected before any expert state is installed?

## Hypothesis

The declaration-blind baseline will score 4/8 on the locked targets and falsely route all four
cross-root requests. The package-owned-root candidate will score 8/8 for a 0.5 absolute gain,
preserve four own-root routes across two roots and 3/3 regressions, restore all 16 unloaded
responses, and reject four inconsistent declarations in both package orders with eight clean
post-rejection states.

## Baseline

The baseline is the unchanged EXP-020 specificity-floor router. It receives the same two
quarantined packages and scope requests but ignores their separately supplied root declarations.
The candidate changes only matching eligibility: a package's include and exclusion patterns are
considered only when the request's first segment equals that package's declared literal root.

## Protocol

1. Lock two synthetic packages, two distinct literal roots, four own-root targets, four
   cross-root targets, three kernel regressions, one third-root probe, and one absent-scope probe.
2. Compose the packages in fixture order and reverse order. Compare the declaration-blind
   baseline with the candidate on all eight held-out targets.
3. Check both roots remain routable, cross-root and third-root requests fail closed, regressions
   are unchanged, decisions are order invariant, and unload restores all target responses.
4. Mutate two root declarations and one literal include and exclusion root. For every mutation,
   test both package orders, require rejection before installation, and probe for clean state.
5. Repeat the complete trial in process and require identical decisions.
6. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned expert-template validation, public-safety checks, and staged diff review.

Only the Python standard library is permitted. Packages, roots, patterns, requests, values, and
mutations are synthetic. Matching is exact and case-sensitive by slash-separated segment. No
model, external service, private datum, training, network call, or production runtime is allowed.

## Metrics

- held-out exact-match accuracy, cross-root false accepts, and absolute gain over baseline;
- own-root routes and cross-root rejections across two declared roots;
- regression accuracy, package-order invariance, third-root and absent-scope rejection;
- rollback equality across both orders;
- invalid declaration acceptance/rejection and clean-state counts across both orders;
- repeatability across two in-process trials;
- fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if the baseline emits every locked baseline output, scores 4/8, and makes four
cross-root false accepts; the candidate scores 8/8 for a 0.5 gain, preserves all four own-root
routes and rejects all four cross-root targets; both conditions retain 3/3 regressions; candidate
decisions are order invariant; third-root and absent-scope probes reject in both orders; rollback
matches 16/16 unloaded outputs; the baseline accepts all eight invalid-declaration orders while
the candidate rejects 8/8 with the exact locked errors and 8/8 clean states; both trials are
identical; the fixture stays below 16 KiB; evaluation finishes below one second with zero
external calls; and every repository check passes.

Stop after eight targets, three regressions, two valid orders, four declaration mutations in two
orders, two in-process trials, and one measured invocation. Stop immediately on a cross-root
route, loss of an own-root route, partial installation, arbitrary order dependence, regression
loss, rollback mismatch, budget overrun, network requirement, historical evaluator mutation, or
repository-test failure.

## Results

The declaration-blind baseline emitted every locked baseline output, scored 4/8 relative to the
candidate expectations, and falsely routed all four cross-root targets. The candidate scored
8/8 for an absolute target gain of 0.5, preserved all four own-root routes across both declared
roots, and rejected all four cross-root targets. The separate third-root probe was falsely
accepted by the baseline and rejected by the candidate in both package orders; the absent-scope
probe was rejected in both orders.

Unloaded and loaded regression accuracy remained 3/3. Candidate decisions were invariant across
both package orders, and unload restored all 16 target responses. The declaration-blind baseline
accepted all eight orderings of the four inconsistent declarations. The candidate rejected 8/8
with the locked errors before state installation, and every post-rejection probe observed a clean
state. The two in-process trials were identical.

The fixture occupied 7,697 bytes, the evaluator made zero external calls, and its single measured
invocation completed in 0.001980 seconds. Final repository checks passed 173 tests, validated 26
experiment records and 26 index-record matches, validated the expert template at the pinned date,
and passed the public-safety scan. These checks do not change the measured result.

## Interpretation

**Observation:** within the locked synthetic configuration, attaching a literal root to each
package prevents its leading wildcard from matching another package's root while both packages
remain routable in their own roots. Invalid root or literal-pattern declarations are rejected
before any expert state is installed.

**Inference:** the single global root fence from EXP-024 can be refined into package-local
matching eligibility without rewriting wildcard patterns or collapsing independent roots. This
supports a later, separate manifest-contract experiment; it does not establish that a declaration
is trustworthy or suitable for authorization.

## Limitations

The protocol cannot establish that a package's declaration is trustworthy, authorization-system
correctness, semantic policy interpretation, learned routing, natural-language capability,
concurrent atomicity, scalable performance, runtime safety, or behavior outside the locked
synthetic cases.

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines hierarchical paths as slash-separated segments and motivates treating the first segment
as a boundary. The primary [XACML 3.0 specification](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html#_Toc325047268)
defines policy applicability and combining behavior that motivate separating ownership
eligibility from later routing. Neither source defines Morpheus's root ownership, wildcard
grammar, specificity score, transaction rule, or synthetic expected outputs.

## Decision

`pass`
