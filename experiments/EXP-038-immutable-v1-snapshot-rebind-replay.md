# EXP-038 — Immutable v1 snapshot rebinding replay

- **Schema**: strict-v1
- **Date**: 2026-09-07
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-037 record, fixture, public v1 template, and synthetic historical fixtures

## Question

Does changing only EXP-037's temporal selector handling so it edits the `path` member of the
full selected source object expose the previously locked loader, behavior, and transitive-pin
outcome without altering any historical fixture or the public template?

## Hypothesis

The unchanged EXP-037 evaluator will reproduce its exact selector-shape exception. The sole
candidate repair will then preserve every selected field except `path`, allow all three baseline
loaders and exactly one rebound loader, reproduce the two locked path-contract blockers, preserve
temporal behavior, identify three invalidated transitive pins, and keep migration deferred.

## Baseline

The baseline is the SHA-256-pinned EXP-037 record and fixture executed through its unchanged
evaluator. The candidate imports the historical evaluator and changes only its equality check:
it verifies `path` and `sha256` within the selected object, retains any additional fields, and
edits only `path` in a deep copy. Snapshot bytes, source fixtures, loaders, expected errors,
hashing, pin scan, and decision remain unchanged.

## Protocol

1. Verify the EXP-037 record and fixture pins, then transitively verify its template, snapshot,
   and three source pins.
2. Reproduce exactly `temporal-corpus direct pin changed` through the unchanged EXP-037 trial.
3. Deep-copy each source fixture, select its direct template reference, verify the locked public
   path and SHA-256, and modify only its `path` member to the immutable snapshot path.
4. Run the three unchanged baseline loaders and the three rebound loaders; compare exact errors
   and temporal-corpus trial outputs.
5. Hash each in-memory rebound fixture, count existing repository references to each original
   fixture hash, and leave every repository fixture unchanged.
6. Repeat the complete baseline/candidate trial inside one measured command.

Reproduce with `python3 scripts/evaluate_template_v1_snapshot_rebind_replay.py`. Use only
repository data and the Python standard library. No model calls, training, downloads, services,
accelerators, subprocesses, writes outside temporary directories, or external calls are allowed.

## Metrics

- Exact EXP-037 failure reproduction and count of full-source selector repairs.
- Snapshot byte/hash equality; baseline and rebound loader acceptance out of three.
- Exact path-contract blockers and temporal-corpus output parity.
- Rebound fixture hashes changed out of three; direct transitive pins found and preserved.
- Complete-trial repeatability, combined direct input bytes, evaluator time, C0 class, and zero
  external calls. No inference, capability, memory-residency, or energy metric is claimed.

## Acceptance and stop criteria

Accept only if the legacy exception is exact; snapshot bytes and hashes match; baseline loaders
score 3/3; rebound references score 3/3; exactly one full-source selector is repaired; rebound
loaders score 1/3; the migration and reachability errors exactly match EXP-037; temporal outputs
match; all three candidate fixture hashes change; exactly three direct transitive pins are found
and zero candidate hashes preserve them; the decision remains
`defer-for-path-contract-and-transitive-pin-plan`; trials repeat; inputs remain below 16 KiB;
measured time is below one second; external calls are zero; and publication checks pass.

Stop on source drift, failure-reproduction drift, snapshot inequality, mutation beyond `path`,
an unexpected loader result or error, behavior drift, pin-count drift, repository mutation,
exception, dependency or runtime change, external call, or budget overrun. The measured evaluator
command may run only once and must not be tuned or rerun after failure. Subsequent tests are
reproducibility checks, not replacement measurements.

## Results

`fail`. The unchanged EXP-037 trial reproduced exactly
`temporal-corpus direct pin changed`. After the sole selector repair, snapshot bytes and hashes
matched; baseline loaders scored 3/3; rebound references scored 3/3; exactly one full-source
selector was repaired; the temporal rebound loader was the sole acceptance; and the other two
loaders returned their exact locked path-contract errors. Temporal outputs matched, all three
rebound fixture hashes changed, and complete trials repeated.

The run stopped on the transitive-pin threshold: it counted 6 references rather than the locked
3. Each source fixture hash now appears once in its pre-EXP-037 dependent fixture and once in the
EXP-037 fixture itself. Candidate hashes preserved 0/6. Inputs were 15,163 bytes; the single
measured invocation took 0.068277 seconds and made zero external calls. The evaluator and fixture
were not patched or rerun after the failure.

## Interpretation

**Observation:** the selector repair exposed every locked loader and temporal-behavior outcome,
but EXP-037's own reproducibility fixture added one dependency edge for each of the three source
fixtures. The repository therefore contains six direct transitive pins, not three.

**Inference:** an in-place rewrite of the three source fixtures would now break both their earlier
dependents and the immutable evidence for EXP-037. The result strengthens the migration block:
preserving only the v1 template is insufficient when the historical dependency graph itself must
remain reproducible. It does not show that six fixture rewrites are safe or desirable.

## Limitations

This is a repository migration-safety replay over synthetic artifacts, not a behavioral-
capability experiment. It cannot establish semantic routing, source authenticity, runtime safety,
natural-language capability, or self-improvement. SHA-256 is used only for local byte-identity
and dependency-drift assertions. The primary
[TUF specification](https://theupdateframework.github.io/specification/latest/) motivates
hash-bound snapshot metadata, but it does not define this repository's migration policy.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines structural assertions; loader path contracts and rebinding policy are local experimental
rules rather than consequences of JSON Schema.

## Decision

`fail`

## Next step

Keep the public template and all historical fixtures unchanged. The next smallest experiment
should pin EXP-038 and build a read-only dependency-edge census that separates pre-existing
consumer pins from experiment-evidence pins, then compare an in-place rewrite with a versioned-v2
template path before proposing any migration.
