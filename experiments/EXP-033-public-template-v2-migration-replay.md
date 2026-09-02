# EXP-033 — Public expert-template v2 migration replay

- **Schema**: strict-v1
- **Date**: 2026-09-02
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-032 fixture and public template plus synthetic routing cases

## Question

Does changing only EXP-032's `knowledge_records` adapter output from mappings to the historical
list-of-`{id, value}` contract allow the previously blocked public-template v2 migration gate to
score and pass its unchanged validation, projection, lifecycle, routing, order, and unload checks?

## Hypothesis

The pinned EXP-032 baseline will reproduce exactly `knowledge_records must be a non-empty list`.
After the sole adapter-shape repair, both manifests will validate at `2026-09-01`; the candidate
will reverse-project exactly and return only `expired` at `2026-09-02`; the stable-v2 candidate
will match the sidecar-root v1 baseline on both target routes, the absent-scope regression, the
exclusion, both package orders, and all four unload responses; and two complete trials will match.

## Baseline

The baseline is the SHA-256-pinned EXP-032 fixture and its default evaluator path, which failed
before routing on object-shaped `knowledge_records`. The candidate uses that same fixture,
template, migration, manifests, dates, requests, expected outputs, kernels, and orderings. It
changes only each knowledge-record mapping into a deterministically sorted list of records with
the same identifiers and values.

## Protocol

1. Pin and validate the unchanged EXP-032 fixture and its pinned public v1 template.
2. Reproduce the exact EXP-032 baseline failure through the unchanged default evaluator path.
3. Build the same two candidate packages, then transform only each knowledge-record container
   from a mapping into a sorted list of `{id, value}` records; verify manifest equality and exact
   identifier-value preservation.
4. Replay the EXP-032 stable validation, reverse projection, next-day lifecycle, two target,
   one regression, one exclusion, two-order, and four-unload comparisons.
5. Repeat the repaired complete trial once in process and require exact equality.
6. Run exactly one measured replay invocation, followed by the repository suite, record and index
   validators, pinned template validation, public-safety scan, and staged-diff review.

Only the Python standard library and repository-owned synthetic data are permitted. Fixture dates
replace wall-clock access. No public template, stable validator, routing kernel, historical default
behavior, model, private datum, external service, training, network call, or production runtime may
change during the measured experiment.

## Metrics

- exact reproduction of the EXP-032 baseline failure and proof that only record shape changed;
- exact baseline and candidate stable-validation outcomes at the pinned reference date;
- exact reverse projection and next-day lifecycle error;
- target routing parity and correctness over two cases;
- parity on one absent-scope regression and one exclusion in both orders;
- package-order invariance and four post-unload comparisons;
- repeatability across two repaired in-process trials;
- combined replay fixture, source fixture, and template bytes, evaluator latency, compute class
  C0, and external-call count;
- repository tests, validators, pinned-template, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if the pinned baseline reproduces its exact failure; the adapter-only invariant holds;
both manifests validate at `2026-09-01`; reverse projection is exact; the candidate returns exactly
`expired` at `2026-09-02`; target parity and correctness are 2/2; regression and exclusion parity
are each 2/2; target outputs are order-invariant; rollback matches 4/4; both repaired trials match;
combined fixtures remain below 16 KiB; evaluation finishes below one second with zero external
calls; and every repository check passes.

Stop after one baseline reproduction, two targets, one regression, one exclusion, two orders, four
unload comparisons, two repaired trials, and one measured invocation. Stop immediately on source
hash drift, any change beyond record-container shape, validation or projection mismatch, routing or
rollback mismatch, unexpected lifecycle result, wall-clock or network requirement, budget overrun,
public-template mutation, or failed repository check. Do not patch and rerun a failed measured
protocol in this experiment. Passing the gate does not itself authorize changing the public
template; that change must preserve historical reproducibility and pass the full repository suite.

## Results

`fail`. The pinned baseline reproduced exactly `knowledge_records must be a non-empty list`, and
the adapter-only invariant passed. The repair allowed the complete routing protocol to run, but
exclusion parity and correctness scored 0/2, below the locked 2/2 threshold.

Both manifests validated at `2026-09-01`; the candidate returned exactly `expired` at
`2026-09-02`; reverse projection was exact; target parity and correctness were 2/2; regression
parity and correctness were 2/2; target outputs were order-invariant; rollback matched 4/4; and
both repaired trials matched. The combined fixtures and template occupied 2,288 bytes, the single
measured invocation took 0.001884 seconds, and it made zero external calls. The evaluator and
locked fixture were not patched or rerun.

## Interpretation

**Observation:** changing only record-container shape removed EXP-032's construction failure and
exposed a second locked mismatch: the two exclusion checks failed while every other scored
criterion passed.

**Inference from static code inspection:** the exclusion request matches the template's rooted
exclude pattern but not its disjoint rooted include pattern. The locked package-owned router
returns `scope-not-found` when no include matches, before it filters exclusions. Thus the baseline
and candidate remain behaviorally equal, but both conflict with the fixture's locked
`scope-excluded` expectation. This is a second protocol-fixture failure, not evidence against v2
validation or projection and not sufficient evidence for public-template migration.

## Limitations

The protocol covers one mechanical prefix migration, one historical record contract, structural
validation, date-only lifecycle behavior, exact synthetic routing, and unload behavior. It cannot
establish source authenticity, migration ergonomics, trusted clocks, authorization correctness,
semantic routing, runtime safety, natural-language capability, or self-improvement.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
distinguishes structural validation from application semantics, and the primary [TUF
specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
motivates a fixed reference time throughout one update workflow. Neither source defines this
adapter representation, migration transform, root policy, router, or synthetic expectations.

## Decision

`fail`
