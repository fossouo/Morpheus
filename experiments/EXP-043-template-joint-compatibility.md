# EXP-043 — Joint template compatibility intersection

- **Schema**: strict-v1
- **Date**: 2026-09-12
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-042 evidence, public v2 template, and synthetic compatibility ranges

## Question

Can two consumers select one deterministic highest template version from the intersection of their
declared compatible ranges, while rejecting an empty intersection and an ambiguous joint maximum
before any package is loaded?

## Hypothesis

Independent highest-compatible selection will answer exactly one of five held-out joint-selection
cases correctly. The joint candidate will answer all five by selecting the unique highest descriptor
that satisfies both consumers, preserving an exact constraint, rejecting an empty intersection, and
rejecting a tied highest descriptor before any load attempt.

## Baseline

The baseline applies EXP-042-style highest-compatible selection to each consumer separately and
accepts a result only when both independent selections name the same descriptor. The candidate sees
the same fixed descriptors and policies, computes descriptor membership in both consumer sets, and
then requires one descriptor at the highest version in the intersection. Neither path reads or
materializes the selected package.

## Protocol

1. Verify SHA-256 pins for EXP-042, its fixture, and the public v2 template; keep every repository
   template and historical evidence file unchanged.
2. Derive five descriptor hashes in memory for four canonical numeric versions, including a second
   path at `1.1.0`; require every embedded schema, version, hash, and pinned-date structural
   validation to match before scoring.
3. Lock five two-consumer cases: two partially overlapping ranges with different independent
   maxima, one exact-plus-range agreement, one empty intersection, and one tied highest descriptor.
4. Compare independent highest selection with joint highest selection, assert zero package-load
   attempts, and repeat the complete trial within one measured command.

Reproduce with `python3 scripts/evaluate_template_joint_compatibility.py`. Use only repository data
and the Python standard library. No model calls, training, downloads, services, accelerators,
subprocesses, external calls, template edits, historical rewrites, package materialization, or
package loading are allowed.

## Metrics

- Selection: independent baseline exactly 1/5; joint candidate 5/5.
- Coverage: both partial overlaps, exact constraint, empty intersection, and ambiguous joint maximum
  produce their locked outcomes for exactly two consumers per case.
- Safety: zero package-load attempts before a unique joint result.
- Complete-trial repeatability, pinned input bytes below 32 KiB, measured time below one second, C0
  class, and zero external calls. No routing, language quality, inference, energy, production, or
  general capability metric is claimed.

## Acceptance and stop criteria

Accept only if all five descriptors remain hash-bound and structurally valid on the pinned date;
the baseline scores exactly 1/5 and the candidate 5/5; every locked case outcome matches; no package
load is attempted; trials repeat; pinned inputs stay below 32 KiB; measured time stays below one
second; external calls are zero; and publication checks pass.

Stop on pin drift, a changed public template, noncanonical version acceptance, an invalid derived
manifest, baseline or candidate score drift, order-dependent intersection, empty-intersection or
ambiguity acceptance, any package load, exception, repository mutation by the evaluator, external
call, or budget overrun. The measured evaluator command may run only once and must not be tuned or
rerun after failure. Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`pass`. All five descriptors remained hash-bound to structurally valid in-memory derivations on
the pinned date. The independent baseline answered 1/5 cases correctly; the joint candidate
answered 5/5. It selected `1.1.0` and `1.0.2` for the two partially overlapping range pairs,
preserved the exact `1.0.2` constraint, rejected the empty intersection, and rejected the two-way
`1.1.0` joint maximum.

Every case had exactly two consumers and the complete trial repeated. Package-load attempts and
external calls were both zero. Pinned inputs were 19,648 bytes and the single measured invocation
took 0.001685 seconds. The evaluator was not tuned or rerun.

## Interpretation

**Observation:** on the five locked synthetic cases, intersecting the two declared acceptable
descriptor sets before choosing their unique highest version prevented independent-selection
disagreement and failed closed on both no common descriptor and a tied joint maximum.

**Inference:** a two-consumer joint gate can remain quarantined for a subsequent hash-bound
materialization test. This does not show that the declared ranges are semantically correct or that
the policy generalizes beyond the locked catalogs.

## Limitations

The protocol covers only two consumers, inclusive ranges over canonical numeric core versions, and
small synthetic descriptor catalogs. It excludes prerelease/build metadata and cannot establish
semantic compatibility, general dependency solving, provenance authenticity, concurrent catalog
mutation safety, production readiness, behavioral capability, or self-improvement. The primary
[Semantic Versioning 2.0.0 specification](https://semver.org/spec/v2.0.0.html) defines numeric
version precedence and motivates bounded dependency ranges, but it does not define this joint
policy. The primary [TUF specification](https://theupdateframework.github.io/specification/latest/)
motivates hash-bound targets, but it does not establish this resolver's safety.

## Decision

`pass`

## Next step

Keep independent selection as the default and the joint resolver quarantined. The next smallest
experiment should materialize one jointly selected artifact in isolation, then remove or mutate it
while a lower jointly compatible artifact remains, and require a hash-bound failure without silent
downgrade.
