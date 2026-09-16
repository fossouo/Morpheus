# EXP-047 — Shared-alias selection snapshot

- **Schema**: strict-v1
- **Date**: 2026-09-16
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-046 evidence and three synthetic shared-alias mutations

## Question

When two selected-descriptor fields intentionally reference the same nested object, does the
deterministic JSON snapshot from EXP-046 preserve that alias behavior, or is an object-graph-aware
deep copy required?

## Hypothesis

Direct reference, shallow copy, and `copy.deepcopy` will each preserve cross-field propagation in
all three held-out mutations. A JSON byte round-trip will isolate the source but lose the shared
identity and answer zero of three cases correctly. Only `copy.deepcopy` will both preserve the
locked alias semantics and isolate the source catalog.

## Baseline

All paths use EXP-046's unchanged two-artifact catalog, two consumer policies, and joint-highest
selection. The selected descriptor receives one synthetic nested object referenced by both
`provenance` and `verification`. The EXP-046 JSON round-trip is the challenged baseline. Direct
reference and shallow copy are non-isolating controls; `copy.deepcopy` is the quarantined
candidate.

## Protocol

1. Verify SHA-256 pins for EXP-046, its fixture and evaluator, and the public v2 template; keep
   repository templates, historical evidence, and artifact bytes unchanged.
2. For each fresh strategy and case, select the unique joint maximum and attach the same nested
   object under both locked fields before handoff.
3. Mutate one leaf through `provenance`: the source identifier, first claim identifier, or review
   boolean. Score whether `verification` observes the same mutation and whether the source catalog
   remains unchanged.
4. Require identical pre-mutation value bytes across all paths, mutation of only the locked leaf,
   and two identical complete trials in one measured command.

Reproduce with `python3 scripts/evaluate_shared_alias_snapshot.py`. Use only repository data and
the Python standard library. No model calls, training, downloads, services, accelerators,
subprocesses, external calls, package execution, artifact loads, repository writes, template
edits, historical rewrites, or network access are allowed.

## Metrics

- Alias behavior: direct reference 3/3, shallow copy 3/3, `copy.deepcopy` 3/3, and JSON round-trip
  exactly 0/3; exactly three JSON alias losses.
- Isolation: direct reference and shallow copy each isolate 0/3 source catalogs; `copy.deepcopy`
  and JSON each isolate 3/3.
- Integrity: identical locked pre-mutation values, one changed leaf per case, unique pre-mutation
  selection, and repeatable complete trials.
- Cost: two complete trials, zero artifact loads, zero repository writes, C0, pinned inputs below
  32 KiB, measured time below one second, and zero external calls. No package behavior,
  concurrency, language quality, inference, energy, production, or general capability is measured.

## Acceptance and stop criteria

Accept only if every pin matches; pre-mutation selection remains the unique `1.1.0` descriptor;
direct reference, shallow copy, and `copy.deepcopy` each score exactly 3/3; JSON scores exactly
0/3 with three alias losses; only `copy.deepcopy` and JSON isolate all source catalogs; all
pre-mutation value bytes match; only locked leaves change; trials repeat; artifact loads and
repository writes remain zero; budgets hold; external calls are zero; and publication checks pass.

Stop on pin drift, changed EXP-046 evidence, selection drift, any unexpected score or alias
relation, source-isolation drift, multi-leaf mutation, pre-mutation value drift, artifact access,
repository mutation, exception, external call, or budget overrun. The measured evaluator command
may run only once and must not be tuned or rerun after failure. Subsequent tests are reproducibility
checks, not replacement measurements.

## Results

`pass`. Direct reference, shallow copy, and `copy.deepcopy` each preserved the locked cross-field
alias behavior in 3/3 cases. The deterministic JSON round-trip scored 0/3 and lost the shared
identity in all three cases.

Direct reference and shallow copy isolated 0/3 source catalogs. Both deep strategies isolated all
three, but only `copy.deepcopy` also preserved alias topology. All pre-mutation value bytes matched,
each case changed only its locked leaf, the unique selection held, and complete trials repeated.

Artifact-load attempts, repository writes, and external calls were zero. Pinned inputs were 26,483
bytes and the single measured invocation took 0.002502 seconds. The evaluator was not tuned or
rerun.

## Interpretation

**Observation:** for one locked shared nested object and three leaf mutations, value-equivalent JSON
decoding created two independent objects and broke the cross-field propagation that direct,
shallow, and memoized deep copy preserved.

**Inference:** the deterministic JSON snapshot from EXP-046 must not be generalized to descriptors
whose semantics depend on object identity. A topology-preserving `copy.deepcopy` path can remain
quarantined for boundary tests; this does not justify promotion or claim general graph safety.

## Limitations

The protocol is limited to two consumers, two descriptors, two fields sharing one JSON-compatible
nested object, three single-leaf mutations, deterministic evaluator-specific JSON, and one
process. It excludes cycles, custom copy hooks, concurrent access, TOCTOU resistance, signatures,
provenance authenticity, artifact access, package execution, production readiness, behavioral
capability, and self-improvement. The primary
[Python copy documentation](https://docs.python.org/3/library/copy.html) documents deep-copy memo
handling for already-copied objects. [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) defines the
JSON data model in terms of objects, arrays, and scalar values; this experiment tests the narrower
consequence for one in-memory shared reference and does not claim full graph serialization.

## Decision

`pass`

## Next step

Keep shared-reference handoff as the default, reject JSON snapshotting as a general object-graph
snapshot, and quarantine `copy.deepcopy`. The next smallest experiment should test one cycle and
one adversarial custom copy hook, with explicit failure boundaries, before any concurrent protocol.
