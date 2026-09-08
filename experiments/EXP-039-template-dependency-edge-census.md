# EXP-039 — Template dependency-edge census

- **Schema**: strict-v1
- **Date**: 2026-09-08
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-038 evidence and deterministic repository fixtures

## Question

Can a read-only typed census distinguish the six dependency edges exposed by EXP-038 and show
whether an in-place source-fixture rewrite or a separate versioned-v2 template path better
preserves historical evidence?

## Hypothesis

The count-only EXP-038 baseline will identify six edges but type none. The candidate census will
classify all six locked edges as three pre-existing consumer pins and three experiment-evidence
pins. Rewriting the three source fixtures in place will preserve 0/6 edges and require changing
all three evidence pins, while a new versioned-v2 template path will preserve 6/6 without any
historical fixture rewrite. Migration will remain unapproved pending a separate versioned-path
gate.

## Baseline

The baseline is EXP-038's undifferentiated transitive-pin count, SHA-256-pinned through its report
and fixture. The candidate uses the same three source hashes and existing repository fixtures,
but records each matching JSON pointer and classifies only references in EXP-037's locked fixture
as experiment evidence; all earlier dependents are consumers. No repository artifact is rewritten.

## Protocol

1. Verify the SHA-256 pins for EXP-038, its fixture, and EXP-037's evidence fixture.
2. Reproduce EXP-038's six-edge observation against its locked expectation of three.
3. Scan JSON `sha256` members in repository fixtures for exact matches to the three source hashes;
   record source, referrer, JSON pointer, and consumer/evidence class.
4. Compare the exact six-edge census with the locked fixture and score typed-edge correctness
   against the count-only baseline.
5. In memory, rebind each source fixture to the immutable v1 snapshot and count invalidated
   consumer and evidence edges.
6. In memory, project the unchanged public v1 template to rooted v2 at a new versioned path;
   validate it on `2026-09-01`, reverse-project it exactly, and count preserved edges while leaving
   all source fixtures untouched.
7. Repeat the complete trial inside one measured command without writing candidate artifacts.

Reproduce with `python3 scripts/evaluate_template_dependency_edge_census.py`. Use only repository
data and the Python standard library. No model calls, training, downloads, services, accelerators,
subprocesses, external calls, or repository writes are allowed.

## Metrics

- Exact EXP-038 six-edge failure reproduction.
- Typed-edge correctness: count-only baseline 0/6; candidate target 6/6.
- Consumer and experiment-evidence edges, total edges, and distinct referrer files.
- For each strategy: source hashes changed, edges preserved, required edge updates, and required
  experiment-evidence updates.
- Versioned candidate validation and exact v1 reverse projection.
- Complete-trial repeatability, combined pinned input bytes, evaluator time, C0 class, and zero
  external calls. No inference, capability, memory-residency, or energy metric is claimed.

## Acceptance and stop criteria

Accept only if EXP-038 reproduces six transitive pins against its locked three; the baseline types
0/6 edges; the candidate types exactly 6/6 as three consumer and three experiment-evidence edges
across four files; in-place rewriting changes three source hashes, preserves 0/6 edges, requires
six edge updates including all three evidence edges; the unused versioned path changes zero source
hashes, preserves 6/6, requires zero historical updates, validates, and reverse-projects exactly;
the public template remains unchanged; migration remains false; trials repeat; inputs stay below
24 KiB; measured time stays below one second; external calls are zero; and publication checks pass.

Stop on pin drift, prior-result drift, an extra or missing edge, classification mismatch,
projection or validation failure, an occupied versioned path, repository mutation, exception,
dependency or runtime change, external call, or budget overrun. The measured evaluator command may
run only once and must not be tuned or rerun after failure. Subsequent tests are reproducibility
checks, not replacement measurements.

## Results

`pass`. EXP-038's failure reproduced with six transitive pins against its locked expectation of
three. The count-only baseline typed 0/6 edges. The candidate census typed 6/6: three consumer
edges and three experiment-evidence edges across four fixture files.

The in-place strategy changed all three source-fixture hashes, preserved 0/6 dependency edges,
and would require six pin updates, including all three experiment-evidence edges. The separate
versioned-path strategy changed zero source hashes, preserved 6/6 edges, and required zero
historical pin updates. Its in-memory rooted v2 candidate validated at the pinned date and
reverse-projected exactly to v1; the proposed path was unused and the public v1 template remained
unchanged.

Complete trials repeated. Combined pinned inputs were 24,365 bytes, below the locked 24 KiB limit
by 211 bytes. The single measured invocation took 0.047241 seconds and made zero external calls.
The evaluator was not tuned or rerun.

## Interpretation

**Observation:** the total of six was not six interchangeable references: half were consumers of
the three source fixtures and half were EXP-037 evidence about those fixtures. Rewriting the
sources in place invalidated every edge, whereas leaving the v1 graph untouched preserved every
edge while an independent v2 candidate remained structurally reversible.

**Inference:** a separate versioned-v2 path is the safer design to test next because it avoids
rewriting the historical evidence graph in this repository. This does not authorize adding or
promoting that path; a dedicated gate must still test a real versioned artifact and new-consumer
contract.

## Limitations

This is a repository dependency-graph experiment over synthetic artifacts, not a behavioral-
capability test. The consumer/evidence boundary is a locked local classification and may not
generalize to other repositories. SHA-256 is used only for local byte-identity and dependency-drift
assertions. The primary [TUF specification](https://theupdateframework.github.io/specification/latest/)
motivates hash-bound consistent snapshots and separately addressable incompatible formats, but it
does not define this repository's edge classes or migration policy.

## Decision

`pass`

## Next step

Keep the public v1 template and all historical fixtures unchanged. Preregister a bounded gate
that materializes a candidate v2 template at the unused versioned path, adds one new synthetic
consumer pinned to it, and proves v1 historical reproducibility plus v2 validation, lifecycle,
routing, rollback, and removal behavior before considering publication of the new path.
