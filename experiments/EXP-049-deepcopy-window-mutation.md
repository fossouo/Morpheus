# EXP-049 — Deepcopy window mutation detection

- **Schema**: strict-v1
- **Date**: 2026-09-18
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-048 evidence and two synthetic built-in graph cases

## Question

Can a quarantined graph-integrity gate detect one deterministic exact-built-in mutation injected
after preflight and before `deepcopy` returns, instead of silently returning the changed graph?

## Hypothesis

The preflight-only baseline will accept the unchanged control and silently return the post-mutation
graph, scoring 1/2. A deterministic alias-aware graph digest checked before and after copying will
accept the control, reject the mutation with `source-changed-during-copy-window`, return no copy for
that case, and score 2/2.

## Baseline

Both paths receive fresh copies of the same locked three-container cyclic graph and use EXP-048's
exact-built-in, identity-memoized, sixteen-container preflight. The baseline validates and then
copies without checking whether the graph changed. The candidate records a deterministic digest of
typed scalar values, container order, cycles, and aliases before the injected callback, then checks
the source and copied graph before returning. The candidate remains quarantined.

## Protocol

1. Verify SHA-256 pins for EXP-048, its fixture and evaluator, and the public v2 template; keep all
   historical evidence and templates unchanged.
2. Run an unchanged control through both paths. Require acceptance, a preserved cyclic back-edge,
   source isolation, matching pre/post/copy digests, and exactly three visited containers.
3. In the held-out case, replace one nested string scalar after preflight and the initial digest but
   before `deepcopy`. Require the baseline to accept a copy matching the changed source and require
   the candidate to return the exact locked error without returning the copy.
4. Require two identical complete trials in one measured command. The callback is deterministic and
   single-threaded; no claim about real concurrency is allowed.

Reproduce with `python3 scripts/evaluate_deepcopy_window_mutation.py`. Use only repository data and
the Python standard library. No model calls, training, downloads, services, accelerators,
subprocesses, external calls, package execution, artifact loads, repository writes, template edits,
historical rewrites, or network access are allowed.

## Metrics

- Correct handling: preflight-only baseline exactly 1/2; integrity candidate exactly 2/2.
- Mutation: baseline exactly one silent drift whose copy matches the post-mutation source; candidate
  exactly one detected mutation, exact `source-changed-during-copy-window` error, and no returned
  copy for that case.
- Graph: every path visits exactly three containers and preserves the cyclic topology when a copy is
  returned; graph encoding includes exact scalar types, mapping-key order, cycles, and aliases.
- Cost: two complete trials, at most sixteen containers per graph, zero artifact loads, zero
  repository writes, C0, pinned inputs below 32 KiB, measured time below one second, and zero
  external calls. No true concurrency, locking, package behavior, language quality, inference,
  energy, production behavior, or general capability is measured.

## Acceptance and stop criteria

Accept only if every pin matches; the control remains unchanged and accepted on both paths; the
baseline silently returns exactly one changed graph; the candidate reports the exact locked error
and returns no copy for the mutation; scores are exactly 1/2 and 2/2; all topology and container
checks hold; trials repeat; artifact loads and repository writes remain zero; budgets hold;
external calls are zero; and publication checks pass.

Stop on pin drift, changed EXP-048 evidence, control drift, missed or extra mutation detection,
wrong error, a returned candidate mutation copy, topology drift, traversal beyond sixteen
containers, artifact access, repository mutation, exception, external call, or budget overrun. The
measured evaluator command may run only once and must not be tuned or rerun after failure.
Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`fail`. The single measured command exited before fixture loading or case scoring because the
direct script entry point could not resolve its `scripts` package import. No baseline or candidate
trial ran, so the declared 1/2 and 2/2 scores were not observed and no integrity conclusion is
available. The protocol stopped on that exception; the evaluator was not changed or rerun.

External calls, package loads, artifact loads, and repository writes by the evaluator were zero.
Post-result unit tests exercise importable functions only and are reproducibility checks, not a
replacement measurement of the failed direct entry point.

## Interpretation

**Observation:** the preregistered direct invocation failed at its repository-module import
boundary before it could verify pins or construct a graph.

**Inference:** the experimental entry point is not reproducible under its declared command. This
result says nothing about whether the digest candidate detects the injected mutation.

## Limitations

The protocol is limited to one unchanged control, one synthetic scalar mutation, one exact-built-in
cyclic graph, two trials, and one process. The primary [Python copy documentation](https://docs.python.org/3/library/copy.html)
describes deep copying and recursive-object memoization; it does not promise an atomic snapshot of a
concurrently mutable graph. This experiment uses a deterministic callback, not a thread, and cannot
establish real concurrency, race freedom, arbitrary-object safety, production readiness,
behavioral capability, or self-improvement.

## Decision

`fail`

## Next step

Preserve this failure unchanged. In a separate replay experiment, change only the import bootstrap,
pin EXP-049, rerun the same fixture and thresholds once, and do not advance toward a mutation-during-
traversal interleaving unless that replay passes.
