# EXP-014 — Package-qualified expert routing

- **Schema**: strict-v1
- **Date**: 2026-08-12
- **Status**: complete
- **Compute**: C0
- **Data**: seven predeclared synthetic held-out requests and two synthetic expert packages

## Question

Can an unchanged deterministic kernel compose and route two quarantined experts that reuse the
same local knowledge identifier by qualifying requests with package identity, while preserving
unrelated behavior, order invariance, and unload rollback?

## Hypothesis

The EXP-013 collision-rejecting baseline will reject both package orders, remain unloaded, and
score 0/4 on the held-out targets. The package-qualified candidate will score 4/4, route the
shared local identifier to two distinct locked values, preserve 3/3 regressions, return identical
responses in both package orders, and restore all four unloaded outputs after unload.

## Baseline

The baseline preserves EXP-013's exact cross-package local-identifier collision rule and differs
from the candidate only in composition and routing policy. Both kernels expose the same qualified
request interface. The baseline rejects the pair before state assignment; the candidate stores
records under the tuple `(package_id, local_id)` and requires both fields on recall requests.

## Protocol

1. Lock two synthetic packages, one shared local ID with different values, four package-qualified
   target requests, three unrelated regression requests, and two reversed package orders.
2. Attempt both orders with the collision-rejecting baseline. Require explicit rejection and the
   original unloaded outputs after each attempt.
3. Compose both orders with the candidate. Measure the same seven requests and require identical
   target and regression responses across orders.
4. Require the two shared-local-ID requests to return their two package-specific locked values.
5. Unload the candidate and remeasure the four target requests.
6. Repeat the complete trial in process and require byte-for-byte identical decisions.
7. Run exactly one measured evaluator invocation, then run the repository tests, record and index
   validators, template validation at a pinned date, public-safety check, and staged diff review.

Only the Python standard library is permitted. Fixtures are synthetic. No model, external
service, private datum, training procedure, network call, or production runtime is permitted.

## Metrics

- exact-match target accuracy and absolute gain over the rejected baseline state;
- exact-match regression accuracy and regression drop;
- baseline collision rejections and unchanged-state counts across two load orders;
- distinct routed values for the shared local identifier;
- candidate order invariance and post-unload equality with baseline;
- repeatability across two in-process trials;
- wall-clock latency for one evaluator invocation and fixture byte size;
- compute class C0, zero external calls, and repository-check status.

## Acceptance and stop criteria

Accept only if baseline target accuracy is 0/4, candidate accuracy is 4/4 for an absolute gain
of 1.0, both regression conditions score 3/3 with zero drop, both baseline orders are rejected
with 2/2 clean states, the shared local ID yields two distinct correct values, reversing package
order changes no response, unload restores 4/4 baseline outputs, repeated trials are identical,
the measured invocation finishes within 1 second, the fixture is below 16 KiB, external calls
remain zero, and all repository checks pass.

Stop after seven held-out requests, two package orders, two in-process trials, and one measured
evaluator invocation. Stop immediately on fixture inconsistency, ambiguous or partial routing,
partial state mutation, budget overrun, network requirement, baseline mutation, or test failure.

## Results

The collision-rejecting baseline rejected both package orders, remained unloaded after both
attempts, and scored 0/4 on the held-out targets. The package-qualified candidate scored 4/4,
an absolute target accuracy gain of 1.0. The two requests sharing `shared-entry-v1` returned
their two distinct package-specific locked values.

Both unloaded and loaded conditions scored 3/3 on the held-out regressions, for zero regression
accuracy drop. Reversing package order changed no target or regression response, and unload
restored all 4 baseline target outputs. Two complete in-process trials were identical. The
fixture was 3,478 bytes, the evaluator made 0 external calls, and the single measured invocation
completed in 0.000529 seconds.

## Interpretation

**Observation:** every predeclared behavioral, collision, routing, regression, order, rollback,
repeatability, size, latency, and cost threshold passed.

**Inference:** within this explicit exact-key protocol, package qualification admits two experts
that EXP-013's local-ID collision policy rejects, while removing the tested load-order ambiguity.
This is a new measured routing behavior relative to that baseline, not evidence of learned or
semantic routing, natural-language capability, or self-improvement.

The bounded EXP-012 through EXP-014 checkpoint is now complete:

| Experiment | Candidate behavior | Held-out target gap | Regressions | Rollback/order evidence |
|---|---|---:|---:|---|
| EXP-012 | Load one external exact-recall expert | 0/6 to 6/6 (+1.0) | 4/4, zero drop | 6/6 restored after unload |
| EXP-013 | Compose compatible experts; reject a collision atomically | 0/4 to 4/4 (+1.0) | 3/3, zero drop | order invariant; 2/2 conflict states clean |
| EXP-014 | Compose colliding local IDs under package-qualified routes | 0/4 to 4/4 (+1.0) | 3/3, zero drop | order invariant; 4/4 restored after unload |

All three used C0 synthetic exact-key fixtures, zero external calls, sub-16-KiB inputs, and
sub-1-second measured evaluator invocations. EXP-012 satisfies the founder's required behavioral
gain, and EXP-013 plus EXP-014 extend the same narrow kernel with measured composition and routing
behaviors. The checkpoint supports continuing the research loop, but only toward harder held-out
behavioral questions; it does not support a general capability or self-improvement claim.

## Limitations

The protocol is limited to explicit package identity, exact string identifiers, tiny synthetic
key-value packages, and a deterministic lookup kernel. It cannot establish learned or semantic
routing, automatic expert discovery, natural-language capability, concurrent atomicity, runtime
safety, or useful behavior outside the locked requests.

## Prior evidence

The primary [Sparsely-Gated Mixture-of-Experts paper](https://arxiv.org/abs/1701.06538) and
[Switch Transformer paper](https://arxiv.org/abs/2101.03961) motivate routing inputs to selected
experts. Neither establishes package-qualified non-parametric lookup or the result of this
synthetic protocol.

## Decision

`pass`
