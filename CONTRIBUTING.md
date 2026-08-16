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

Never submit private infrastructure details, secrets, raw logs, private datasets, model
weights, or identifying system metadata. Report resources using the anonymous capability
envelope.
