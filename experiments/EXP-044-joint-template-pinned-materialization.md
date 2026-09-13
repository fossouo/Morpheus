# EXP-044 — Joint template pinned materialization

- **Schema**: strict-v1
- **Date**: 2026-09-13
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-043 evidence, public v2 template, and synthetic materialization faults

## Question

After two consumers jointly select one template artifact, does retaining that exact artifact's
schema, version, path, and SHA-256 make removal or mutation fail closed while a lower jointly
compatible artifact remains available?

## Hypothesis

A fallback baseline that recomputes joint selection from currently loadable artifacts will answer
exactly one of three held-out materialization cases correctly and silently downgrade twice. A
pinned candidate will answer all three: load the intact selected artifact, reject its removal, and
reject its mutation without loading the lower jointly compatible artifact.

## Baseline

Both paths first use EXP-043's unchanged joint-selection policy over the same two-consumer range
intersections and two materialized artifacts. After the locked fault, the baseline discards missing
or hash-mismatched descriptors and recomputes the highest joint match. The candidate retains the
pre-fault selected descriptor and loads only its exact schema, version, path, and SHA-256.

## Protocol

1. Verify SHA-256 pins for EXP-043, its fixture and evaluator, and the public v2 template; keep all
   repository templates and historical evidence unchanged.
2. In a fresh temporary directory per case, derive, validate, and materialize canonical `1.0.2`
   and `1.1.0` artifacts. Lock the two EXP-043 consumers for which both are compatible and `1.1.0`
   is the unique joint maximum.
3. Run three held-out cases: intact selected bytes, selected path removed, and selected bytes
   mutated. Require the lower `1.0.2` artifact to remain byte-exact and present in every case.
4. Compare fallback re-selection with exact pinned loading, remove each temporary directory, and
   repeat the complete trial within one measured command.

Reproduce with `python3 scripts/evaluate_joint_template_pinned_materialization.py`. Use only
repository data, temporary files, and the Python standard library. No model calls, training,
downloads, services, accelerators, subprocesses, external calls, package execution, repository
writes, template edits, historical rewrites, or network access are allowed.

## Metrics

- Outcome accuracy: fallback baseline exactly 1/3; pinned candidate 3/3.
- Integrity: two baseline silent downgrades; zero candidate silent downgrades; removal and mutation
  each produce their distinct locked candidate error.
- Isolation: two artifacts materialized per case; the lower artifact remains present and hash-exact
  in 3/3 cases; zero repository writes; all temporary directories removed.
- Complete-trial repeatability, pinned input bytes below 32 KiB, measured time below one second, C0
  class, and zero external calls. No package behavior, routing, language quality, inference, energy,
  production, semantic compatibility, or general capability metric is claimed.

## Acceptance and stop criteria

Accept only if every pin and derived manifest validates on the pinned date; pre-fault joint
selection chooses the unique `1.1.0` descriptor in all cases; the baseline scores exactly 1/3 and
silently downgrades twice; the candidate scores 3/3 with zero silent downgrade; both fault-specific
errors match; the lower artifact remains present and exact in 3/3 cases; materialization is confined
to cleaned temporary directories; trials repeat; pinned inputs stay below 32 KiB; measured time
stays below one second; external calls are zero; and publication checks pass.

Stop on pin drift, changed historical evidence or templates, invalid derivation, selection drift,
missing lower artifact, baseline or candidate score drift, candidate fallback, a wrong error,
package execution, repository mutation, temporary-path residue, exception, external call, or budget
overrun. The measured evaluator command may run only once and must not be tuned or rerun after
failure. Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`pass`. The pre-fault joint selection chose the unique `1.1.0` descriptor in all three cases.
The fallback baseline answered 1/3 cases correctly and produced both locked lower-version loads,
silently selecting the still-present `1.0.2` artifact after both removal and mutation of `1.1.0`.
The pinned candidate answered 3/3 cases correctly with zero silent downgrade: it loaded the intact
artifact, returned `error:pinned-artifact-missing` after removal, and returned
`error:pinned-artifact-hash-mismatch` after mutation.

Both artifacts were materialized in each isolated case. The lower artifact remained present and
hash-exact in 3/3 cases; all temporary roots were removed; repository writes and external calls
were zero. Complete trials repeated. Pinned inputs were 29,330 bytes and the single measured
invocation took 0.007420 seconds. The evaluator was not tuned or rerun.

## Interpretation

**Observation:** on the three locked synthetic filesystem states, keeping the exact descriptor
chosen before the fault prevented the fallback baseline's two lower-version loads and separated a
missing path from changed bytes.

**Inference:** the pinned joint loader can remain quarantined for an adversarial descriptor-state
test. This does not show safety under concurrent mutation or that either consumer range is
semantically correct.

## Limitations

The protocol covers two consumers, two canonical numeric versions, three synthetic filesystem
states, and one process. It excludes concurrent mutation, TOCTOU resistance, signatures, provenance
authenticity, semantic compatibility, package execution, production readiness, behavioral
capability, and self-improvement. The primary [Semantic Versioning 2.0.0
specification](https://semver.org/spec/v2.0.0.html) defines numeric precedence and requires released
version contents not to change, but it does not define this fallback policy. The primary [TUF
specification](https://theupdateframework.github.io/specification/latest/) motivates hash-bound
targets, but it does not establish this loader's safety.

## Decision

`pass`

## Next step

Keep independent selection as the default and the pinned joint loader quarantined. The next
smallest experiment should mutate the shared catalog descriptor after selection and compare a
shared-reference handoff with an immutable selection snapshot, without loading or changing any
repository artifact.
