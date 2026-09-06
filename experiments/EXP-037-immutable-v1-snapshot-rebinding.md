# EXP-037 — Immutable v1 snapshot rebinding

- **Schema**: strict-v1
- **Date**: 2026-09-06
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned public v1 template and three direct historical fixtures

## Question

Can an exact immutable v1 snapshot plus path-only rebinding of the three direct historical
template pins preserve the current loaders and transitive SHA-256 evidence without changing
any historical fixture payload beyond those three path values?

## Hypothesis

The immutable snapshot will be byte-for-byte identical to the public v1 template, but the
path-only transaction will not yet be reproducible: exactly one of three loaders will accept
the rebound path, two will reject their path contracts, and all three changed fixture payloads
will invalidate one direct transitive pin each. Migration will remain deferred.

## Baseline

The baseline is the unchanged public v1 template and the three direct historical pins in the
temporal-corpus, public-template-migration, and exclusion-reachability fixtures. The candidate
adds an exact archived snapshot and changes only those three path values in memory. It does not
write a rebound fixture or replace the public template.

## Protocol

1. Verify SHA-256 pins for the public template, immutable snapshot, and three source fixtures.
2. Require exact byte and SHA-256 equality between the public v1 template and snapshot.
3. Load all three unchanged source fixtures through their historical loaders.
4. Deep-copy each fixture and change only its direct template path to the snapshot path.
5. Run the same loaders, record exact path-contract errors, and compare temporal-corpus outputs.
6. Hash each rebound fixture and count repository fixture references to its original hash.
7. Repeat the complete trial inside one measured command; do not write candidate fixtures.

Reproduce with `python3 scripts/evaluate_template_v1_snapshot_rebind.py`. Use only repository
data and the Python standard library. No model calls, training, downloads, services,
accelerators, subprocesses, or external calls are allowed.

## Metrics

- Snapshot byte equality and SHA-256 equality.
- Baseline loaders accepted out of three; rebound loaders accepted out of three.
- Exact path-contract blockers and temporal-corpus output parity.
- Rebound fixture hashes changed out of three; direct transitive pins found and preserved.
- Complete-trial repeatability, combined direct input bytes, evaluator time, C0 class, and
  zero external calls. No inference, capability, or energy metric is claimed.

## Acceptance and stop criteria

Accept the hypothesis only if snapshot bytes and hashes are exact; baseline loaders score 3/3;
the rebound path is present in 3/3 candidate copies; rebound loaders score exactly 1/3; the two
locked errors are exact; temporal outputs match; all three candidate fixture hashes change;
exactly three direct transitive pins are found and zero remain valid for the candidate hashes;
the decision is `defer-for-path-contract-and-transitive-pin-plan`; trials repeat; inputs remain
below 16 KiB; measured time is below one second; external calls are zero; and publication checks
pass.

Stop on source drift, snapshot inequality, an unexpected loader result or error, behavior drift,
pin-count drift, repository mutation, exception, dependency or runtime change, external call, or
budget overrun. The measured evaluator command may run only once and must not be tuned or rerun
after failure. Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`fail`. The single measured command stopped on the first source, after the temporal-corpus
baseline fixture loaded but before any rebound loader ran. Its selector resolves to the full
source object, which also contains `id`, `selector`, lifecycle expectations, and other fields.
The evaluator incorrectly required that selected object to equal only `{path, sha256}` and
raised `ValueError: temporal-corpus direct pin changed`.

No baseline-loader total, rebound-loader total, temporal parity, transitive-pin count,
repeatability, input-size, or evaluator-time metric was scored. The measured command made zero
external calls and was not patched or rerun. A pre-measure repository check established that
the added snapshot and current public v1 template have the same SHA-256 digest, but that check
does not rescue the failed protocol or support a migration decision.

## Interpretation

**Observation:** the protocol encoded one selector shape incorrectly and stopped before testing
its hypothesis.

**Inference:** EXP-037 provides no evidence for or against the safety of rebinding the three
historical pins. It only demonstrates a protocol-construction failure. The public template and
all three historical fixture references remain unchanged.

## Limitations

This is a repository migration-safety experiment over synthetic artifacts. It does not test
semantic routing, source authenticity, runtime safety, natural-language capability, or
self-improvement. A matching SHA-256 digest is used here as a local byte-identity assertion;
the primary [TUF specification](https://theupdateframework.github.io/specification/latest/)
motivates integrity metadata and consistent snapshots but does not define this repository's
migration policy.

## Decision

`fail`

## Next step

Keep the public template on v1. A new experiment should pin EXP-037, change only the selector
handling so it edits the `path` member of the full temporal source object, and replay the same
loader, behavior, transitive-pin, repeatability, and budget thresholds without changing any
historical fixture.
