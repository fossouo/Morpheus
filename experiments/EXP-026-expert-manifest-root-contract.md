# EXP-026 — Expert-manifest root contract

- **Schema**: strict-v1
- **Date**: 2026-08-26
- **Status**: complete
- **Compute**: C0
- **Data**: synthetic expert manifests and repository-owned historical v1 fixtures

## Question

Can an opt-in expert-manifest contract require a package-owned literal root and reject missing,
empty, wildcard, nested, and literal-pattern-mismatched roots while preserving the unchanged
validation behavior of valid historical `expert-package-v1` manifests?

## Hypothesis

A root-presence-only baseline will classify 4/10 locked cases correctly and falsely accept six
invalid rooted manifests. The candidate will classify 10/10, produce the locked error for every
case, make zero false accepts, and exactly match the existing validator on four valid historical
v1 sources.

## Baseline

The baseline applies the unchanged v1 structural validator to all shared fields and, for the
opt-in v2 shape, checks only that `root` is a present non-empty string. This isolates whether
segment grammar and include/exclude consistency add discrimination beyond field presence. Both
conditions route historical v1 manifests through the unchanged stable validator.

## Protocol

1. Lock one synthetic v2 base manifest containing one literal root, root-owned literal scope
   patterns, and leading whole-segment wildcard patterns.
2. Apply ten deterministic cases: two valid forms plus missing, empty, whole-wildcard,
   partial-wildcard, nested, dot-segment, include-mismatch, and exclude-mismatch mutations.
3. Compare the presence-only baseline with a quarantined candidate that requires a canonical
   single literal root and permits each scope pattern to begin only with that root or one whole-
   segment wildcard.
4. Load four repository-owned valid v1 sources and require the candidate's error list to equal
   the unchanged stable validator's error list exactly.
5. Repeat the complete trial in process and require identical decisions.
6. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned expert-template validation, public-safety checks, and staged diff review.

Only the Python standard library and repository-owned synthetic fixtures are permitted. No stable
validator or template is changed in this experiment. No model, external service, private datum,
training, network call, or production runtime is allowed.

## Metrics

- exact classification accuracy and false accepts across ten locked cases;
- exact locked-error presence for all ten candidate decisions;
- exact error-list parity and acceptance across four historical v1 sources;
- repeatability across two in-process trials;
- fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if the baseline scores exactly 4/10 with six false accepts; the candidate scores
10/10 with zero false accepts and all ten locked error expectations; all four historical v1
sources remain accepted with exact error-list parity; both trials are identical; the fixture
stays below 16 KiB; evaluation finishes below one second with zero external calls; and every
repository check passes.

Stop after ten cases, four historical sources, two in-process trials, and one measured evaluator
invocation. Stop immediately on a candidate false accept, any v1 parity change, fixture or time
budget overrun, network requirement, stable-validator mutation, or repository-test failure. Do
not patch and rerun a failed measured protocol in this experiment.

## Results

The presence-only baseline classified 4/10 cases correctly and falsely accepted six invalid
rooted manifests. The candidate classified 10/10, produced all ten locked error expectations,
and made zero false accepts. Both valid v2 forms were accepted; missing, empty, whole-wildcard,
partial-wildcard, nested, dot-segment, include-mismatch, and exclude-mismatch forms were rejected.

All four historical v1 sources remained accepted, and the candidate's error lists matched the
unchanged stable validator exactly in 4/4 comparisons. The two in-process trials were identical.
The fixture occupied 3,678 bytes, the evaluator made zero external calls, and its single measured
invocation completed in 0.002769 seconds.

## Interpretation

**Observation:** within the locked synthetic configuration, a non-empty root field alone did not
distinguish wildcard, nested, dot-segment, or literal-pattern mismatches. The candidate's
single-literal-segment and scope-consistency rules rejected all such cases without changing the
four checked v1 outcomes.

**Inference:** the package-owned routing behavior from EXP-025 can be represented by a backward-
compatible opt-in manifest contract in this narrow fixture. This supports a later promotion
experiment; it does not justify changing the stable validator from this structural result alone.

## Limitations

The protocol can test only structural discrimination and backward compatibility on four
repository-owned v1 sources. It cannot establish declaration trust, authorization correctness,
semantic routing, migration safety, scalable performance, runtime safety, natural-language
capability, or self-improvement.

The primary [URI generic syntax specification](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)
defines hierarchical paths as sequences of segments separated by slashes and motivates the
narrow segment grammar. The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines structural validation concepts that motivate distinguishing required properties from
value constraints. Neither source defines Morpheus's root ownership, wildcard policy, version
compatibility, expected errors, or synthetic labels.

## Decision

`pass`
