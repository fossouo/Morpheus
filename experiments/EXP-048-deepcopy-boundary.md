# EXP-048 — Bounded deepcopy graph boundary

- **Schema**: strict-v1
- **Date**: 2026-09-17
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-047 evidence and two synthetic object-graph cases

## Question

Can the quarantined `copy.deepcopy` path preserve one built-in cyclic graph while failing closed
before executing one adversarial custom copy hook?

## Hypothesis

Unguarded `copy.deepcopy` will preserve and isolate the built-in cycle, but it will invoke the
custom `__deepcopy__` hook once, permit one source mutation, and retain the adversarial object.
An identity-memoized exact-built-in graph gate will preserve the same cycle through `deepcopy` and
reject the custom object before its hook runs. The baseline will score 1/2 and the candidate 2/2.

## Baseline

Both paths receive fresh graphs from the same locked fixture. The baseline calls `copy.deepcopy`
directly. The candidate first traverses at most sixteen exact built-in `dict` and `list` containers,
accepts only exact scalar leaves, rejects non-string mapping keys and all other types, and then
calls the same `copy.deepcopy`. The candidate remains quarantined.

## Protocol

1. Verify SHA-256 pins for EXP-047, its fixture and evaluator, and the public v2 template; keep
   templates, historical evidence, and artifact bytes unchanged.
2. Construct one three-container `dict`/`list` cycle. Require both paths to preserve the back-edge,
   isolate all mutable source containers, and leave the source unchanged after a copied-leaf edit.
3. Construct one source containing a synthetic object whose `__deepcopy__` hook increments a
   counter, mutates source state, and returns itself. Score the direct baseline and the preflight
   candidate on fresh sources.
4. Require two identical complete trials in one measured command. The graph guard must track
   container identity so the allowed cycle terminates without recursion.

Reproduce with `python3 scripts/evaluate_deepcopy_boundary.py`. Use only repository data and the
Python standard library. No model calls, training, downloads, services, accelerators, subprocesses,
external calls, package execution, artifact loads, repository writes, template edits, historical
rewrites, or network access are allowed.

## Metrics

- Correct handling: unguarded baseline exactly 1/2; guarded candidate exactly 2/2.
- Cycle: both paths preserve the back-edge and isolate the source; the candidate visits exactly
  three containers and leaves the source unchanged after mutation of the copy.
- Hook boundary: baseline exactly one hook call, one source mutation, and one retained source
  alias; candidate exact `unsupported-type:AdversarialCopyHook` rejection, zero hook calls, and
  unchanged source state.
- Cost: two complete trials, at most sixteen candidate containers per graph, zero artifact loads,
  zero repository writes, C0, pinned inputs below 32 KiB, measured time below one second, and zero
  external calls. No package behavior, concurrency, language quality, inference, energy,
  production, or general capability is measured.

## Acceptance and stop criteria

Accept only if every pin matches; both cycle paths preserve topology and source isolation; the
candidate visits exactly three containers; the baseline hook runs exactly once, mutates its source,
and returns the source object; the candidate rejects with the exact locked error before any hook
call or source mutation; scores are exactly 1/2 and 2/2; trials repeat; artifact loads and
repository writes remain zero; budgets hold; external calls are zero; and publication checks pass.

Stop on pin drift, changed EXP-047 evidence, cycle or isolation drift, any unexpected hook count,
error, alias, or source mutation, traversal beyond sixteen containers, artifact access, repository
mutation, exception, external call, or budget overrun. The measured evaluator command may run only
once and must not be tuned or rerun after failure. Subsequent tests are reproducibility checks, not
replacement measurements.

## Results

`pass`. The unguarded baseline scored 1/2 and the guarded candidate 2/2. Both paths preserved
the three-container cycle's back-edge, isolated its mutable containers, and left its source
unchanged after mutation of the copy. The candidate visited exactly three containers.

On the custom-object case, unguarded `copy.deepcopy` invoked the synthetic hook exactly once. The
hook mutated its source state and returned the original object, so the copied graph retained that
source alias. The guarded candidate returned the exact locked
`unsupported-type:AdversarialCopyHook` error before the hook ran; its hook count and source
mutations were both zero.

Artifact-load attempts, repository writes, and external calls were zero. Pinned inputs were 25,590
bytes and the single measured invocation took 0.000389 seconds. The evaluator was not tuned or
rerun.

## Interpretation

**Observation:** on the two locked graphs, `copy.deepcopy` handled the exact-built-in cycle but
also delegated to the custom hook, which produced both a source side effect and retained alias.
The identity-memoized exact-built-in preflight kept the cycle case while excluding the hook case
before delegation.

**Inference:** `copy.deepcopy` is acceptable only as a quarantined operation behind an explicit
data-type and size boundary for this tested configuration. The result does not make arbitrary
Python object graphs safe and does not remove a time-of-check/time-of-use gap between preflight
and copy.

## Limitations

The protocol is limited to one three-container exact-built-in cycle, one synthetic custom hook,
two trials, and one process. It excludes tuples, sets, mapping subclasses, deep or wide graphs,
resource exhaustion, concurrent mutation, TOCTOU resistance, arbitrary hostile Python execution,
artifact access, package execution, production readiness, behavioral capability, and
self-improvement. The primary [Python copy documentation](https://docs.python.org/3/library/copy.html)
documents both memo handling for recursive objects and user-defined `__deepcopy__` control; this
experiment tests a narrower preflight boundary rather than claiming that `deepcopy` is a sandbox.

## Decision

`pass`

## Next step

Keep shared-reference handoff as the default and keep the exact-built-in gate plus `deepcopy` in
quarantine. The next smallest experiment should inject one deterministic built-in mutation between
preflight and copy, then require detection rather than silently copying the changed graph before
considering real concurrency.
