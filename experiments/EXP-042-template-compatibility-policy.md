# EXP-042 — Consumer-declared template compatibility policy

- **Schema**: strict-v1
- **Date**: 2026-09-11
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-041 evidence, public v2 template, and synthetic version catalogs

## Question

Can a consumer-declared policy select the deterministic highest compatible patch or minor
template version while preserving exact selection, rejecting a tied highest version, and failing
closed rather than silently downgrading after removal?

## Hypothesis

The exact-only baseline will answer exactly one of five held-out selection cases correctly. The
candidate will answer all five by preserving exact lookup, selecting the highest compatible patch
and minor versions, rejecting an empty compatible set and a tied highest version, and returning a
pinned-artifact-missing error after removal even though lower compatible artifacts remain.

## Baseline

The baseline is EXP-041-style exact schema/path/hash selection extended only with an exact numeric
version field; it rejects compatibility policies. The candidate sees the same fixed catalogs and
bytes, interprets only canonical three-component numeric versions, filters by the consumer's
declared schema, major version, and minimum version, then requires one descriptor at the highest
compatible version before loading it by path and SHA-256.

## Protocol

1. Verify SHA-256 pins for EXP-041, its fixture, and the public v2 template; keep all repository
   templates and historical evidence unchanged.
2. Derive four temporary artifacts from the pinned v2 bytes: versions `1.0.0`, `1.0.2`, `1.1.0`,
   and a second path for `1.1.0`. Require every derived byte hash, embedded schema and version,
   and pinned-date structural validation to match before scoring.
3. Lock three catalogs: patch-only, patch-plus-minor, and a catalog with two descriptors tied at
   the highest version. Compare the exact-only baseline with the candidate on one exact case,
   two compatible-selection cases, one no-match case, and one highest-version ambiguity case.
4. In an isolated temporary directory, select `1.1.0`, remove only that selected file, verify
   lower compatible files remain, and repeat the same policy without changing the catalog.
5. Repeat the complete trial within one measured command.

Reproduce with `python3 scripts/evaluate_template_compatibility_policy.py`. Use only repository
data, temporary files, and the Python standard library. No model calls, training, downloads,
services, accelerators, subprocesses, external calls, template edits, or historical rewrites are
allowed.

## Metrics

- Validation: four of four derived descriptors load hash-bound artifacts whose embedded schema
  and version match and whose manifests validate on the pinned date.
- Selection: exact-only baseline exactly 1/5; candidate 5/5, including highest compatible patch,
  highest compatible minor, no-match rejection, and tied-highest rejection.
- Removal: `1.1.0` selects before removal; afterward the result is exactly
  `error:pinned-template-missing`, lower compatible files remain, and no downgrade occurs.
- Complete-trial repeatability, pinned input bytes below 32 KiB, measured time below one second,
  C0 class, and zero external calls. No routing, language quality, inference, energy, production,
  or general capability metric is claimed.

## Acceptance and stop criteria

Accept only if all four derived artifacts validate and remain hash-bound; the baseline scores
exactly 1/5 and the candidate 5/5; exact, patch, minor, no-match, and ambiguity outcomes all match;
removal returns the exact locked error while lower files remain and no downgrade occurs; trials
repeat; pinned inputs stay below 32 KiB; measured time stays below one second; external calls are
zero; and publication checks pass.

Stop on pin drift, a changed public template, noncanonical version acceptance, invalid derived
manifest, baseline or candidate score drift, nondeterministic highest selection, ambiguity
acceptance, fallback after removal, exception, repository mutation by the evaluator, external
call, or budget overrun. The measured evaluator command may run only once and must not be tuned or
rerun after failure. Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`pass`. All four derived descriptors produced hash-bound artifacts with matching embedded schema
and version and valid manifests on the pinned date. The exact-only baseline answered 1/5 cases
correctly; the candidate answered 5/5. It preserved exact `1.0.2` selection, chose `1.0.2` from
the patch catalog and `1.1.0` from the minor catalog, rejected a minimum of `1.2.0` with no match,
and rejected the two-way `1.1.0` highest-version tie.

Before isolated removal, the compatible policy selected the pinned `1.1.0` artifact. After only
that file was removed, it returned exactly `error:pinned-template-missing` while both lower
compatible files remained; it did not silently downgrade. Complete trials repeated. Pinned inputs
were 20,093 bytes, the single measured invocation took 0.005094 seconds, and external calls were
zero. The evaluator was not tuned or rerun.

## Interpretation

**Observation:** on the three locked numeric versions, a consumer-declared minimum and major
policy selected the unique highest compatible descriptor and failed closed for both a tied maximum
and removal of the selected artifact.

**Inference:** a minimal deterministic compatibility policy can be quarantined alongside exact
selection for broader synthetic dependency cases. This does not justify replacing exact selection
or claiming that numeric compatibility implies semantic compatibility.

## Limitations

The protocol covers only canonical numeric core versions and caller-declared policies over small
synthetic catalogs. It excludes prerelease/build metadata and cannot establish semantic
compatibility, dependency solving, provenance authenticity, concurrent removal safety,
production readiness, behavioral capability, or self-improvement. The primary
[Semantic Versioning 2.0.0 specification](https://semver.org/spec/v2.0.0.html) defines numeric
version precedence, but it does not define this compatibility policy. The primary
[TUF specification](https://theupdateframework.github.io/specification/latest/) motivates
hash-bound targets, but it does not establish this resolver's safety.

## Decision

`pass`

## Next step

Keep exact selection as the default and the compatibility resolver quarantined. The next smallest
experiment should add two consumers whose compatible ranges share some, but not all, versions and
compare independent highest selection with a deterministic joint-satisfaction gate that rejects
an empty intersection without changing templates or loading packages.
