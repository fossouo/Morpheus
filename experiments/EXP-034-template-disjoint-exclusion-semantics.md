# EXP-034 — Template disjoint-exclusion semantics

- **Schema**: strict-v1
- **Date**: 2026-09-03
- **Status**: complete
- **Compute**: C0
- **Data**: SHA-256-pinned EXP-033 and EXP-032 fixtures and public v1 template

## Question

Does EXP-033's exclusion failure come solely from its expected response, while the v1
sidecar-root and stable-v2 paths already agree on the disjoint declared exclusion?

## Hypothesis

The historical trial will reproduce exclusion correctness 0/2 despite response equality
2/2. Changing only that expected response to `route-error:scope-not-found` will yield
correctness 2/2 without changing any trial output. The exclusion request will match a
literal excluded prefix but no included prefix in either package. Reverse projection
will independently preserve the complete source template, including both scope lists.

## Baseline

The baseline is the pinned EXP-033 replay, including its repaired record adapter and
incorrect `scope-excluded` expectation. The candidate changes only one expected response
in an in-memory copy of the EXP-032 fixture. Packages, router, validator, dates, requests,
answers, orderings, and historical files stay fixed. Both scoring rules see the same
responses; this is an exposed-case diagnostic, not a held-out capability comparison.

## Protocol

1. Verify the new fixture's EXP-033 SHA-256, then the transitive EXP-032 and template pins.
2. Inspect the migrated synthetic packages with a literal segment-prefix predicate
   independent of the routing implementation. Reject wildcard input to this narrow probe.
   Require zero include matches and exactly one exclude match for the locked request.
3. Execute one unchanged EXP-033 baseline trial. Score equality separately from correctness.
4. Copy the source fixture and replace only the exclusion expectation. Restore that one
   value in another copy and require complete equality with the original fixture.
5. Run two corrected trials using the unchanged EXP-033 adapter and EXP-032 harness.
   Require both trials to equal the historical trial exactly, including all output fields.
6. Separately migrate and reverse-project the source template and compare the entire object
   and the include and exclude lists, without consulting routing outcomes.
7. Perform one measured command, then the required repository checks and public diff review.

Reproduce with `python3 scripts/evaluate_template_disjoint_exclusion.py`. Pinned lifecycle
dates remain `2026-09-01` and `2026-09-02`; they are historical test dates, not assertions
that the template is active on the run date. Only repository data and the Python standard
library may be used. There are no model calls, training, downloads, service changes, or
new accelerator workloads. The public template remains v1 even if the diagnostic passes.

## Metrics

- Historical exclusion response equality and old-expectation correctness across two orders.
- Corrected exclusion response equality and correctness across both orders, separately.
- Literal include/exclude match counts; expectation-only change and complete-output parity.
- Exact targets in both orders (4 comparisons), regressions (2), unload responses (4),
  full order invariance, source/candidate validation, and next-day expiry.
- Independent complete-template and scope-list projection equality; two-trial repeatability.
- Combined new fixture, two pinned fixtures, and template bytes; measured evaluator time;
  C0 execution and external-call count. No resident-memory or inference measurement is claimed.

## Acceptance and stop criteria

Accept only if historical equality is 2/2 and old-expectation correctness is 0/2; corrected
equality and correctness are both 2/2; the probe counts are zero includes and one exclude;
only the expected value changed; all complete trials match; targets are 4/4, regressions
2/2, and unload 4/4; both order outputs are identical; both manifests validate at the pinned
date; the candidate returns exactly `expired` on the next day; projection and both scope
lists are identical; trials repeat; combined inputs are below 16 KiB; measured time is
below one second with zero external calls; and all repository publication checks pass.

Stop on a pin mismatch, unsupported probe pattern, exception, threshold failure, input or
runtime mutation, external dependency, or budget overrun. The single measured invocation
contains one historical and two corrected trials; do not tune or rerun it after failure.
Subsequent unit tests are reproducibility checks, not replacement measured observations.

## Results

`pass`. Historical response equality was 2/2 while old-expectation correctness was 0/2
for each path. Corrected equality and correctness were 2/2 for each path. The literal
probe found zero included prefixes and one excluded prefix. Only the in-memory expected
response changed, and the complete historical and both corrected trials were identical.

Target correctness and v1/v2 equality passed 4/4 comparisons across both orders;
regressions passed 2/2 and unload passed 4/4. Full order invariance, two-trial repeatability,
both pinned-date validations, next-day expiry, complete reverse projection, and both
scope lists passed. Combined input size was 2,646 bytes. The single measured command took
0.002590 seconds and made zero external calls. The protocol was not tuned or rerun.

The first repository-suite invocation found a report-format error: the strict record
contract requires the Decision section to contain only its verdict. Moving the next-step
paragraph under its own heading fixed that publication issue without changing the measured
protocol, fixture, results, or validator.

After the formatting correction, all 234 repository tests passed; all 35 experiment
records and 35 index entries validated; the public v1 template validated at its pinned
date; the public-safety scan and whitespace check passed. The contributor workflow's
existing successful evaluators also passed. Manual staged-diff review found only synthetic
fixtures, diagnostic code, tests, and documentation, with no private observations or
infrastructure details.

## Interpretation

**Observation:** identical v1/v2 responses failed the historical expectation and passed
the preregistered replacement. The independent literal probe confirms that the declared
exclude matches this request while no include matches. Projection independently preserved
the complete template and its scope lists.

**Inference:** EXP-033's mismatch was an expectation error for this disjoint request, not
a difference between the compared routing paths. Changing scoring establishes no improved
routing capability. The historical failed records retain their original verdicts.

## Limitations

The cases were exposed in EXP-032 and EXP-033 and must not be described as a fresh holdout.
The independent reachability probe covers only literal prefixes and the locked request;
it does not establish general wildcard exclusion coverage. This diagnostic cannot establish
migration ergonomics, source authenticity, authorization correctness, runtime safety,
natural-language capability, or self-improvement. No stable component is promoted.

The primary [JSON Schema 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
defines structural assertions; it does not define this router's error precedence. The
primary [TUF specification](https://theupdateframework.github.io/specification/latest/#record-fixed-update-start-time)
uses a fixed update start time. Our date-only lifecycle and synthetic routing remain
repository-defined policies; neither source establishes the expected experiment result.

## Decision

`pass`

## Next step

Retain this diagnostic in quarantine and keep the public template on v1. The next smallest
step is a separately preregistered synthetic pair contrasting a disjoint exclusion with an
exclusion nested within an included prefix, using fresh held-out request suffixes and both
routing paths. That would test reachable exclusion behavior before a template migration
decision; it must not be presented as learned language capability.
