# EXP-032 — Public expert-template v2 migration gate

- **Schema**: strict-v1
- **Date**: 2026-09-01
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned public template and synthetic routing fixture

## Question

Can a rooted v2 candidate derived from the current public v1 expert template pass stable
validation, exact reverse projection, pinned lifecycle, routing non-regression, and unload checks
without changing the public template during the experiment?

## Hypothesis

The current v1 template and its rooted v2 candidate will both validate at the pinned date
`2026-09-01`; the candidate will reverse-project exactly to the source v1 JSON and return exactly
`expired` on `2026-09-02`; a stable-v2 router will match the sidecar-root v1 baseline on two target
routes, one absent-scope regression, one exclusion, both package orders, and all four post-unload
responses; and two complete trials will repeat.

## Baseline

The baseline is the SHA-256-pinned public v1 template. For routing only, the deterministic
migration adds a literal root prefix to its include and exclude patterns while EXP-025's sidecar
entry carries that root. The candidate carries the same rooted patterns and root inside an
`expert-package-v2` manifest and uses EXP-031's stable-validator-native composition path. The
source template stays unchanged.

## Protocol

1. Pin the current public v1 template by SHA-256 and validate it at `2026-09-01`.
2. Deterministically create a v2 candidate by adding root `synthetic` and prefixing every scope
   include and exclude with that root; reject any reverse projection lacking the exact prefix.
3. Validate the candidate through the stable validator at `2026-09-01`, require exact reverse
   projection to the pinned v1 object, and require exactly `expired` at `2026-09-02`.
4. Compose the migrated template with one synthetic peer in both orders. Compare sidecar-root v1
   baseline and stable-native v2 outputs on two targets, one absent-scope regression, one
   exclusion, and four post-unload target responses.
5. Repeat the complete trial in process and require identical outputs.
6. Run exactly one measured evaluator invocation, followed by repository tests, record and index
   validators, pinned public-template validation, public-safety checks, and staged-diff review.

Only the Python standard library and repository-owned synthetic data are permitted. All dates
come from the fixture; wall-clock access is forbidden. No public template, stable validator,
historical evaluator, model, private datum, external service, training, network call, package
migration, or production runtime may change.

## Metrics

- exact baseline and candidate stable-validation outcomes at the pinned reference date;
- exact candidate reverse projection and next-day lifecycle error;
- target routing parity and correctness over two cases;
- parity on one absent-scope regression and one exclusion in both package orders;
- package-order invariance and four post-unload comparisons;
- repeatability across two in-process trials;
- combined fixture bytes, measured evaluator latency, compute class C0, and external-call count;
- repository test, validator, public-safety, and staged-diff status.

## Acceptance and stop criteria

Accept only if both manifests validate at `2026-09-01`; reverse projection is exact; the v2
candidate returns exactly `expired` at `2026-09-02`; target parity and correctness are 2/2;
regression and exclusion parity are 2/2 across both orders; target outputs are order-invariant;
rollback matches 4/4; both trials repeat; combined fixtures remain below 16 KiB; evaluation
finishes below one second with zero external calls; and every repository check passes.

Stop after two targets, one regression, one exclusion, two orders, four unload comparisons, two
in-process trials, and one measured invocation. Stop immediately on source-hash drift, validation
or projection mismatch, routing or rollback mismatch, unexpected lifecycle result, wall-clock or
network requirement, budget overrun, public-template mutation, or failed repository check. Do not
patch and rerun a failed measured protocol in this experiment.

## Results

`fail`. The single measured evaluator invocation stopped during first-order baseline composition,
before producing any routing output. The locked package builder supplied `knowledge_records` as
an object, while the historical composition kernel requires a non-empty list of records with
`id` and `value` fields. It raised exactly `knowledge_records must be a non-empty list`.

The source hash and fixture structure had passed their pre-execution checks, but target,
regression, exclusion, order, rollback, and repeatability metrics were not scored. The combined
fixture and pinned template occupied 1,976 bytes and the evaluator made zero external calls. The
failed invocation did not emit its internal latency metric because it stopped before the summary
path. The measured protocol was not patched or rerun.

## Interpretation

**Observation:** the failure came from the experiment adapter's record representation before the
candidate and baseline could be compared. It is a protocol-construction failure, not a routing,
validation, lifecycle, or projection result.

**Inference:** EXP-032 provides no evidence for or against public-template v2 migration. The
candidate must remain unpromoted. A new experiment may correct only the predeclared record shape,
pin the failed fixture as its baseline, and rerun the same bounded comparisons under a new ID.

## Limitations

The protocol can test only one mechanical prefix migration, structural validation, date-only
lifecycle behavior, exact synthetic routing, and unload behavior. It cannot establish declaration
authenticity, migration ergonomics, trusted clocks, authorization correctness, semantic routing,
runtime safety, natural-language capability, or self-improvement.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
distinguishes structural validation from application semantics, and the primary [TUF
specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
motivates a fixed reference time throughout one update workflow. Neither source defines this
migration transform, root policy, router, or synthetic expectations.

## Decision

`fail`
