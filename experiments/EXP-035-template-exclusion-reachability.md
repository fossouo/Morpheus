# EXP-035 — Template exclusion reachability pair

- **Schema**: strict-v1
- **Date**: 2026-09-04
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned public v1 template and two fresh synthetic scope cases

## Question

Do the v1 sidecar-root and stable-v2 routing paths distinguish a disjoint matching
exclusion from a matching exclusion nested beneath the same package's included prefix?

## Hypothesis

For fresh held-out request suffixes, both paths will return `scope-not-found` when an
exclude matches but no include is reachable, and `scope-excluded` when both a package's
include and its nested exclude match. An exclude-only heuristic will score 1/2 while an
independent include-gated reachability oracle will score 2/2.

## Baseline

The semantic baseline predicts `scope-excluded` whenever a package's exclude matches,
without checking whether that package is a routing candidate. The candidate oracle first
requires a matching include from the same package. The behavioral comparison runs both
the historical v1 manifest plus sidecar root and the promoted stable-v2 validator/router,
using identical manifests, knowledge, package orders, and requests.

## Protocol

1. Verify the SHA-256 pin of the unchanged public v1 template and its validity at the
   historical reference date `2026-09-01`.
2. Derive two otherwise identical synthetic manifests. The disjoint case keeps the
   template's separate include and exclude prefixes. The nested case places the exclude
   below the include prefix. Root both through the existing deterministic migration.
3. Use an independent literal segment-prefix oracle to count include and exclude matches
   for fresh `amber-035` and `cobalt-035` held-out suffixes.
4. Compose each case with the same peer package in both orders. Query the case, a fresh
   allowed descendant, and a fresh absent descendant through the v1 sidecar-root and
   stable-v2 paths, then unload both paths and query again.
5. Execute two complete trials in one measured command. Require exact repetition, then run
   the repository checks and manually inspect the public diff.

Reproduce with `python3 scripts/evaluate_template_exclusion_reachability.py`. Only repository
data and the Python standard library may be used. No model call, training, download, service
change, production mutation, paid call, or accelerator workload is permitted. The public
template and stable routers remain unchanged regardless of outcome.

## Metrics

- Exclude-only baseline and include-gated oracle accuracy across two locked cases.
- Independent include/exclude match counts for each case.
- Exact v1/v2 parity across two cases and two package orders (4 comparisons), plus
  correctness across both paths (8 comparisons).
- Allowed and absent regression correctness across both paths and orders (8 each).
- Rollback correctness across both paths, cases, and orders (8 comparisons), order
  invariance, candidate-manifest validity, and two-trial repeatability.
- Combined fixture and pinned-template bytes, evaluator wall time, C0 class, and external
  call count. No resident-memory, inference, or energy measurement is claimed.

## Acceptance and stop criteria

Accept only if the exclude-only baseline scores exactly 1/2 and the reachability oracle
2/2; independent match counts are exact for 2/2 cases; both candidate manifests validate;
v1/v2 parity is 4/4 and path correctness 8/8; allowed and absent regressions are each 8/8;
rollback is 8/8; both orders are invariant; complete trials repeat; combined inputs are
below 16 KiB; measured time is below one second; external calls are zero; and all repository
publication checks pass.

Stop on pin drift, fixture mutation, unsupported oracle input, exception, threshold failure,
dependency or runtime mutation, external call, or budget overrun. The single measured
invocation contains both trials and must not be tuned or rerun after a failure. Unit tests
afterward are reproducibility checks, not replacement measurements.

## Results

`pass`. The exclude-only baseline scored 1/2 while the independent include-gated oracle
scored 2/2. The disjoint case had zero include matches and one exclude match and returned
`scope-not-found`; the nested case had one include and one exclude match and returned
`scope-excluded`.

Both candidate manifests validated. The v1 sidecar-root and stable-v2 responses matched
4/4 across both cases and orders, and correctness across the two paths was 8/8. Allowed
and absent regressions each passed 8/8; rollback passed 8/8; order invariance and two-trial
repeatability held. Combined input size was 2,419 bytes. The single measured invocation
took 0.002300 seconds and made zero external calls. The protocol was not tuned or rerun.

## Interpretation

**Observation:** both routing paths distinguished the two locked topologies exactly as
preregistered, while the exclude-only heuristic misclassified the disjoint case.

**Inference:** in this literal synthetic router, an exclusion produces `scope-excluded`
only after a same-package include makes the request a routing candidate. A matching
exclusion outside the include region is not independently reachable. This clarifies the
template migration fixture semantics; it does not improve or modify either router.

## Limitations

The request suffixes are fresh, but the public template vocabulary and routing kernels are
already exposed. The pair does not test wildcard scopes, multiple matching candidates,
natural-language intent, authorization semantics, source trust, runtime safety, or general
language capability. A passing result cannot by itself justify template migration.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines structural assertions, not routing precedence. The primary
[TUF specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
motivates a fixed time reference, but this experiment's date-only lifecycle and routing
semantics remain repository-defined policies.

## Decision

`pass`

## Next step

Keep the public template on v1. The next smallest step is a final preregistered template-
migration decision gate that consumes EXP-034's corrected disjoint expectation and EXP-035's
reachable nested companion, while requiring exact validation, projection, routing, expiry,
order, regression, and rollback checks before any template change.
