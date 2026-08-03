# EXP-005 — Metadata-value validation

- **Schema**: strict-v1
- **Date**: 2026-08-03
- **Status**: complete
- **Compute**: C0
- **Data**: eight predeclared synthetic metadata-value cases

## Question

Can deterministic value checks reject empty and known placeholder `Data` metadata that the
existing strict contract accepts?

## Hypothesis

On eight predeclared synthetic cases, the candidate validator will classify every case
correctly with zero false accepts. The prior contract, which checks required metadata
presence and typed fields but not `Data` placeholders, will falsely accept at least five of
the seven invalid records.

## Baseline

The baseline is the existing validator. It retains title, filename, required-metadata,
duplicate, date, status, compute, section, and decision checks. The candidate adds only exact
placeholder detection for `Data`, without changing the metadata parser.

## Protocol

1. Lock one valid record and seven single-fault `Data` mutations before evaluation.
2. Cover the unchanged template value, four normalized short markers, an empty value, and a
   whitespace-only value.
3. Compare the prior contract with the placeholder-aware candidate on the same labels.
4. Repeat the candidate evaluation in-process and require identical decisions.
5. Run the repository unit tests, repository-level record validator, and public-safety check.

The candidate recognizes only exact normalized values declared for `Data`. It does not try
to infer whether a data description is truthful or sufficiently detailed. Only the Python
standard library is permitted; the evaluator makes no network or model calls.

## Metrics

- candidate decision accuracy across eight cases;
- candidate false-accept count across seven invalid cases;
- prior-contract false-accept count across seven invalid cases;
- repeatability across two in-process evaluations;
- wall-clock duration for one evaluator invocation;
- fixture byte size as a bounded input-memory proxy;
- repository test, record-validation, and public-safety status.

## Acceptance and stop criteria

Accept only if candidate accuracy is 8/8, candidate false accepts are 0, baseline false
accepts are at least 5, repeated decisions are identical, one evaluator invocation finishes
within 1 second, the fixture is smaller than 16 KiB, and all repository checks pass.

Stop after eight cases and one measured evaluator invocation. Stop immediately on an
unexpected schema error, budget overrun, network requirement, or test failure.

## Results

The candidate classified 6 of 8 cases correctly and produced 2 false accepts, so it failed
the predeclared 8/8 and zero-false-accept thresholds. It rejected the unchanged template
value and all four short markers. It falsely accepted both the empty and whitespace-only
values. The baseline falsely accepted all 7 invalid records.

The two in-process candidate evaluations were identical. The fixture was 663 bytes, the
evaluator made 0 external calls, and the single measured command completed in 0.005077
seconds. The final repository checks reported 35 passing tests, 6 valid experiment records,
and zero public-safety findings.

## Interpretation

**Observation:** the candidate closed five exact-placeholder cases but did not make empty
`Data` values invalid. Inspection of the fixed parser shows that its `\s*` expression can
consume line breaks, so an empty metadata line can be joined to later content rather than
captured as an empty value. The [Python regular-expression documentation](https://docs.python.org/3/library/re.html)
confirms that `\s` includes newline characters.

**Inference:** exact placeholder checks are insufficient until metadata parsing is constrained
to a single line. Because the acceptance criteria failed, the candidate is retained only in
the evaluator and is not promoted into the repository validator.

## Limitations

The fixture is synthetic and isolates `Data`; it does not test every metadata field or every
whitespace code point. Exact placeholder detection cannot establish scientific quality,
truthfulness, completeness, or genuine temporal preregistration.

## Prior evidence

The [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
distinguishes a required property from string-length constraints and states that omitting
`minLength` behaves like a minimum of zero. This experiment applies only the narrower analogy
that required experiment metadata also needs a non-placeholder value; it is not a JSON Schema
implementation.

## Decision

`fail`
