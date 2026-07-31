# EXP-002 — Held-out promotion gate

- **Date**: 2026-07-31
- **Status**: complete
- **Compute**: C0
- **Data**: five predeclared synthetic cases

## Question

Can a deterministic promotion rule reject a candidate that improves its target score
but exceeds a held-out control regression budget?

## Hypothesis

On the five predeclared cases, a guarded rule requiring both sufficient target gain and
an acceptable held-out control delta will match all expected decisions with zero false
promotions. A target-only baseline will falsely promote at least one rejected case.

## Baseline

The baseline promotes whenever target gain is at least 50 score units. It ignores the
held-out control. The guarded rule uses the same target threshold and additionally
requires control-score loss to be no more than 20 units.

Scores are integers from 0 to 1,000, so 10 units represent one percentage point. Integer
arithmetic avoids floating-point boundary ambiguity.

## Protocol

1. Lock five synthetic cases and their expected decisions before running the evaluator.
2. Include a safe gain, a regressive gain, an insufficient gain, an inclusive boundary,
   and a target regression with control improvement.
3. Evaluate the target-only baseline and guarded rule against the same cases.
4. Repeat the guarded evaluation in-process and require byte-identical decisions.
5. Run the repository unit tests and public-safety checker.

The evaluator uses only the Python standard library. It makes no network or model calls.

## Metrics

- guarded decision accuracy against the predeclared oracle;
- guarded false-promotion count among expected rejections;
- baseline false-promotion count among expected rejections;
- repeatability across two in-process evaluations;
- wall-clock duration for one command;
- fixture byte size as a bounded input-memory proxy;
- existing unit-test and public-safety regression status.

## Acceptance and stop criteria

Accept only if:

- guarded accuracy is 5/5;
- guarded false promotions are 0;
- target-only baseline false promotions are at least 1;
- repeated guarded decisions are identical;
- one evaluator invocation finishes within 1 second;
- the fixture is smaller than 16 KiB;
- all repository tests and the public-safety check pass.

Stop after five cases and one measured evaluator invocation. Stop immediately on a
schema error, budget overrun, network requirement, or test failure.

## Results

The guarded rule matched all 5 expected decisions and produced 0 false promotions
among the 3 expected rejections. The target-only baseline produced 1 false promotion:
it accepted the case with sufficient target gain and excessive held-out control loss.

The two in-process guarded evaluations were identical. The fixture was 1,005 bytes,
the evaluator made 0 external calls, and the measured command completed in 0.05 seconds.
The evaluator's acceptance result was `true`.

## Interpretation

**Observation:** the guarded rule passed every predeclared case while the target-only
baseline failed the deliberately regressive case.

**Inference:** for this deterministic fixture, an explicit control-regression budget
prevents a failure that target-only selection permits. This supports using a two-part
gate in later synthetic promotion protocols. It does not establish appropriate
thresholds or robustness to noisy estimates.

## Limitations

The fixture is small, deterministic, and hand-authored. Passing it validates only
the implementation of this decision contract, not its thresholds, statistical power,
or effectiveness on noisy real tasks.

## Prior evidence

The [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) empirically evaluates
candidate changes on coding benchmarks. [PACE](https://arxiv.org/abs/2606.08106)
studies acceptance rules for repeated self-modification under noisy held-out estimates.
EXP-002 tests a much narrower deterministic contract and does not reproduce either
paper's statistical claims.

## Decision

`pass`
