# Contributing

Contributions should strengthen falsifiability, reproducibility, or safety.

Before proposing a change:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_experiment_records.py .
python3 scripts/validate_experiment_index.py .
python3 scripts/validate_expert_manifest.py templates/expert-package.json --reference-date 2026-08-08
python3 scripts/evaluate_expert_lookup.py
python3 scripts/evaluate_expert_composition.py
python3 scripts/evaluate_qualified_expert_routing.py
python3 scripts/evaluate_scope_expert_routing.py
python3 scripts/evaluate_hierarchical_scope_routing.py
python3 scripts/evaluate_wildcard_scope_routing.py
python3 scripts/evaluate_exclusion_scope_routing.py
python3 scripts/evaluate_package_owned_exclusion_routing.py
python3 scripts/evaluate_specificity_floor_exclusion_routing.py
python3 scripts/evaluate_equal_specificity_exclusion_isolation.py
python3 scripts/evaluate_declared_root_boundary.py
python3 scripts/evaluate_package_root_ownership.py
python3 scripts/evaluate_expert_manifest_root.py
python3 scripts/evaluate_manifest_integrated_root_routing.py
python3 scripts/evaluate_expert_manifest_temporal_corpus.py
python3 scripts/evaluate_stable_validator_integration.py
python3 scripts/check_public_safety.py .
```

Experiment reports must use the template, declare failure criteria in advance, and avoid
claims broader than the tested configuration.

New experiment reports declare `Schema: strict-v1`. The validator checks their required
metadata and sections, including rejection of empty bodies and known template placeholders;
historical reports without a schema declaration remain legacy records.

Required metadata values are parsed from their own line. Empty values are invalid, and the
unchanged template `Data` value plus the exact short markers declared by the validator are
rejected as structural placeholders rather than semantic-quality judgments.

Every `EXP-NNN` file must occur exactly once in the experiment index. Indexed status and
verdict values must match the corresponding record. The indexed title must match the record
heading; a backslash-escaped table pipe is compared with its rendered literal pipe.

Expert packages start from `templates/expert-package.json` and remain in quarantine. The
structural validator requires explicit scope exclusions, provenance, separated knowledge,
experience, skill, tool, and adapter layers, target and held-out regression tests, expiry, and
an unload rollback. Callers must supply a pinned reference date; the date-only policy treats the
package as valid on `expires_on` and expired on later dates. Validation does not constitute
promotion or evidence of runtime safety.

Identifiers are unique both within and across the five expert layer lists. This exact,
case-sensitive structural rule keeps one identifier from ambiguously naming knowledge,
experience, a skill, a tool, or an adapter; it does not infer semantic equivalence.

The EXP-012 evaluator exercises a quarantined expert as an unloadable non-parametric lookup
layer. Its synthetic held-out target and regression cases demonstrate only exact-key behavior;
passing them is not evidence of semantic retrieval or general language capability.

The EXP-013 evaluator composes quarantined synthetic lookup experts transactionally. It checks
order-invariant compatible composition, fail-closed exact knowledge-ID conflicts, and unload
rollback; passing it is not evidence of semantic conflict detection or concurrent atomicity.

The EXP-014 evaluator tests explicit package-qualified lookup for experts that reuse a local
knowledge ID. It compares this with EXP-013's fail-closed collision policy and checks routing,
order invariance, and unload rollback; passing it is not evidence of learned or semantic routing.

The EXP-015 evaluator routes exact caller-supplied scope labels to composed quarantined experts.
It rejects overlapping and absent scopes, checks order invariance and unload rollback, and compares
with EXP-014's explicit package qualification. Passing it is not evidence of semantic intent
classification, expert discovery, or natural-language routing.

The EXP-016 evaluator treats slash-separated caller scopes as a segment hierarchy and selects the
deepest declared prefix. It compares descendant routing with EXP-015's exact-only policy, rejects
duplicate equal-specificity prefixes, near-prefixes, and absent scopes, and checks order invariance
and unload rollback. Passing it is not evidence of semantic, learned, or wildcard routing.

The EXP-017 evaluator adds a minimal whole-segment `*` pattern and ranks matches by declared depth
then literal-segment count. It compares wildcard routing with EXP-016's literal-prefix policy,
rejects request-time equal-specificity ties, and checks boundaries, order invariance, regressions,
and unload rollback. Passing it is not evidence of semantic, learned, or natural-language routing.

The EXP-018 evaluator applies exact and whole-segment-wildcard exclusions before include ranking
or expert lookup. It compares this with EXP-017's exclusion-blind policy and checks specificity,
ties, boundaries, order invariance, regressions, and unload rollback. Passing it is not evidence
of authorization-system correctness, semantic policy interpretation, or runtime safety.

The EXP-019 evaluator filters each matching package by only the exclusions that package owns,
then applies the existing include ranking. It compares this with EXP-018's global deny rule and
checks cross-package interference, all-excluded fail-closed behavior, specificity, ties,
regressions, order invariance, and unload rollback. Passing it is not evidence of authorization-
system correctness, semantic policy interpretation, or runtime safety.

The EXP-020 evaluator fixes the best matching include score before package-owned exclusion
filtering. It compares this specificity floor with EXP-019's broader eligible fallback and checks
exact and wildcard fallback denials, cross-package delegation, all-excluded behavior, specificity,
ties, regressions, order invariance, and unload rollback. Passing it is not evidence of
authorization-system correctness, semantic policy interpretation, or runtime safety.

The EXP-021 evaluator separates equal-specificity ambiguity from package-owned exclusion. It
tests selection only when exclusion leaves one top-score package eligible, while preserving
ambiguity between two eligible packages, all-excluded denial, and the EXP-020 specificity floor.
Passing it is not evidence of authorization-system correctness, semantic policy interpretation,
or runtime safety.

The EXP-022 evaluator extends the locked candidate set to three equal-specificity packages. It
checks exact and wildcard transitions from three candidates to one, two, or zero eligible
packages across every package permutation. The locked run failed because a first-segment wildcard
crossed the intended top-level scope boundary; running the EXP-022 evaluator directly reproduces
that failure and is expected to exit non-zero. The result does not establish authorization-system
correctness, semantic policy interpretation, scalable performance, or runtime safety.

The EXP-023 evaluator tests a pre-composition rule requiring literal first scope segments and
replays EXP-022 after eight locked literal-root substitutions. The locked run failed because the
substitutions also increased literal-count specificity, changing three held-out routing outputs;
running the evaluator directly reproduces that failure and is expected to exit non-zero. The
guard did reject unsafe packages transactionally and fix the boundary probe, but it is not
promoted and does not establish authorization-system correctness, semantic policy interpretation,
scalable performance, or runtime safety.

The EXP-024 evaluator tests a separately declared literal root fence against the unchanged
EXP-022 packages. The locked run rejected four cross-root requests in every package permutation
while preserving the original targets, cardinalities, regressions, and unload rollback. Passing
it is not evidence that an untrusted root declaration is correct, nor of authorization-system
correctness, semantic policy interpretation, scalable performance, or runtime safety.

The EXP-025 evaluator tests package-owned literal roots across two synthetic namespaces. It
constrains a package's leading wildcard to its own root, preserves unrelated-root routing, and
rejects inconsistent declarations before installing state. Passing it is not evidence that a
package's declaration is trustworthy, nor of authorization-system correctness, semantic policy
interpretation, scalable performance, or runtime safety.

The EXP-026 evaluator tests a quarantined opt-in manifest contract for a package-owned literal
root while routing historical v1 manifests through the unchanged stable validator. It rejects
missing, empty, wildcard, nested, dot-segment, and literal-pattern-mismatched roots in the locked
fixture. The contract is not promoted by this experiment, and passing it is not evidence of
declaration trust, migration safety, authorization correctness, semantic routing, scalable
performance, or runtime safety.

The EXP-027 evaluator moves EXP-025's sidecar roots into opt-in v2 manifests, validates them with
the quarantined EXP-026 contract and a pinned expiry date, then reuses the unchanged EXP-025
router. It tests exact synthetic behavioral parity, transactional invalid-manifest rejection,
rollback, and historical v1 validation parity without promoting a stable contract. Passing is not
evidence of declaration trust, migration safety, authorization correctness, semantic routing,
scalable performance, or runtime safety.

The EXP-028 evaluator tests stable v2 promotion against the quarantined contract, historical v1
sources, held-out routing, invalid-composition rejection, and rollback. The locked run failed
because one structurally valid historical v1 source was expired at the promotion date; running
the evaluator directly reproduces that failure and is expected to exit non-zero. No stable
validator or template change was promoted, and the result does not establish declaration trust,
migration safety, authorization correctness, semantic routing, scalable performance, runtime
safety, or self-improvement.

The EXP-029 evaluator separates invariant structural compatibility from pinned-date lifecycle
acceptance across the four historical v1 sources used by EXP-026. It locks before, on, after,
and EXP-028 reference dates without changing the stable validator or retrying v2 promotion.
Passing does not establish source authenticity, clock trust, migration safety, runtime safety,
or self-improvement.

The EXP-030 evaluator retries the v2 promotion gate only after consuming EXP-029's separate
structural and pinned-date lifecycle expectations. It also replays EXP-027 routing, invalid
composition, and rollback behavior. Every locked threshold passed, so the stable validator now
accepts opt-in v2 manifests while the public template remains on v1. Passing does not establish
declaration authenticity, clock trust, migration safety, authorization correctness, semantic
routing, runtime safety, or self-improvement.

The EXP-031 evaluator replaces the quarantined validation path in expert composition with the
promoted stable validator and compares the complete result with EXP-030's frozen promotion-
candidate baseline. It checks exact synthetic routing, invalid-composition rejection, clean
state, and unload rollback without migrating the public template. Passing does not establish
declaration authenticity, authorization correctness, semantic routing, runtime safety, natural-
language capability, or self-improvement.

Never submit private infrastructure details, secrets, raw logs, private datasets, model
weights, or identifying system metadata. Report resources using the anonymous capability
envelope.
