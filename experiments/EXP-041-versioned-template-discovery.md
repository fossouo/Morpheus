# EXP-041 — Versioned expert-template discovery

- **Schema**: strict-v1
- **Date**: 2026-09-10
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned public templates, EXP-040 evidence, and synthetic consumers

## Question

Can a second independently authored synthetic v2 consumer discover and select the exact
versioned template while v1 remains the default, an advertised incompatible version is rejected,
and removal of v2 fails closed without fallback?

## Hypothesis

The default-only baseline will answer only one of three discovery cases correctly. The candidate
will increase exact v2 consumers from one to two, answer all three cases correctly, validate and
route the independent package in both package orders, unload cleanly, reject the incompatible v3
descriptor, and preserve the v1 default after isolated v2 removal without substituting it for the
missing pinned v2 artifact.

## Baseline

The baseline is EXP-040's single materialized v2 consumer plus a resolver that always returns the
public default v1 template regardless of the requested schema. The candidate adds one static,
independently specified synthetic v2 package and exact schema/path/SHA-256 selection. Both use the
same fixed public v1 and versioned v2 bytes, stable manifest validator, routing kernel, pinned date,
and discovery cases.

## Protocol

1. Verify SHA-256 pins for EXP-040, its fixture, public v1, and versioned v2; require EXP-040's
   one-consumer baseline and keep both templates unchanged.
2. Lock two v2 consumer descriptors: EXP-040's prior consumer and a separately specified synthetic
   package with distinct identity, root, scope, provenance, layers, tests, and knowledge record.
3. Advertise v1, v2, and an unsupported v3 descriptor. Compare the default-only baseline with an
   exact resolver on unspecified, v2, and v3 requests; load supported artifacts only by path and
   SHA-256 and validate their embedded schema.
4. Compose the independent package with the existing synthetic template package in both orders;
   score two held-out targets, one absent-scope regression, one disjoint exclusion, and unload.
5. In an isolated temporary directory, select v2, remove only its file, and require the same pinned
   v2 request to fail closed while an unspecified request still selects v1 and v3 remains rejected.
6. Repeat the complete trial within one measured command.

Reproduce with `python3 scripts/evaluate_versioned_template_discovery.py`. Use only repository
data, temporary files, and the Python standard library. No model calls, training, downloads,
services, accelerators, subprocesses, external calls, template edits, or historical rewrites are
allowed.

## Metrics

- Exact v2 consumers: baseline 1; candidate target 2, with the second package structurally valid.
- Discovery: baseline 1/3; candidate 3/3; three descriptors discovered, two supported, one
  incompatible descriptor explicitly rejected; public v1 remains the unspecified default.
- Routing: 4/4 target responses, 2/2 regressions, 2/2 exclusions, order invariance, and 4/4
  post-unload responses.
- Removal: v2 selects before removal, returns exactly `error:pinned-template-missing` afterward,
  does not fall back to v1, while default v1 still selects and v3 remains rejected.
- Complete-trial repeatability, pinned input bytes, evaluator time, C0 class, and zero external
  calls. No language-quality, inference, energy, production, or general capability metric is
  claimed.

## Acceptance and stop criteria

Accept only if consumers increase from exactly one to two; the independent package validates; the
baseline scores exactly 1/3 and the candidate 3/3; v1 stays default; v2 selection is hash-bound; v3
is discovered but rejected; all 4 target, 2 regression, 2 exclusion, and 4 rollback comparisons
pass; both orders are identical; isolated removal returns the exact locked error without v1
fallback while v1 and v3 outcomes remain correct; trials repeat; pinned inputs stay below 32 KiB;
measured time stays below one second; external calls are zero; and publication checks pass.

Stop on pin drift, a changed template, consumer-count mismatch, invalid independent package,
ambiguous or incorrect selection, unsupported-version acceptance, hash bypass, v1 fallback after
v2 removal, routing/order/rollback mismatch, exception, repository mutation by the evaluator,
external call, or budget overrun. The measured evaluator command may run only once and must not be
tuned or rerun after failure. Subsequent tests are reproducibility checks, not replacement
measurements.

## Results

`pass`. The exact v2 consumer count increased from the locked EXP-040 baseline of one to two,
and the independently specified package passed structural validation. The default-only resolver
answered 1/3 cases correctly; the exact resolver answered 3/3. It discovered all three
descriptors, kept v1 as the unspecified default, selected v2 only after its bytes matched the
declared SHA-256 and embedded schema, and rejected the advertised v3 descriptor as unsupported.

Both package orders produced 4/4 correct target responses, 2/2 absent-scope regressions, and 2/2
disjoint-exclusion responses. Order invariance held, and unload restored 4/4 baseline responses.
In the isolated removal trial, v2 selected before deletion and then returned exactly
`error:pinned-template-missing`; it did not fall back to v1. An unspecified request still selected
v1, and v3 remained rejected. Complete trials repeated. Pinned inputs were 16,923 bytes, the
single measured invocation took 0.004359 seconds, and external calls were zero. The evaluator was
not tuned or rerun.

## Interpretation

**Observation:** a second static synthetic consumer selected the versioned v2 artifact through an
exact schema/path/hash reference, routed its held-out exact-lookup case, and failed closed after
artifact removal while the public v1 default remained available.

**Inference:** the repository can retain v1 as its default while supporting two opt-in v2
consumers under this deterministic discovery contract. This supports a bounded next experiment on
consumer-declared compatibility ranges or metadata, not a change to either public template and not
a claim of semantic discovery or broader capability.

## Limitations

This protocol is limited to exact, caller-supplied schema identifiers and synthetic packages. It
cannot establish semantic discovery, dependency negotiation, provenance authenticity, trusted
clocks, concurrent removal safety, production readiness, language capability, or self-improvement.
SHA-256 is used only for local byte-identity and dependency-drift assertions. The primary
[TUF specification](https://theupdateframework.github.io/specification/latest/) motivates
separately addressed, hash-bound targets, but does not define this resolver. The primary
[JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-validation-01)
describes structural validation concepts but does not establish routing or lifecycle safety.

## Decision

`pass`

## Next step

Keep v1 as the public default and v2 opt-in. The next smallest experiment should compare exact
schema selection with a minimal consumer-declared compatibility policy over synthetic patch/minor
versions, requiring hash-bound artifacts, deterministic highest-compatible selection, explicit
ambiguity rejection, and fail-closed removal before any resolver is promoted beyond this evaluator.
