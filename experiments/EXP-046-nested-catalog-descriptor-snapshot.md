# EXP-046 — Nested catalog descriptor selection snapshot

- **Schema**: strict-v1
- **Date**: 2026-09-15
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-045 evidence and three synthetic nested-member mutations

## Question

After joint selection but before handoff, does a shallow copy isolate a descriptor from mutations
inside one nested mutable member, or is a deterministic deep snapshot required?

## Hypothesis

A shared-reference baseline and a shallow-copy comparator will each answer zero of three held-out
nested-mutation cases correctly. A candidate decoded from deterministic snapshot bytes will answer
all three correctly.

## Baseline

All paths use EXP-045's unchanged two-artifact catalog, two consumer policies, and joint-highest
selector, then attach the same synthetic `provenance` member to each fresh descriptor. The baseline
retains the selected catalog object by reference. The comparator uses `copy.copy` on the selected
descriptor. The candidate serializes the complete pre-mutation descriptor into deterministic bytes
and decodes only those bytes for handoff.

## Protocol

1. Verify SHA-256 pins for EXP-045, its fixture and evaluator, and the public v2 template; keep all
   repository templates, historical evidence, and artifact bytes unchanged.
2. Select the unique joint maximum, retain one shared reference, make one shallow copy, and capture
   one deterministic byte snapshot before applying each fault.
3. Run three held-out in-memory mutations inside the single `provenance` member: replace a nested
   source identifier, replace one claim-list element, or replace a nested review boolean. Compare
   all three handoffs with the locked pre-mutation identity.
4. Require each mutation to remain visible in the catalog, only its locked leaf to change, the
   unselected descriptor to stay exact, and the deep snapshot bytes to stay exact; repeat the
   complete trial in one measured command.

Reproduce with `python3 scripts/evaluate_nested_catalog_descriptor_snapshot.py`. Use only
repository data and the Python standard library. No model calls, training, downloads, services,
accelerators, subprocesses, external calls, package execution, artifact loads, repository writes,
template edits, historical rewrites, or network access are allowed.

## Metrics

- Outcome accuracy: shared-reference baseline exactly 0/3; shallow-copy comparator exactly 0/3;
  deterministic deep snapshot candidate 3/3.
- Drift: three shared-reference drifts, three shallow-copy drifts, and zero deep-snapshot drifts;
  all three mutations visible in the source catalog and confined to their locked leaf.
- Isolation: the shallow top-level object is distinct but its nested member is aliased; the deep
  snapshot's nested member is distinct; the unselected descriptor and snapshot bytes stay exact.
- Cost: two complete trials, zero artifact loads, zero repository writes, C0, pinned inputs below
  32 KiB, measured time below one second, and zero external calls. No package behavior,
  concurrency, language quality, inference, energy, production, or general capability is measured.

## Acceptance and stop criteria

Accept only if every pin matches; pre-mutation selection remains the unique `1.1.0` descriptor in
all cases; shared reference and shallow copy each score exactly 0/3 and drift three times; the deep
snapshot scores 3/3 with zero drift; the locked alias relations hold; each mutation is visible and
changes only its locked leaf; the unselected descriptor and snapshot bytes remain exact; trials
repeat; artifact loads and repository writes remain zero; budgets hold; external calls are zero;
and publication checks pass.

Stop on pin drift, changed EXP-045 evidence, selection drift, unexpected shared or shallow accuracy,
any deep-snapshot drift, wrong alias relation, multi-leaf mutation, unselected-descriptor change,
snapshot-byte change, artifact access, repository mutation, exception, external call, or budget
overrun. The measured evaluator command may run only once and must not be tuned or rerun after
failure. Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`pass`. The shared-reference baseline and shallow-copy comparator each answered 0/3 cases
correctly and exposed all three post-selection nested mutations to the consumer handoff. The
deterministic deep byte snapshot answered 3/3 correctly with zero drift.

The shallow top-level descriptor was distinct while its `provenance` member remained aliased; the
deep snapshot and its nested member were distinct. Every locked mutation was visible in the source
catalog and changed only its specified leaf. The unselected descriptor and snapshot bytes remained
exact, and complete trials repeated.

Artifact-load attempts, repository writes, and external calls were zero. Pinned inputs were 24,602
bytes and the single measured invocation took 0.001755 seconds. The evaluator was not tuned or
rerun.

## Interpretation

**Observation:** on three locked mutations within one nested mutable member, both direct handoff
and shallow copy drifted every time; a descriptor decoded from bytes captured before mutation
preserved the complete locked identity every time.

**Inference:** the deterministic deep snapshot can remain quarantined for a shared-nested-alias
test. This does not show that serialization preserves intentional alias topology or that snapshot
capture and artifact access are atomic.

## Limitations

The protocol is limited to two consumers, two descriptors, one synthetic nested `provenance`
member, three single-leaf in-memory mutations, deterministic evaluator-specific JSON, and one
process. It excludes concurrent access, cycles, custom objects, alias graphs outside this member,
TOCTOU resistance, signatures, provenance authenticity, artifact access, package execution,
production readiness, behavioral capability, and self-improvement. The primary
[Python copy documentation](https://docs.python.org/3/library/copy.html) defines shallow copies as
retaining references to contained objects and deep copies as recursively copying them. The primary
[JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html) motivates recursively
deterministic JSON representations for hashing, but this evaluator does not claim full JCS
conformance or establish the candidate's safety.

## Decision

`pass`

## Next step

Keep shared-reference handoff as the default and the deterministic deep snapshot quarantined. The
next smallest experiment should place the same nested object under two descriptor fields and test
whether serialization's loss of alias topology changes locked semantics before considering
concurrency.
