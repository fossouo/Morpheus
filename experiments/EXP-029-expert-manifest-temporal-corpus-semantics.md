# EXP-029 — Expert-manifest temporal corpus semantics

- **Schema**: strict-v1
- **Date**: 2026-08-29
- **Status**: complete
- **Compute**: C0
- **Data**: repository-owned synthetic v1 manifests and pinned lifecycle dates

## Question

Can the historical v1 corpus represent structural compatibility separately from pinned-date
lifecycle acceptance for every source, resolving the ambiguity that stopped EXP-028?

## Hypothesis

All four SHA-256-pinned historical v1 sources will remain structurally valid. Across sixteen
locked lifecycle cases, the structure-only baseline will classify exactly 11/16 and falsely
accept five expired states; the date-aware candidate will match all 16 exact error expectations
with zero false accepts. At EXP-028's pinned date, the candidate will classify three sources as
active and one as expired.

## Baseline

The baseline is the EXP-026 structural-compatibility interpretation: it calls the unchanged v1
validator without a reference date and reuses that result as lifecycle state. The candidate uses
the same unchanged validator but keeps structural errors as one output and supplies each locked
reference date for a separate lifecycle output. This isolates temporal corpus semantics without
retrying v2 promotion or changing validation policy.

## Protocol

1. Pin the public template and the three repository-owned v1 base manifests used by EXP-026 with
   SHA-256, along with their expected `expires_on` values and empty structural error lists.
2. For each source, lock the day before expiry, the expiry day, the day after expiry, and the
   EXP-028 reference date `2026-08-28`, for sixteen lifecycle cases total.
3. Require the fixture validator to derive every expected lifecycle error from the existing
   inclusive date-only policy: active through `expires_on`, then exactly `expired`.
4. Compare the structure-only baseline with the date-aware candidate, while scoring structural
   compatibility independently.
5. Repeat the complete trial in process and require identical outputs.
6. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned public-template validation, public-safety checks, and staged diff review.

Only the Python standard library and repository-owned synthetic fixtures are permitted. The
evaluator receives every reference date as fixture data and must not read a wall clock. No stable
validator, v2 contract, public template, model, external service, private datum, training, network
call, package migration, or production runtime may change.

## Metrics

- exact structural error-list matches and acceptance across four historical sources;
- exact lifecycle error-list matches across sixteen pinned-date cases;
- baseline accuracy and false accepts among expired states;
- candidate false accepts, expiry-day acceptance, and next-day rejection;
- exact classifications at the EXP-028 reference date;
- repeatability across two in-process trials;
- fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if all four source hashes and expiry values match; structural outcomes are accepted
and exactly match 4/4; the baseline scores exactly 11/16 with five false accepts; the candidate
matches 16/16 exact lifecycle errors with zero false accepts; all four expiry-day cases are
accepted and all four next-day cases are rejected; the EXP-028 date yields exactly three active
and one expired source with 4/4 exact matches; both trials match; the fixture is below 16 KiB;
evaluation finishes below one second with zero external calls; and every repository check passes.

Stop after four sources, sixteen lifecycle cases, two in-process trials, and one measured
invocation. Stop immediately on source-hash or expiry drift, a structural compatibility change,
an unexpected lifecycle error, wall-clock access, budget overrun, network requirement, stable-
validator or v2-promotion mutation, or repository-test failure. Do not patch and rerun a failed
measured protocol in this experiment.

## Results

All four pinned source hashes and expiry values matched. Every source remained structurally
accepted with exact 4/4 empty-error parity. Across the sixteen lifecycle cases, the structure-
only baseline classified 11/16 correctly and falsely accepted all five expired states. The
date-aware candidate matched 16/16 exact error lists with zero false accepts.

All four manifests were accepted on their expiry date and rejected with exactly `expired` on
the next day. At EXP-028's pinned date, the candidate classified the three `2026-09-01` sources
as active and the `2026-08-09` source as expired, for 4/4 exact outcomes. Both in-process trials
were identical. The fixture occupied 2,898 bytes, the evaluator made zero external calls, and
the single measured invocation completed in 0.002794 seconds.

## Interpretation

**Observation:** within the locked repository corpus, structural validity was invariant across
all four sources while lifecycle acceptance changed only with the explicit reference date. A
structure-only result could not identify any of the five expired cases.

**Inference:** the historical corpus can state structural compatibility and temporal lifecycle
expectations as separate dimensions without changing the stable validator. This resolves the
specific ambiguity that stopped EXP-028, but it does not by itself justify retrying or promoting
the v2 contract.

## Limitations

The protocol can distinguish structural validation from date-only lifecycle acceptance on four
synthetic repository sources. It cannot establish source authenticity, clock trust, migration
safety, authorization correctness, semantic routing, runtime safety, natural-language capability,
or self-improvement.

The primary [TUF specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
records one fixed time for an update workflow and evaluates expiry against it, motivating explicit
pinned reference values. The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines structural validation concepts. Neither source defines Morpheus's date-only policy,
historical corpus, expected errors, or promotion decision.

## Decision

`pass`
