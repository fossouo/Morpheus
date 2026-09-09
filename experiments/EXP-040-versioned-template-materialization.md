# EXP-040 — Versioned expert-template materialization gate

- **Schema**: strict-v1
- **Date**: 2026-09-09
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned public templates, EXP-039 evidence, and synthetic requests

## Question

Can a canonical v2 expert template be materialized at the unused versioned path with one pinned
synthetic consumer while preserving the six locked historical v1 dependency edges and proving
bounded validation, lifecycle, routing, rollback, and removal behavior?

## Hypothesis

EXP-039's in-memory-only baseline has zero materialized v2 consumers. The candidate will provide
one exact pinned consumer of a canonical versioned artifact, preserve all six historical v1 edges,
validate on the pinned reference date, expire the next day, reverse-project exactly to public v1,
route every locked request in either package order, unload cleanly, and fail closed when the v2
artifact is removed from an isolated temporary copy without disturbing v1.

## Baseline

The baseline is the SHA-256-pinned EXP-039 result and fixture. It validated an in-memory v2
candidate at an unused path but explicitly left that path unmaterialized and had no consumer
pinned to a versioned artifact. The candidate changes only that state: it adds the canonical
rooted v2 template and this new synthetic consumer while keeping public v1, the immutable v1
snapshot, all historical fixtures, validators, and routing kernels fixed.

## Protocol

1. Verify pins for EXP-039, its fixture, public v1, the immutable v1 snapshot, and the candidate
   versioned template.
2. Recount only EXP-039's four locked historical referrers and require its exact six typed v1
   edges to remain present.
3. Derive canonical v2 again in memory from public v1 and require byte equality with the real
   versioned artifact, exact reverse projection, structural validation on `2026-09-01`, and
   expiry on `2026-09-02`.
4. Require the new synthetic consumer to contain exactly one SHA-256 pin to the materialized v2
   template, compared with EXP-039's zero-consumer baseline.
5. Compose the materialized template with one deterministic peer in both orders; score two
   held-out targets, one absent-scope regression, one disjoint-exclusion precedence probe, and
   unload rollback.
6. In an isolated temporary directory, load exact v1 and v2 copies, remove only v2, require the
   v2 consumer to fail closed with the locked error, and require v1 to remain byte-exact.
7. Repeat the complete trial inside one measured command.

Reproduce with `python3 scripts/evaluate_versioned_template_materialization.py`. Use only
repository data, temporary files, and the Python standard library. No model calls, training,
downloads, services, accelerators, subprocesses, external calls, historical rewrites, or public-v1
replacement are allowed.

## Metrics

- Materialized pinned consumers: baseline 0; candidate target 1.
- Historical v1 edges: 6/6, comprising three consumer and three experiment-evidence edges across
  four locked referrer files.
- Canonical byte equality, v1 snapshot equality, v2 validation, next-day expiry, and exact reverse
  projection.
- Routing: 4/4 target responses, 2/2 regressions, 2/2 exclusion-precedence responses, package-order
  invariance, and 4/4 post-unload responses.
- Removal: initial v2 load, exact missing-artifact error after removal, v2 absence, and preserved
  v1 load in the isolated copy.
- Complete-trial repeatability, combined pinned input bytes, evaluator time, C0 class, and zero
  external calls. No language-quality, inference, energy, or general capability metric is claimed.

## Acceptance and stop criteria

Accept only if the materialized-consumer count improves from 0 to exactly 1; all six locked v1
edges and the byte-exact v1 snapshot remain intact; the real v2 file equals the canonical
derivation, validates on the pinned date, expires the next day, and reverse-projects exactly; all
4 target, 2 regression, 2 exclusion-precedence, and 4 rollback comparisons pass; both orders are
identical; temporary removal returns exactly `versioned-template-missing` while v1 survives;
complete trials repeat; pinned inputs stay below 32 KiB; measured time stays below one second;
external calls are zero; and publication checks pass.

Stop on pin drift, any changed or missing historical edge, a second v2 consumer pin, canonical or
projection mismatch, validation or lifecycle failure, routing, order, rollback, or removal mismatch,
repository mutation by the evaluator, exception, external call, or budget overrun. The measured
evaluator command may run only once and must not be tuned or rerun after failure. Subsequent tests
are reproducibility checks, not replacement measurements.

## Results

`pass`. The EXP-039 baseline had zero materialized v2 consumers; the candidate fixture supplied
one exact SHA-256 consumer pin to the new canonical versioned artifact. All six locked historical
v1 dependency edges remained present: three consumer and three experiment-evidence edges across
four referrer files. Public v1 remained valid and byte-identical to its immutable snapshot.

The materialized v2 bytes exactly matched a fresh canonical derivation from public v1. The artifact
validated at `2026-09-01`, returned `expired` at `2026-09-02`, and reverse-projected exactly to v1.
Both package orders produced 4/4 correct target responses, 2/2 absent-scope regressions, and 2/2
correct disjoint-exclusion precedence responses; order invariance held and unload restored 4/4
baseline responses.

In the isolated removal trial, v2 loaded before deletion, then returned exactly
`versioned-template-missing`; v2 was absent and v1 remained loadable and byte-exact. Complete
trials repeated. Pinned inputs were 13,874 bytes, the single measured invocation took 0.015447
seconds, and external calls were zero. The evaluator was not tuned or rerun.

The first full repository-suite invocation then exposed one integration failure: EXP-039's
historical evaluator recomputed its measurement-time `versioned path unused` observation against
the now-materialized repository. That non-monotonic observation was renamed and frozen as the
measurement-time value, with current availability reported separately. No EXP-040 fixture,
artifact, threshold, routing path, measured result, or historical evidence file changed, and the
measured evaluator was not rerun.

## Interpretation

**Observation:** a separately addressed canonical v2 artifact acquired one pinned consumer without
changing the six locked v1 dependency edges. Its structural, date-only lifecycle, exact synthetic
routing, unload, and isolated removal checks all met the preregistered thresholds.

**Inference:** the versioned v2 path is ready to publish as an opt-in quarantined template while
public v1 remains the unchanged default. This is evidence for bounded repository integration and
reversibility only; it is not evidence of broader behavioral capability or safe production use.

## Limitations

This is a repository migration-safety experiment over a synthetic exact-lookup route. It cannot
establish source authenticity, trusted clocks, authorization correctness, semantic or learned
routing, natural-language capability, production safety, migration ergonomics for other consumers,
or self-improvement. SHA-256 is used only for local byte-identity and dependency-drift assertions.
The primary [TUF specification](https://theupdateframework.github.io/specification/latest/)
motivates separately addressable incompatible formats and hash-bound targets, but it does not
define this repository's template policy. The primary
[JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-validation-01)
describes structural validation concepts but does not validate Morpheus's routing behavior.

## Decision

`pass`

## Next step

Keep public v1 as the default and the new v2 path opt-in. The next smallest experiment should add a
second independently authored synthetic v2 consumer and test incompatible-version discovery,
selection, and removal without changing either template or weakening hash-bound loading.
