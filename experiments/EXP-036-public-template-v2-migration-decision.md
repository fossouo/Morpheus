# EXP-036 — Public template v2 migration decision

- **Schema**: strict-v1
- **Date**: 2026-09-05
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-034/035 fixtures and public v1 template

## Question

Can the public expert template be replaced in place by its rooted v2 projection while
preserving validation, lifecycle, exact synthetic behavior, rollback, and the repository's
direct SHA-256-pinned historical evidence?

## Hypothesis

The v2 projection will pass all functional thresholds inherited from EXP-034 and EXP-035,
but an in-place replacement will preserve zero of three direct historical template pins.
The gate will therefore defer migration until an immutable v1 snapshot exists.

## Baseline

The baseline is the unchanged public v1 template, its three direct SHA-256 fixture pins,
EXP-034's corrected disjoint expectation, and EXP-035's disjoint/nested reachability pair.
The candidate is only an in-memory rooted v2 projection; neither template nor historical
fixture is changed during the measured run.

## Protocol

1. Verify SHA-256 pins for the public template and EXP-034/035 evidence fixtures.
2. Validate v1 and the in-memory v2 projection at `2026-09-01`, require v2 expiry on
   `2026-09-02`, and reverse-project v2 to exact full-object v1 equality.
3. Replay EXP-034 and EXP-035 through their frozen v1 sidecar-root and stable-v2 paths.
4. Require exact routing, order, allowed/absent regression, and unload rollback thresholds.
5. Inspect the three locked direct fixture pins to the public-template path and compare
   them with both current-v1 and canonical candidate-v2 SHA-256 values.
6. Repeat the complete trial inside one measured command. Approve in-place migration only
   if every functional check passes and every direct historical pin remains valid.

Reproduce with `python3 scripts/evaluate_public_template_v2_decision.py`. Use only repository
data and the Python standard library. No model calls, training, downloads, services,
accelerators, or external calls are allowed. The public template must remain v1 during this run.

## Metrics

- v1/v2 validation, next-day expiry, and exact reverse projection.
- EXP-034 targets 4/4, regressions 2/2, rollback 4/4.
- EXP-035 path parity 4/4, path correctness 8/8, allowed and absent regressions 8/8 each,
  rollback 8/8, order invariance, and internal repeatability.
- Current and candidate preserved direct template pins out of three.
- Complete-trial repeatability, combined direct input bytes, evaluator time, C0 class,
  and zero external calls. No inference, memory-residency, or energy metric is claimed.

## Acceptance and stop criteria

Accept the hypothesis only if every functional threshold above passes; all three current
pins validate; zero candidate pins validate; the decision is exactly
`defer-for-immutable-v1-snapshot`; complete trials repeat; inputs remain below 16 KiB;
measured time is below one second; external calls are zero; and publication checks pass.

Stop on any pin drift, schema or lifecycle error, projection mismatch, behavioral threshold
failure, mutation, exception, dependency or runtime change, external call, or budget overrun.
The measured evaluator command may run only once and must not be tuned or rerun after failure.
Subsequent tests are reproducibility checks, not replacement measurements.

## Results

`pass`. The v1 baseline and in-memory v2 candidate both validated on the pinned date;
the candidate returned exactly `expired` on the following day and reverse-projected to
the complete v1 template. EXP-034 passed with targets 4/4, regressions 2/2, and rollback
4/4. EXP-035 passed with v1/v2 parity 4/4, path correctness 8/8, allowed and absent
regressions 8/8 each, and rollback 8/8.

All three current direct SHA-256 template pins validated. The canonical in-place v2
payload preserved 0/3 pins, so functional readiness was true while migration readiness
was false. The locked decision was `defer-for-immutable-v1-snapshot`. Complete trials
repeated; combined direct inputs were 3,778 bytes; the single measured invocation took
0.008915 seconds and made zero external calls. The command was not tuned or rerun.

## Interpretation

**Observation:** every locked functional threshold passed, but all three direct historical
pins would fail after an in-place replacement of the public template.

**Inference:** the rooted v2 representation is functionally ready in these synthetic paths,
but the repository is not ready for an in-place public-template change without first giving
historical evidence an immutable v1 target. This is a reproducibility block, not evidence
against the v2 contract or its tested behavior.

## Limitations

The behavioral evidence is synthetic and mostly inherited; this is a migration-safety
decision, not a new capability test. Direct-pin preservation is necessary but may not be
sufficient for a safe migration. The gate does not establish source authenticity,
authorization correctness, semantic routing, runtime safety, natural-language capability,
or self-improvement.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines structural assertions, not repository migration policy. The primary
[TUF specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
motivates a fixed time reference; this repository's date-only lifecycle and SHA-256 pin
policy remain local experimental rules.

## Decision

`pass`

## Next step

Keep the public template on v1. The next smallest experiment should add an immutable v1
snapshot in quarantine, rebind only the three direct historical pins with exact byte and
behavior parity, and prove the full repository remains reproducible before reconsidering
an in-place v2 migration.
