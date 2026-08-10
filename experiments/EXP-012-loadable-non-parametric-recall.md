# EXP-012 — Loadable non-parametric recall

- **Schema**: strict-v1
- **Date**: 2026-08-10
- **Status**: complete
- **Compute**: C0
- **Data**: ten predeclared synthetic held-out requests and one synthetic expert package

## Question

Can an unchanged deterministic kernel gain exact recall on held-out synthetic requests after
loading a quarantined non-parametric expert, preserve unrelated behavior, and return exactly to
its baseline behavior after unloading the expert?

## Hypothesis

On six predeclared held-out target requests, the unloaded baseline will score 0/6 and the
loaded candidate will score 6/6, an absolute gain of 1.0. On four held-out regression requests,
both conditions will score 4/4. After unload, all six target responses will equal the original
unloaded responses.

## Baseline

The baseline is the same deterministic kernel with no expert loaded. It supports a stable
`echo` operation and returns `unknown` for recall requests. The candidate differs only by
loading one validated, quarantined expert whose six synthetic knowledge records are stored
outside the kernel. No weights, prompts, or baseline code paths are changed between conditions.

## Protocol

1. Lock one synthetic expert package, six target requests, and four unrelated regression
   requests before the evaluator is run.
2. Validate the manifest at the pinned reference date `2026-08-10`; require quarantine state,
   unload rollback, synthetic provenance, and exact agreement between declared knowledge IDs,
   stored records, and target test IDs.
3. Evaluate the ten requests with the expert unloaded, load the expert, and evaluate the same
   ten requests again.
4. Unload the expert and evaluate the six target requests a third time.
5. Repeat the complete transition in process and require byte-for-byte identical decisions.
6. Run exactly one measured evaluator invocation, then run the repository tests, record and
   index validators, template validation at the pinned date, public-safety check, and staged
   diff review.

Only the Python standard library is permitted. The fixture is synthetic. No model, external
service, private datum, training procedure, or network call is permitted.

## Metrics

- exact-match target accuracy for unloaded and loaded conditions, plus absolute accuracy gain;
- exact-match regression accuracy for unloaded and loaded conditions, plus regression drop;
- rollback equality with the original six unloaded target responses;
- repeatability across two complete in-process transitions;
- wall-clock latency for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- compute class C0 and external-call count as cost metrics;
- repository test, record-validation, index-validation, template-validation, and public-safety
  status.

## Acceptance and stop criteria

Accept only if unloaded target accuracy is 0/6, loaded target accuracy is 6/6, absolute target
gain is 1.0, both regression accuracies are 4/4, regression drop is zero, all six post-unload
responses equal their original unloaded responses, repeated transitions are identical, the
measured invocation finishes within 1 second, the fixture is smaller than 16 KiB, external
calls remain zero, and all repository checks pass.

Stop after ten locked requests, two in-process transitions, and one measured evaluator
invocation. Stop immediately on a manifest or fixture inconsistency, budget overrun, network
requirement, unexpected mutation of the kernel baseline, or test failure.

## Results

The unloaded kernel scored 0/6 on the held-out target cases. With the quarantined expert
loaded, the same kernel scored 6/6, an absolute target accuracy gain of 1.0. Both unloaded and
loaded conditions scored 4/4 on held-out regression cases, for zero regression accuracy drop.

After unload, all 6 target responses matched the original unloaded responses. Two complete
in-process transitions were identical. The locked fixture was 2,896 bytes, the evaluator made
0 external calls, and the single measured command completed in 0.000316 seconds. Final checks
reported 82 passing tests, 13 valid experiment records, 13 index-to-record matches, a valid
public expert-package template at the pinned date, and zero public-safety findings.

## Interpretation

**Observation:** every measured behavioral, rollback, repeatability, size, latency, and cost
threshold passed. Loading the package changed only the six declared recall responses, and
unloading it restored their baseline outputs.

**Inference:** within this synthetic exact-key protocol, a non-parametric expert added a new
measured recall behavior without modifying the kernel and without observed regression on the
four locked controls. EXP-012 therefore satisfies the behavioral-capability requirement for the
bounded EXP-012 through EXP-014 checkpoint, subject to comparison after its third successful
experiment. This is not evidence of semantic retrieval, natural-language capability, or
self-improvement.

## Limitations

This protocol tests exact lookup over a tiny synthetic key-value expert. It cannot establish
natural-language understanding, semantic retrieval, open-domain generalization, generation
quality, runtime safety, or useful capability outside the ten locked requests.

## Prior evidence

The primary [Retrieval-Augmented Generation paper](https://arxiv.org/abs/2005.11401) studies
language generation with access to explicit non-parametric memory. It motivates testing an
external-memory condition but does not establish the outcome of this narrower deterministic
lookup protocol.

## Decision

`pass`
