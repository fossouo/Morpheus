# EXP-030 — Expert-manifest v2 temporal promotion

- **Schema**: strict-v1
- **Date**: 2026-08-30
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned synthetic manifest, temporal, routing, and rollback fixtures

## Question

Can the opt-in `expert-package-v2` contract pass a stable-validator promotion gate when
structural compatibility and pinned-date lifecycle acceptance are scored separately, while
preserving the held-out routing, invalid-composition, and rollback behavior from EXP-027?

## Hypothesis

The frozen v1-only baseline will classify 8/10 structural cases and reject both valid v2
manifests. The candidate will classify 10/10 with zero false accepts and every locked error,
match all 16 separate lifecycle expectations with zero false accepts, classify three historical
sources active and one expired at the pinned promotion date, preserve 8/8 targets and 3/3
regressions, reject all eight ordered invalid compositions with clean state, restore all 16
post-unload responses, and exactly match the quarantined integration trial.

## Baseline

The structural baseline freezes the stable pre-promotion behavior: v1 manifests are validated by
the existing contract and opt-in v2 manifests are unsupported. The candidate is the unchanged
EXP-028 v2 implementation, but historical compatibility now consumes EXP-029's independent
structural and lifecycle expectations instead of treating current-date acceptance as structural
parity. EXP-027 remains the behavioral baseline for routing and rollback.

## Protocol

1. Pin by SHA-256 the complete EXP-026 structural fixture, EXP-027 integration fixture, and
   EXP-029 temporal-corpus fixture.
2. Replay ten v2 structural cases against the frozen v1-only baseline and unchanged candidate,
   including the two valid forms and eight locked invalid forms with exact errors.
3. Replay all four historical v1 sources as invariant structural checks and all sixteen pinned
   lifecycle cases, including the EXP-028 promotion date `2026-08-28`.
4. Replay EXP-027 in fixture and reverse order, comparing eight held-out targets, three
   regressions, eight ordered invalid compositions, clean state, and sixteen unload responses.
5. Repeat the complete trial in process and require byte-for-byte-equivalent JSON results.
6. Run exactly one measured evaluator invocation. Promote v2 into the stable validator only if
   every locked threshold passes; keep the public expert-package template on v1.
7. After a passing measured run, execute repository tests, record and index validators, pinned
   template validation, public-safety checks, and staged-diff review without rerunning or patching
   the measured protocol.

Only the Python standard library and repository-owned synthetic fixtures are permitted. All dates
come from fixtures; wall-clock access is forbidden. No model, private datum, service, training,
network call, package migration, production runtime, or public-template version change is allowed.

## Metrics

- structural accuracy, valid-v2 false rejects, false accepts, and exact locked errors over ten
  cases;
- exact structural parity over four historical v1 sources and lifecycle parity over sixteen
  pinned-date cases, including active/expired counts at the promotion date;
- exact target and regression parity, invalid-composition rejection, clean states, and rollback;
- complete candidate/quarantine trial equality and repeatability across two in-process trials;
- combined fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- stable-validator candidate parity, repository tests, validators, public safety, and diff status.

## Acceptance and stop criteria

Accept only if the baseline scores exactly 8/10 and rejects both valid v2 manifests; the candidate
scores 10/10 with zero false accepts and all ten locked error expectations; historical structure
matches 4/4; lifecycle errors match 16/16 with zero false accepts; the promotion date yields
exactly three active and one expired source with 4/4 exact outcomes; targets match 8/8;
regressions match 3/3; eight invalid compositions are rejected with eight clean states; rollback
matches 16/16; the complete candidate and quarantine integration trials are equal; both trials
repeat; combined fixtures remain below 16 KiB; evaluation finishes below one second with zero
external calls; the promoted stable validator matches the locked candidate; and every repository
check passes.

Stop after ten structural cases, four historical sources, sixteen lifecycle cases, eight targets,
three regressions, eight ordered invalid compositions, sixteen unload comparisons, two in-process
trials, and one measured invocation. Stop immediately on source-hash drift, a false accept,
behavioral or rollback mismatch, unexpected lifecycle result, partial installation, wall-clock or
network requirement, budget overrun, public-template mutation, or failed repository check. Do not
patch and rerun a failed measured protocol.

## Results

The frozen v1-only baseline classified 8/10 structural cases and rejected both valid v2
manifests. The candidate classified 10/10, produced all ten locked error expectations, and made
zero false accepts. The four historical v1 sources retained exact structural parity, and the
candidate matched all 16 pinned lifecycle expectations with zero false accepts. At the pinned
promotion date, three sources were active and one was expired, matching 4/4 expectations.

The candidate matched EXP-027 on 8/8 held-out targets and 3/3 regressions. It rejected all eight
ordered invalid compositions before state installation, left eight clean states, restored all
16 post-unload responses, and produced a complete integration trial equal to the quarantined
baseline. Both in-process trials were identical. The combined fixtures occupied 8,632 bytes, the
evaluator made zero external calls, and the single measured invocation completed in 0.012891
seconds.

Every locked threshold passed, so the v2 contract was promoted into the stable validator. The
public expert-package template remains on v1. The post-promotion repository suite, validators,
template check, public-safety scan, and staged-diff review all passed.

## Interpretation

**Observation:** within the locked synthetic configuration, separating invariant v1 structure
from pinned-date lifecycle state removed EXP-028's false 4/4 current-date premise. The candidate
then preserved every structural, temporal, routing, transactional, and rollback expectation.

**Inference:** the opt-in rooted v2 contract can join the stable validator without migrating the
public v1 template or changing the tested v1 outcomes. This is a contract promotion supported by
locked synthetic evidence, not a new behavioral capability or evidence of autonomous improvement.

## Limitations

This protocol can test only deterministic structural, date-only lifecycle, exact synthetic
routing, transactional rejection, and unload behavior on repository-owned fixtures. It cannot
establish declaration authenticity, trusted clocks, migration safety, authorization correctness,
semantic routing, scalable performance, runtime safety, natural-language capability, or
self-improvement.

The primary [TUF specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
motivates using one fixed time during an update workflow, and the primary [JSON Schema 2020-12
validation specification](https://json-schema.org/draft/2020-12/json-schema-validation) motivates
separating structural constraints from application lifecycle policy. Neither source defines
Morpheus's v2 contract, date-only expiry rule, synthetic labels, or promotion decision.

## Decision

`pass`
