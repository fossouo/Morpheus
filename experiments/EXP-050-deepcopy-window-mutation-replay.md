# EXP-050 — Deepcopy window mutation replay

- **Schema**: strict-v1
- **Date**: 2026-09-19
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-049 evidence and its unchanged synthetic fixture

## Question

Does correcting only the direct-entry import bootstrap let the locked EXP-049 protocol execute
reproducibly, and does its quarantined graph-integrity candidate meet the unchanged thresholds?

## Hypothesis

The replay entry point will complete two identical trials. The preflight-only baseline will score
exactly 1/2 and silently return the one post-mutation graph, while the unchanged integrity
candidate will score exactly 2/2, report `source-changed-during-copy-window`, and return no copy for
the mutation.

## Baseline

EXP-049 is the entry-point baseline: its declared direct invocation failed before fixture loading
because the script directory, rather than the repository root, was first on Python's module search
path. The replay adds the repository root to `sys.path` before importing the unchanged EXP-049
module. It reuses EXP-049's fixture, two internal paths, graph construction, injection callback,
digests, thresholds, two-trial rule, and decision without modification.

## Protocol

1. Verify EXP-049 at SHA-256
   `a8a9297c255b1d59ba0a86fad8c18ee90ddf9b67d58694702a6de366bf46592d`, then use its unchanged
   loader to verify all transitive evidence pins and load the original fixture.
2. Add only the repository root import bootstrap, import the unchanged EXP-049 evaluator, and run
   its unchanged control and scalar-mutation cases through both paths.
3. Require the same two identical complete trials, three-container topology checks, baseline and
   candidate scores, drift counts, exact candidate error, and no-copy mutation response.
4. Execute `python3 scripts/evaluate_deepcopy_window_mutation_replay.py` exactly once as the measured
   command. Do not tune or rerun it after success or failure.

Use only repository data and the Python standard library. No model calls, training, downloads,
services, accelerators, subprocesses, external calls, package execution, artifact loads,
repository writes, template edits, historical rewrites, or network access are allowed.

## Metrics

- Entry point: successful direct import and exactly two identical complete trials.
- Correct handling: preflight-only baseline exactly 1/2; integrity candidate exactly 2/2.
- Mutation: exactly one baseline silent drift whose copy matches the changed source; exactly one
  candidate detection with `source-changed-during-copy-window` and no returned mutation copy.
- Graph: every path visits exactly three containers and preserves cyclic topology when returning a
  copy.
- Cost: two trials, at most sixteen containers per graph, zero artifact loads and repository
  writes, C0, all recursively pinned inputs below 32 KiB, measured time below one second, and zero
  external calls.

## Acceptance and stop criteria

Accept only if EXP-049 and all its transitive pins match; the direct replay completes; scores are
exactly 1/2 and 2/2; silent drift and detection counts are each exactly one; the candidate returns
the locked error and no mutation copy; topology and container checks hold; trials repeat; pinned
inputs remain below 32 KiB; runtime is below one second; artifact loads, repository writes, and
external calls are zero; and publication checks pass.

Stop on any pin drift, import failure, changed fixture or threshold, incomplete trial, score or
error mismatch, returned candidate mutation copy, topology drift, traversal beyond sixteen
containers, artifact access, repository mutation, exception, external call, or budget overrun. The
measured command may run only once; later tests are reproducibility checks, not replacement
measurement.

## Results

`pass`. The single measured direct invocation completed both trials. The preflight-only baseline
scored 1/2 and silently returned the post-mutation graph once. The unchanged integrity candidate
scored 2/2, detected the one mutation with `source-changed-during-copy-window`, and returned no copy
for that case. All returned copies preserved the locked cyclic topology, and every path visited
exactly three containers.

The two complete trials were identical. Recursively pinned inputs were 28,935 bytes and the measured
invocation took 0.001538 seconds. External calls, artifact loads, and repository writes were zero.
The evaluator was not tuned or rerun.

## Interpretation

**Observation:** adding the repository root before importing the unchanged EXP-049 evaluator made
the declared direct entry point reproducible, and every locked synthetic threshold passed.

**Inference:** for this deterministic two-case fixture, the digest gate detects the injected scalar
change that the preflight-only baseline silently copies. This result supports only the next bounded
synthetic interleaving test; the candidate remains quarantined and the shared-reference path remains
the default.

## Limitations

The protocol is limited to one unchanged control, one deterministic scalar mutation, one
exact-built-in cyclic graph, two trials, and one process. Python documents that a script directory
is initially first on the module search path and that `deepcopy` uses memoization for recursive
objects; neither behavior provides an atomic snapshot guarantee. This replay tests deterministic
entry-point reproducibility and the locked synthetic callback only, not real concurrency, race
freedom, arbitrary-object safety, production readiness, behavioral capability, or self-improvement.

Primary sources: [Python module search path initialization](https://docs.python.org/3/library/sys_path_init.html)
and [Python `copy` documentation](https://docs.python.org/3/library/copy.html).

## Decision

`pass`

## Next step

Preregister one deterministic exact-built-in mutation during graph traversal, after one container
has been encoded but before the digest completes, and require detection without adding threads or
changing the default handoff.
