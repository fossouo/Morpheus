# EXP-045 — Catalog descriptor selection snapshot

- **Schema**: strict-v1
- **Date**: 2026-09-14
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-044 evidence and three synthetic descriptor mutations

## Question

After joint selection but before handoff, does an immutable selection snapshot prevent a mutable
catalog descriptor's changed path, hash, or version from altering the selected identity observed by
the consumer?

## Hypothesis

A baseline that hands off the same mutable descriptor object held by the catalog will answer zero of
three held-out mutation cases correctly. A candidate that snapshots the selected descriptor into
canonical immutable bytes before mutation will answer all three correctly.

## Baseline

Both paths use EXP-044's unchanged two-artifact catalog, two consumer policies, and joint-highest
selector. The baseline retains the selected catalog object by reference. The candidate serializes
that same pre-mutation descriptor into deterministic bytes and hands off only the decoded snapshot.

## Protocol

1. Verify SHA-256 pins for EXP-044, its fixture and evaluator, and the public v2 template; keep all
   repository templates, historical evidence, and artifact bytes unchanged.
2. Select the unique joint maximum, retain one shared reference, and capture one canonical byte
   snapshot before applying each fault.
3. Run three held-out in-memory mutations against the selected catalog object: replace only `path`,
   only `sha256`, or only `version`. Compare both handoffs with the locked pre-mutation identity.
4. Require the mutation to remain visible in the catalog, the unselected descriptor to stay exact,
   and the snapshot bytes to remain exact; then repeat the complete trial in one measured command.

Reproduce with `python3 scripts/evaluate_catalog_descriptor_snapshot.py`. Use only repository data
and the Python standard library. No model calls, training, downloads, services, accelerators,
subprocesses, external calls, package execution, artifact loads, repository writes, template edits,
historical rewrites, or network access are allowed.

## Metrics

- Outcome accuracy: shared-reference baseline exactly 0/3; immutable snapshot candidate 3/3.
- Drift: three baseline handoff drifts; zero candidate drifts; all three mutations visible in the
  source catalog; only the locked field changes; the unselected descriptor and snapshot stay exact.
- Cost and isolation: two complete trials, zero artifact loads, zero repository writes, C0, pinned
  inputs below 32 KiB, measured time below one second, and zero external calls. No package behavior,
  concurrency, language quality, inference, energy, production, or general capability is measured.

## Acceptance and stop criteria

Accept only if every pin matches; pre-mutation selection remains the unique `1.1.0` descriptor in
all three cases; the baseline scores exactly 0/3 and drifts three times; the candidate scores 3/3
and never drifts; each locked mutation is visible in the source catalog; no other descriptor field
or unselected descriptor changes; snapshot bytes remain exact; trials repeat; artifact loads and
repository writes remain zero; budgets hold; external calls are zero; and publication checks pass.

Stop on pin drift, changed EXP-044 evidence, selection drift, unexpected baseline accuracy, any
candidate drift, multi-field mutation, unselected-descriptor change, snapshot-byte change, artifact
access, repository mutation, exception, external call, or budget overrun. The measured evaluator
command may run only once and must not be tuned or rerun after failure. Subsequent tests are
reproducibility checks, not replacement measurements.

## Results

`pass`. The shared-reference baseline answered 0/3 cases correctly and exposed all three
post-selection catalog mutations to the consumer handoff. The immutable byte snapshot answered
3/3 correctly with zero drift. The path, SHA-256, and version mutations were each visible in the
source catalog, changed only their locked field, and left the unselected descriptor exact.

The snapshot bytes remained exact and complete trials repeated. Artifact-load attempts,
repository writes, and external calls were zero. Pinned inputs were 27,995 bytes and the single
measured invocation took 0.001002 seconds. The evaluator was not tuned or rerun.

## Interpretation

**Observation:** on three locked flat-descriptor mutations, retaining the catalog object by
reference changed the handed-off identity every time; canonical bytes captured before mutation
preserved it every time.

**Inference:** the immutable selection snapshot can remain quarantined for a nested-descriptor and
concurrent-mutation test. This does not show that the catalog source is authentic or that snapshot
capture and artifact access are atomic.

## Limitations

The protocol is limited to two consumers, two flat descriptors, three single-field in-memory
mutations, deterministic canonical JSON, and one process. It excludes nested descriptors,
concurrency, TOCTOU resistance, signatures, provenance authenticity, artifact access, package
execution, production readiness, behavioral capability, and self-improvement. The primary
[Python copy documentation](https://docs.python.org/3/library/copy.html) distinguishes assignment
bindings from copied mutable objects. The primary [TUF specification](https://theupdateframework.github.io/specification/latest/)
motivates consistent metadata snapshots and exact expected targets, but neither source establishes
this candidate's safety.

## Decision

`pass`

## Next step

Keep the shared-reference path as the default and the immutable snapshot candidate quarantined. The
next smallest experiment should add one nested mutable descriptor member, compare shallow and deep
snapshots, and still avoid artifact access before considering any concurrent protocol.
